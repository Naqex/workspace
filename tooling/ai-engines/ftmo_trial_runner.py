"""Bounded FTMO DEMO observation or private shadow ledger; never sends orders."""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import ftmo_free_trial_adapter as adapter

ASSETS = ("XAUUSD", "EURUSD", "US500", "GBPUSD", "AUDUSD")
ALLOW_LIVE_ORDER_SEND = False
SPEC_FIELDS = ("trade_contract_size", "volume_min", "volume_step", "volume_max", "point",
    "trade_tick_size", "trade_tick_value", "trade_stops_level", "trade_freeze_level", "swap_long",
    "swap_short", "swap_mode", "swap_rollover3days", "trade_mode", "currency_profit", "currency_margin")


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)


def terminal_inventory():
    if sys.platform != "win32":
        return []
    raw = subprocess.check_output(["powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name = 'terminal64.exe'\" | "
        "Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"],text=True,encoding="utf-8").strip()
    value = json.loads(raw) if raw else []
    return value if isinstance(value,list) else [value]


def check_mt5_ready(*, terminal=None, sdk=None, inventory=None,expected_binding=None):
    """Inspect an existing FTMO demo IPC session; never login/select/send."""
    started=time.perf_counter();initialized=False;native_clock=sdk is None
    r=dict(schema="MT5-readonly-preflight-v22",status="NOT_READY",read_only_ready=False,
        shadow_ready=False,actual_broker_orders=0,terminal_connected=False,
        last_reported_broker_ping_ms=None,ping_is_fresh_network_measurement=False,
        remaining_shadow_requirements=["account/spec/session parity","news/holiday coverage","admitted seeds"])
    try:
        terminals=terminal_inventory() if inventory is None else inventory
        r["terminals_seen"]=len(terminals)
        if not terminals:r["reason"]="NO_RUNNING_TERMINAL";return r
        if terminal is None:
            if len(terminals)!=1:r["reason"]="MULTIPLE_TERMINALS_REQUIRE_EXPLICIT_PATH";return r
            terminal=terminals[0].get("ExecutablePath")
        if not terminal or str(Path(terminal).resolve()).casefold() not in {
                str(Path(t["ExecutablePath"]).resolve()).casefold() for t in terminals if t.get("ExecutablePath")}:
            r["reason"]="REQUESTED_TERMINAL_NOT_OBSERVED_RUNNING";return r
        if sdk is None:
            import importlib
            sdk=importlib.import_module("MetaTrader5")
        if not sdk.initialize(path=str(Path(terminal).resolve()),timeout=500):
            r["reason"]="READONLY_IPC_ATTACH_FAILED";return r
        initialized=True
        account=sdk.account_info();info=sdk.terminal_info()
        if account is None or info is None:r["reason"]="ACCOUNT_OR_TERMINAL_INFO_UNAVAILABLE";return r
        a=account._asdict();ti=info._asdict()
        if type(a.get("trade_mode")) is not int or a["trade_mode"]!=0:r["reason"]="DEMO_TRIAL_REQUIRED";return r
        if "ftmo" not in (str(a.get("server",""))+str(a.get("company",""))).lower():
            r["reason"]="NON_FTMO_ACCOUNT_OUTSIDE_SCOPE";return r
        if a.get("currency")!="USD":r["reason"]="USD_ACCOUNT_REQUIRED";return r
        r["account"]={k:a.get(k) for k in ("server","company","currency","trade_mode")}
        if type(a.get("login")) is int:
            r["binding"]=dict(server=a["server"],account_hash=adapter.account_hash(a["login"],a["server"]))
        if expected_binding is not None and r.get('binding')!=expected_binding:
            r['reason']='CONFIGURED_TRIAL_ACCOUNT_CHANGED';return r
        r["terminal_path"]=str(Path(terminal).resolve())
        r["terminal_connected"]=bool(ti.get("connected"))
        ping=ti.get("ping_last")
        if isinstance(ping,(int,float)) and math.isfinite(ping) and ping>0:r["last_reported_broker_ping_ms"]=ping/1000
        symbols={};now=int(time.time()*1000)
        for asset in ASSETS:
            spec=sdk.symbol_info(asset);tick=sdk.symbol_info_tick(asset) if spec is not None else None
            quote=tick._asdict() if tick is not None else {}
            if native_clock and quote.get('time_msc') is not None:
                from ftmo_connection import quote_utc_msc
                quote['time_msc']=quote_utc_msc(quote['time_msc'],a.get('server'))
            valid=(isinstance(quote.get("time_msc"),int) and quote["time_msc"]<=now and
                all(isinstance(quote.get(k),(int,float)) and math.isfinite(quote[k]) for k in ("bid","ask")) and
                quote["bid"]>0 and quote["ask"]>=quote["bid"])
            age=now-quote["time_msc"] if valid else None
            symbols[asset]=dict(info_readable=spec is not None,quote_readable=bool(valid),quote_age_ms=age,
                fresh=bool(valid and age<=120000),permission_inferred_from_read_success_only=True)
        r["symbols"]=symbols
        r["read_only_ready"]=r["terminal_connected"] and all(symbols[a]["fresh"] for a in adapter.ASSETS)
        r["status"]="READ_ONLY_PROBE_OK" if r["read_only_ready"] else "NOT_READY"
        r["reason"]="SHADOW_PARITY_STILL_REQUIRED" if r["read_only_ready"] else "DISCONNECTED_OR_ACTIVE_SYMBOL_QUOTE_UNAVAILABLE_OR_STALE"
        return r
    except Exception as exc:
        r["reason"]="PREFLIGHT_ERROR";r["error_type"]=type(exc).__name__;return r
    finally:
        if initialized:
            try:sdk.shutdown()
            except Exception as exc:
                r.update(status="NOT_READY",read_only_ready=False,reason="READONLY_IPC_SHUTDOWN_FAILED",error_type=type(exc).__name__)
        r["probe_wall_ms"]=(time.perf_counter()-started)*1000
        r["probe_under_one_second"]=r["probe_wall_ms"]<1000


def snapshot(reader, now, *, replay=False):
    account=reader.account()
    if type(account.get("trade_mode")) is not int or account["trade_mode"] != 0:
        raise adapter.AdapterError("FTMO_DEMO_TRIAL_REQUIRED_REAL_ACCOUNT_REJECTED")
    if "ftmo" not in (str(account.get("server",""))+str(account.get("company",""))).lower():
        raise adapter.AdapterError("NON_FTMO_TERMINAL_OUTSIDE_TARGET_SCOPE")
    if account.get("currency") != "USD":
        raise adapter.AdapterError("FROZEN_USD_ACCOUNT_REQUIRED")
    binding=dict(server=account["server"],account_hash=adapter.account_hash(account["login"],account["server"]))
    adapter.verify_account(account,binding)
    specs={}
    for asset in ASSETS:
        try:
            raw=reader.spec(asset)
        except (adapter.AdapterError,KeyError):
            specs[asset]=dict(status="SYMBOL_UNAVAILABLE",unknown_fields=list(SPEC_FIELDS));continue
        value={k:raw.get(k) for k in SPEC_FIELDS}
        value.update(sessions_quote=raw.get("sessions_quote"),sessions_trade=raw.get("sessions_trade"),
            session_timezone=raw.get("session_timezone"),session_known_at_msc=raw.get("session_known_at_msc"))
        value["unknown_fields"]=[k for k,v in value.items() if v is None]
        value["status"]="PARTIAL" if value["unknown_fields"] else "OBSERVED"
        specs[asset]=value
    return dict(schema="FTMO-target-spec-v20",observed_at_msc=now,source="REPLAY_FIXTURE" if replay else "NATIVE_MT5",
        binding=binding,account={k:account.get(k) for k in ("server","company","currency","leverage","trade_mode")},
        specs=specs,actual_broker_orders=0,session_schedule_certified=False,
        commission_schedule="Requires signed deal-level costs; not inferred from swap or spread.")


def parity(snapshot_value, holidays=None):
    rows=[]
    for asset,spec in snapshot_value["specs"].items():
        expected={"trade_contract_size":100 if asset=="XAUUSD" else 100000,
                  "volume_min":.01,"volume_step":.01} if asset in adapter.ASSETS else {}
        for field,value in expected.items():
            actual=spec.get(field)
            rows.append(dict(asset=asset,field=field,expected=value,actual=actual,
                status="UNKNOWN" if actual is None else "MATCH" if actual==value else "DIFFERENT"))
        status="UNKNOWN";deadline=None
        now=snapshot_value["observed_at_msc"]
        sessions=spec.get("sessions_trade")
        if asset in adapter.ASSETS and sessions and spec.get("session_timezone") and adapter.calendar_known(holidays,now):
            try:
                deadline=adapter.session_deadline(now,holidays)
                zone=ZoneInfo(spec["session_timezone"])
                local_date=datetime.fromtimestamp(deadline/1000,timezone.utc).astimezone(zone).date()
                opened=False
                for day in (local_date-timedelta(days=1),local_date):
                    midnight=datetime.combine(day,datetime.min.time(),tzinfo=zone)
                    for session in sessions:
                        if session["weekday"]!=(day.weekday()+1)%7:continue
                        start=int(session["from_server_seconds"])%86400
                        raw_end=int(session["to_server_seconds"])
                        end=raw_end%86400 or (86400 if raw_end else 0)
                        if end<=start:end+=86400
                        lo=int((midnight+timedelta(seconds=start)).timestamp()*1000)
                        hi=int((midnight+timedelta(seconds=end)).timestamp()*1000)
                        opened=opened or lo<=deadline<hi
                status="MATCH" if opened else "DIFFERENT"
            except (adapter.AdapterError,KeyError,ValueError,TypeError,ZoneInfoNotFoundError):
                status="UNKNOWN"
        rows.append(dict(asset=asset,field="sessions_trade",status=status,
            expected="Current UTC day's registered flat deadline must be inside a supplied weekly trade session.",
            expected_deadline_msc=deadline,actual=sessions))
        if not expected:
            rows.append(dict(asset=asset,field="strategy_contract",status="NOT_IN_ACTIVE_PORTFOLIO",
                             expected=None,actual=spec.get("trade_contract_size")))
        rows.append(dict(asset=asset,field="commission_schedule",status="UNKNOWN",actual=None,
            expected="Registered proxy requires target deal/spec reconciliation; SDK symbol_info does not establish commission.",
            consequence="Read-only collection allowed; no execution-cost certification."))
    active=[r for r in rows if r["field"]=="sessions_trade" and r["asset"] in adapter.ASSETS]
    return dict(rows=rows,exact_session_parity=all(r["status"]=="MATCH" for r in active),
        session_parity_scope="Current registered cutoff versus supplied weekly sessions; not independent broker holiday certification.",
        blocking_divergences=[r for r in rows if r["status"]=="DIFFERENT"],
        missing_session_data_blocks_live_shadow=True)


class QuoteParquet:
    def __init__(self,path):
        import pyarrow as pa
        import pyarrow.parquet as pq
        self.pa,self.path=pa,Path(path)
        if self.path.exists():raise ValueError("quote_output_exists")
        self.schema=pa.schema([(k,t) for k,t in (("asset",pa.string()),("time_msc",pa.int64()),
            ("known_at_msc",pa.int64()),("bid",pa.float64()),("ask",pa.float64()),
            ("spread",pa.float64()),("flags",pa.int64()))])
        self.writer=pq.ParquetWriter(self.path,self.schema,compression="zstd",compression_level=9)
        self.pending=[];self.count=0;self.last={};self.gaps=[]

    def accept(self,event):
        if event["kind"]!="quote":return
        r={k:event[k] for k in ("asset","time_msc","known_at_msc","bid","ask")}
        if (not all(math.isfinite(r[k]) for k in ("bid","ask")) or r["bid"]<=0 or
                r["ask"]<r["bid"] or r["known_at_msc"]<r["time_msc"]):
            raise ValueError("invalid_or_future_quote")
        old=self.last.get(r["asset"])
        if old is not None and r["time_msc"]<old:raise ValueError("quote_time_regression")
        if old is not None and r["time_msc"]-old>120000:
            self.gaps.append(dict(asset=r["asset"],after=old,before=r["time_msc"],
                                  status="OBSERVATION_GAP_NOT_MARKET_CLOSURE_CERTIFICATE"))
        self.last[r["asset"]]=r["time_msc"]
        r.update(spread=r["ask"]-r["bid"],flags=int(event.get("flags",0)))
        self.pending.append(r);self.count+=1
        if len(self.pending)>=1024:self.flush()

    def flush(self):
        if self.pending:
            self.writer.write_table(self.pa.Table.from_pylist(self.pending,schema=self.schema));self.pending=[]

    def close(self):
        self.flush();self.writer.close()
        return dict(rows=self.count,observation_gaps=self.gaps,
            no_tick_arrival_not_proof_of_missing_vendor_ticks=True,slippage_measured=False,
            file=self.path.name,sha256=hashlib.sha256(self.path.read_bytes()).hexdigest())


class ObserverPaper(adapter.ShadowPaper):
    def __init__(self,plan,start,end):
        requested=plan.get("policy","V16")
        if requested=="V20":
            from prop_v20_common import FREEZE,read
            from prop_v20_accounts import V20Account
            profile=next((p for p in read(FREEZE)["profiles"] if p["name"]==plan.get("v20_profile")),None)
            if profile is None:raise adapter.AdapterError("UNFROZEN_V20_PROFILE")
            base=dict(plan,policy="V19")
            from prop_v19_common import FREEZE as parent_freeze,read as parent_read
            base["profile"]=parent_read(parent_freeze)["selected_profile"]
            super().__init__(base,start,end)
            self.account=V20Account(start,end,"SYM_FLAT",rolling=True,
                standalone=plan["phase"]=="FUNDED_STANDARD",profile=profile,friction_pct=100)
            if plan["phase"]=="VERIFICATION":self.account.phase=2
        else:
            super().__init__(plan,start,end)
        self.requested_policy=requested;self.excursions={}

    def advance(self,tick):
        active=list(self.account.active)
        def observe(indices):
            for i in indices:
                t=self.trades[i]
                if t["asset"]!=tick["asset"]:continue
                sign=1 if t["side"]=="BUY" else -1;scale=t["scale"]
                px=tick["bid"] if sign==1 else tick["ask"]
                move=sign*(px-t["entry_price_units"]/scale)
                row=self.excursions.setdefault(t["intent_id"],dict(MFE_price=0.,MAE_price=0.,observations=0))
                row["MFE_price"]=max(row["MFE_price"],move);row["MAE_price"]=min(row["MAE_price"],move)
                row["observations"]+=1;row["last_quote_msc"]=tick["time_msc"]
        observe(active)
        super().advance(tick)
        observe([i for i in self.account.active if i not in active])

    def report(self):
        return dict(super().report(),requested_policy=self.requested_policy,excursions=self.excursions,
                    excursion_basis="Observed executable quote markout; not net account PnL or certified intrasecond path.")


def stream(events,paper,recorder,output,*,speed=1.,sleeper=time.sleep):
    if not math.isfinite(speed) or speed<=0:raise ValueError("positive_replay_speed_required")
    previous=None;seen=set()
    with (output/"shadow-events.jsonl").open("x",encoding="utf-8") as journal:
        for ordinal,event in enumerate(events):
            known=event["known_at_msc"]
            if previous is not None and known<previous:raise adapter.AdapterError("REPLAY_TIME_REGRESSION")
            if not paper.account.start<=known<paper.account.end:raise adapter.AdapterError("REPLAY_CAPTURE_FENCE")
            identity=event.get("record_id",str(ordinal))
            if identity in seen:raise adapter.AdapterError("DUPLICATE_REPLAY_EVENT")
            seen.add(identity)
            if previous is not None:sleeper((known-previous)/1000/speed)
            previous=known;journal.write(json.dumps(event)+"\n");journal.flush()
            if event["kind"]=="quote":recorder.accept(event);paper.advance(event)
            elif event["kind"]=="account_mark":paper.mark=event["mark"]
            elif event["kind"]=="signal":paper.offer(event["intent"],known)
            elif event["kind"]=="closed_hours":
                import numpy as np
                asset=event["asset"];adapter.validate_closed_hours(event["rows"],known)
                hours=np.array([tuple(r[k] for k in ("t","bo","bh","bl","bc")) for r in event["rows"]],
                               dtype=[(k,"<i8") for k in ("t","bo","bh","bl","bc")])
                class Calendar:
                    def allowed(self,at):
                        try:return at<adapter.session_deadline(at,paper.plan["holidays"])
                        except adapter.AdapterError:return False
                for intent in adapter.signals_from_closed_hours(hours,asset,known,Calendar()):paper.offer(intent,known)
            elif event["kind"]=="closed_M1":
                if any(t%60000 or t+60000>known for t in event["times"]):raise adapter.AdapterError("FUTURE_CLOSED_M1")
                old=paper.plan.setdefault("closed_M1_times",{}).get(event["asset"],[])
                paper.plan["closed_M1_times"][event["asset"]]=sorted(set(old+event["times"]))[-1000:]
            else:raise adapter.AdapterError("UNKNOWN_REPLAY_EVENT")
            paper.last_time=known
    return paper.report()


def builtin_fixture():
    from prop_v19_common import FREEZE,read
    at=1651485600000
    specs={asset:dict(trade_contract_size=100 if asset=="XAUUSD" else 100000,
        volume_min=.01,volume_step=.01,volume_max=100,point=.001 if asset=="XAUUSD" else .00001,
        trade_tick_size=.01 if asset=="XAUUSD" else .00001,trade_stops_level=0,trade_freeze_level=0,
        swap_long=-45.,swap_short=-5.,swap_mode=1,swap_rollover3days=3,trade_mode=4) for asset in ASSETS}
    account=dict(login=123456,server="FTMO-REPLAY-FIXTURE",company="FTMO OFFLINE FIXTURE",trade_mode=0,currency="USD",leverage=100)
    cal=dict(source="DECLARED_SYNTHETIC_FIXTURE",known_at_msc=at-1,from_msc=at-60000,
             to_msc=at+86400000,coverage_complete=True,events=[],days={})
    p=dict(policy="V19",profile=read(FREEZE)["selected_profile"],phase="FREE_TRIAL",from_msc=at,to_msc=at+86400000,
        specs=specs,binding=dict(server=account["server"],account_hash=adapter.account_hash(account["login"],account["server"])),
        news=cal,holidays=cal,closed_M1_times={a:list(range(at-30*60000,at,60000)) for a in adapter.ASSETS})
    mark=dict(known_at_msc=at,midnight_msc=adapter.prague_midnight(at),history_query_complete=True,
              midnight_balance=50000.,equity=50000.,initial_balance=50000.)
    identity=next(k for k in p["profile"]["weights"] if k.startswith("XAUUSD|F3"))
    events=[dict(kind="account_mark",known_at_msc=at,mark=mark),dict(kind="signal",known_at_msc=at,
        intent=dict(id=identity,asset="XAUUSD",side="BUY",decision_msc=at,stop_units=1990000,mode="P0",intent_id="synthetic-demo"))]
    for seconds,bid in ((0,2000.),(1,2001.),(2,1998.),(3,1988.)):
        events.append(dict(kind="quote",known_at_msc=at+seconds*1000,time_msc=at+seconds*1000,
                           asset="XAUUSD",bid=bid,ask=bid+.338,flags=1))
    return dict(account=account,specs=specs,events=events),p


def run(mode,output,*,manifest=None,bridge=None,replay=False,seconds=60,speed=1.,terminal=None,
        require_native=False,expected_binding=None):
    if not 1<=seconds<=3600:raise ValueError("bounded_duration_1_to_3600_seconds")
    if not math.isfinite(speed) or speed<=0:raise ValueError("positive_replay_speed_required")
    inventory=terminal_inventory() if not replay else []
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    write(output/"environment.json",dict(terminals=inventory,SDK_available=bool(importlib.util.find_spec("MetaTrader5")),
        broker_order_capability=False,python=sys.executable))
    if require_native and (replay or bridge or not inventory):
        raise adapter.AdapterError("WATCH_NATIVE_TERMINAL_DISAPPEARED_NO_REPLAY_FALLBACK")
    if bridge:
        if not manifest:raise ValueError("bridge_requires_plan_manifest")
        bundle=json.loads(Path(bridge).read_text(encoding="utf-8-sig"));plan=json.loads(Path(manifest).read_text(encoding="utf-8-sig"))
        replay=True
    elif replay or not inventory:
        bundle,plan=builtin_fixture();replay=True
    else:
        if terminal is None:
            if len(inventory)!=1:raise adapter.AdapterError("MULTIPLE_TERMINALS_REQUIRE_EXPLICIT_PATH")
            terminal=inventory[0]["ExecutablePath"]
        from ftmo_connection import ClockReader
        reader=adapter.NativeMT5Reader(terminal)
        if hasattr(reader,'sdk'):reader=ClockReader(reader)
        try:
            now=int(time.time()*1000);snap=snapshot(reader,now)
            if expected_binding is not None and snap["binding"]!=expected_binding:
                raise adapter.AdapterError("WATCH_ACCOUNT_CHANGED_AFTER_PROBE")
            if manifest:
                plan=json.loads(Path(manifest).read_text(encoding="utf-8-sig"))
                if plan["binding"]!=snap["binding"]:raise adapter.AdapterError("MANIFEST_ACCOUNT_MISMATCH")
                export=plan.get("session_export")
                if export:
                    raw=Path(export["path"]).read_bytes()
                    if hashlib.sha256(raw).hexdigest()!=export["sha256"]:raise adapter.AdapterError("SESSION_EXPORT_HASH")
                    sessions=json.loads(raw)
                    if (sessions.get("schema")!="mt5-readonly-sessions-v1" or sessions["server"]!=snap["binding"]["server"] or
                            adapter.account_hash(sessions["login"],sessions["server"])!=snap["binding"]["account_hash"]):
                        raise adapter.AdapterError("SESSION_EXPORT_ACCOUNT_BINDING")
                    if not adapter.calendar_known(export,now):raise adapter.AdapterError("SESSION_EXPORT_COVERAGE_OR_CLOCK_UNKNOWN")
                    for asset in adapter.ASSETS:
                        values=sessions["symbols"].get(asset,{})
                        for key in ("sessions_quote","sessions_trade"):
                            if key in values:snap["specs"][asset][key]=values[key]
                        snap["specs"][asset]["session_timezone"]=export.get("session_timezone")
            diff=parity(snap,plan.get("holidays") if manifest else None)
            write(output/"TARGET_ACCOUNT_SPEC_SNAPSHOT.json",snap);write(output/"SPEC_PARITY_DIFF.json",diff)
            with_path=QuoteParquet(output/"quotes.parquet")
            try:
                if mode=="shadow-paper":
                    if not manifest:raise adapter.AdapterError("NATIVE_SHADOW_NEEDS_VERIFIED_SEED_NEWS_SESSION_MANIFEST")
                    plan=json.loads(Path(manifest).read_text(encoding="utf-8-sig"))
                    if plan["binding"]!=snap["binding"]:raise adapter.AdapterError("MANIFEST_ACCOUNT_MISMATCH")
                    if not all(isinstance(snap["specs"][a].get("sessions_trade"),list) and
                               bool(snap["specs"][a]["sessions_trade"]) for a in adapter.ASSETS):
                        raise adapter.AdapterError("SESSION_EXPORT_BRIDGE_REQUIRED_BEFORE_NATIVE_SHADOW")
                    if not adapter.calendar_known(plan["holidays"],now) or not adapter.calendar_known(plan["news"],now):
                        raise adapter.AdapterError("CURRENT_NEWS_AND_HOLIDAY_COVERAGE_REQUIRED")
                    if not all(snap["specs"][a].get("session_timezone") for a in adapter.ASSETS):
                        raise adapter.AdapterError("BROKER_SESSION_TIMEZONE_MAPPING_REQUIRED")
                    if not diff["exact_session_parity"] or diff["blocking_divergences"]:
                        raise adapter.AdapterError("SPEC_OR_SESSION_CUTOFF_PARITY_NOT_ESTABLISHED")
                    result=adapter.run_native_shadow(reader,plan,output,max_seconds=seconds,poll_seconds=1,
                        paper_factory=ObserverPaper,event_sink=with_path.accept)
                    write(output/"shadow_paper_ledger.json",result)
                else:
                    previous={};deadline=time.monotonic()+seconds
                    while time.monotonic()<deadline:
                        adapter.verify_account(reader.account(),snap["binding"]);end=int(time.time()*1000)
                        for asset,spec in snap["specs"].items():
                            if spec["status"]=="SYMBOL_UNAVAILABLE":continue
                            first=previous[asset][0] if asset in previous else now
                            rows=reader.ticks(asset,first,end+1);received=int(time.time()*1000)
                            fresh=adapter.new_live_ticks(rows,previous.get(asset))
                            for row in fresh:with_path.accept(dict(row,kind="quote",known_at_msc=received))
                            if rows:
                                boundary=rows[-1]["time_msc"]
                                previous[asset]=(boundary,[(r["time_msc"],r["bid"],r["ask"],r.get("flags",0)) for r in rows if r["time_msc"]==boundary])
                        time.sleep(1)
                    result=dict(mode="READ_ONLY",actual_broker_orders=0,slippage_measured=False)
            finally:write(output/"quote_capture.json",with_path.close())
            write(output/"report.json",dict(result,native_terminal_verified=True,source="NATIVE_MT5"));return
        finally:reader.close()
    reader=adapter.FileBridge.__new__(adapter.FileBridge);reader.bundle=bundle
    snap=snapshot(reader,plan["from_msc"],replay=True)
    if snap["binding"]!=plan["binding"]:raise adapter.AdapterError("REPLAY_ACCOUNT_BINDING_MISMATCH")
    write(output/"TARGET_ACCOUNT_SPEC_SNAPSHOT.json",snap);write(output/"SPEC_PARITY_DIFF.json",parity(snap))
    recorder=QuoteParquet(output/"quotes.parquet")
    try:
        if mode=="shadow-paper":
            paper=ObserverPaper(plan,plan["from_msc"],plan["to_msc"])
            result=stream(bundle["events"],paper,recorder,output,speed=speed)
            result["fill_reconciliation"]=adapter.reconcile_fills(result["expected_fills"],bundle.get("external_fills",[]))
            write(output/"shadow_paper_ledger.json",result)
        else:
            previous=None
            for event in bundle["events"]:
                if event["kind"]!="quote":continue
                if previous is not None:time.sleep((event["known_at_msc"]-previous)/1000/speed)
                recorder.accept(event);previous=event["known_at_msc"]
            result=dict(mode="READ_ONLY",actual_broker_orders=0)
    finally:write(output/"quote_capture.json",recorder.close())
    write(output/"report.json",dict(result,source="TIMESTAMP_PACED_REPLAY",native_terminal_verified=False,
        injected_fixture_intent=bridge is None,strategy_signal_parity_not_established_by_builtin_fixture=True,
        slippage_measured=False))


def watch_mt5(output,*,timeout=300,poll_seconds=5,capture_seconds=60,terminal=None,manifest=None,expected_binding=None,
              probe=None,capture=None,clock=time.monotonic,sleeper=time.sleep):
    """Bounded foreground wait followed by native read-only capture, never paper/orders."""
    if not math.isfinite(timeout) or not 1<=timeout<=3600:raise ValueError("WATCH_TIMEOUT_1_TO_3600_SECONDS")
    if not math.isfinite(poll_seconds) or not .1<=poll_seconds<=30:raise ValueError("WATCH_POLL_01_TO_30_SECONDS")
    if not 1<=capture_seconds<=3600:raise ValueError("WATCH_CAPTURE_1_TO_3600_SECONDS")
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    if probe is None:
        probe=lambda **kwargs:check_mt5_ready(**kwargs,expected_binding=expected_binding)
    capture=capture or run
    start=clock();deadline=start+timeout;attempts=0
    result=dict(schema="MT5-watch-v23",status="WAITING",actual_broker_orders=0,native_capture_completed=False,
        wait_timeout_seconds=timeout,capture_seconds=capture_seconds,permanent_service_installed=False)
    write(output/"watch-plan.json",dict(timeout=timeout,poll_seconds=poll_seconds,capture_seconds=capture_seconds,
        terminal=terminal,manifest_supplied=manifest is not None,scope="FTMO_DEMO_USD_NATIVE_READONLY_ONLY"))
    try:
        with (output/"watch-events.jsonl").open("x",encoding="utf-8") as journal:
            while clock()<deadline:
                r=probe(terminal=terminal);attempts+=1
                journal.write(json.dumps(dict(attempt=attempts,elapsed=clock()-start,status=r.get("status"),
                    reason=r.get("reason"),terminals_seen=r.get("terminals_seen"),read_only_ready=r.get("read_only_ready",False)))+"\n");journal.flush()
                if clock()>=deadline:break
                if r.get("read_only_ready"):
                    if expected_binding is not None and r.get('binding')!=expected_binding:raise adapter.AdapterError('CONFIGURED_TRIAL_ACCOUNT_CHANGED')
                    if not r.get("binding") or not r.get("terminal_path"):
                        raise adapter.AdapterError("WATCH_PROBE_ACCOUNT_OR_TERMINAL_BINDING_UNKNOWN")
                    write(output/"ready-probe.json",r)
                    capture("read-only",output/"native-capture",seconds=capture_seconds,
                        terminal=r["terminal_path"],manifest=manifest,require_native=True,expected_binding=r["binding"])
                    native=json.loads((output/"native-capture/report.json").read_text(encoding="utf-8"))
                    if native.get("source")!="NATIVE_MT5" or not native.get("native_terminal_verified"):
                        raise adapter.AdapterError("WATCH_CAPTURE_MUST_BE_NATIVE_NOT_REPLAY")
                    result.update(status="NATIVE_READONLY_CAPTURE_COMPLETED",native_capture_completed=True,
                        spec_snapshot="native-capture/TARGET_ACCOUNT_SPEC_SNAPSHOT.json",quote_capture="native-capture/quotes.parquet",
                        shadow_ready=False,commission_and_sessions_may_remain_unknown=True)
                    break
                sleeper(min(poll_seconds,max(0.,deadline-clock())))
            else:result["status"]="TIMEOUT_NO_READY_TARGET"
            if result["status"]=="WAITING":result["status"]="TIMEOUT_NO_READY_TARGET"
    except KeyboardInterrupt:
        result["status"]="INTERRUPTED";result["resume_requires_reconciliation"]=True
    except Exception as exc:
        result.update(status="CAPTURE_OR_PROBE_FAILED",error_type=type(exc).__name__)
        if isinstance(exc,adapter.AdapterError):result["reason"]=str(exc)
    finally:
        result.update(attempts=attempts,total_wall_seconds=clock()-start)
        write(output/"WATCH_REPORT.json",result)
    return result


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--mode",choices=("read-only","shadow-paper"),default="read-only")
    p.add_argument("--output",type=Path);p.add_argument("--manifest",type=Path);p.add_argument("--bridge",type=Path)
    p.add_argument("--replay",action="store_true");p.add_argument("--seconds",type=int,default=60)
    p.add_argument("--speed",type=float,default=1.);p.add_argument("--terminal")
    p.add_argument("--check-mt5-ready",action="store_true")
    p.add_argument("--watch-mt5",action="store_true");p.add_argument("--watch-timeout",type=float,default=300)
    p.add_argument("--watch-poll-seconds",type=float,default=5)
    p.add_argument('--credentials-file',type=Path,help='Four-key private FTMO Trial env file; never a shell script')
    a=p.parse_args()
    from ftmo_connection import credentials,trial_session
    try:
        values=credentials(a.credentials_file)
        if values and (a.replay or a.bridge):p.error('credentials are separate from fixture/bridge replay')
        with trial_session(values) as terminal:
            a.credentials_active=values is not None
            a.expected_binding=dict(server=values['FTMO_MT5_SERVER'],account_hash=adapter.account_hash(int(values['FTMO_MT5_LOGIN']),values['FTMO_MT5_SERVER'])) if values else None
            if terminal:a.terminal=terminal
            return dispatch(a,p)
    except ValueError as exc:p.exit(2,'FTMO Trial setup stopped: '+str(exc)+'\n')


def dispatch(a,p):
    if a.watch_mt5:
        if a.check_mt5_ready or a.replay or a.bridge or a.mode!="read-only":p.error("watch only supports native read-only capture")
        from prop_v23_common import JOB as watch_root
        out=a.output or watch_root/("watch-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        try:r=watch_mt5(out,timeout=a.watch_timeout,poll_seconds=a.watch_poll_seconds,capture_seconds=a.seconds,
            terminal=a.terminal,manifest=a.manifest,expected_binding=a.expected_binding)
        except ValueError as exc:p.error(str(exc))
        print(json.dumps(dict(r,output=str(out))))
        return 0 if r["native_capture_completed"] else 130 if r["status"]=="INTERRUPTED" else 2
    if a.check_mt5_ready:
        if a.replay or a.bridge or a.manifest:p.error("readiness check is separate from replay/shadow manifests")
        from prop_v22_common import JOB as check_root
        out=a.output or check_root/("preflight-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        out.mkdir(parents=True,exist_ok=False)
        result=check_mt5_ready(terminal=a.terminal,expected_binding=a.expected_binding);write(out/"MT5_PREFLIGHT.json",result)
        print(json.dumps(dict(result,output=str(out))))
        return 0 if result["read_only_ready"] else 2
    from prop_v20_common import JOB
    out=a.output or JOB/("observer-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    try:run(a.mode,out,manifest=a.manifest,bridge=a.bridge,replay=a.replay,seconds=a.seconds,speed=a.speed,terminal=a.terminal,
        require_native=a.credentials_active,expected_binding=a.expected_binding)
    except (adapter.AdapterError,ValueError,ModuleNotFoundError) as exc:
        if out.exists() and not (out/"failure.json").exists():write(out/"failure.json",dict(error=str(exc),actual_broker_orders=0))
        p.exit(2,"Read-only/shadow stopped: "+str(exc)+". See QUICKSTART-FTMO-FREE-TRIAL.md.\n")
    print(json.dumps(dict(output=str(out),mode=a.mode,actual_broker_orders=0)))


if __name__=="__main__":raise SystemExit(main())
