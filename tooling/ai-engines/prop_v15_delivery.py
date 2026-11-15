"""Compact V15 evidence, fixed smoke campaign and owner-facing report."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from statistics import median,stdev
import json
import subprocess
import time
import numpy as np
from prop_v15_common import *
from prop_v15_campaign import metrics

REPORT=Path("planning/research/BRIDGE-AND-VELOCITY-V15-RESULTS-20261115")
PYTHON="C:/Users/MIIKEY/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"


def verify_tests():
    previous=set();current=set();groups={}
    for group in ("base","native","statistics","worker"):
        a=read(V14/f"tests-{group}.json")
        latest=JOB/f"tests-{group}-after-runner.json"
        b=read(latest if latest.exists() else JOB/f"tests-{group}.json")
        if not b["passed"] or b["skipped"]:raise ValueError("V15_test_group_failed:"+group)
        previous.update(a["timings"]);current.update(b["timings"])
        groups[group]={k:b[k] for k in ("tests","passed","skipped","seconds")}
    if previous-current or len(previous)!=1110:raise ValueError("V15_baseline_test_ID_loss")
    name="test-ID-preservation-after-runner.json" if (JOB/"test-ID-preservation.json").exists() else "test-ID-preservation.json"
    save(name,dict(passed=True,baseline_ids=len(previous),current_ids=len(current),
        missing=[],added=sorted(current-previous),groups=groups,zero_skip=True))


def smoke(label=""):
    prefix="smoke-"+label+"-" if label else "smoke-"
    def write(name,value):save(prefix+name,value)
    plan=dict(attempts=10,fresh_process=True,workers=1,tier="smoke",group="base",
        thresholds=dict(body_seconds=.85,heading_seconds=.8),retry_to_find_good_streak=False,
        initial_profile_separate_from_ten=True)
    plan["label"]=label or "initial"
    plan["baseline_retained"]="smoke-results.json" if label else None
    write("plan.json",plan)
    command=[PYTHON,"tooling/ai-engines/quant_test_suite.py","--group","base","--tier","smoke"]
    # First profile is diagnostic, not substituted for an outlier among the ten.
    subprocess.run(command+["--output",str(JOB/(prefix+"profile.json"))],check=True,capture_output=True)
    rows=[]
    for i in range(10):
        path=JOB/f"{prefix}{i:02d}.json";started=time.perf_counter()
        subprocess.run(command+["--output",str(path)],check=True,capture_output=True)
        wall=time.perf_counter()-started;r=read(path)
        rows.append(dict(attempt=i+1,wall_seconds=wall,suite_seconds=r["seconds"],
            tests=r["tests"],skipped=r["skipped"],passed=r["passed"]))
    if len({r["tests"] for r in rows})!=1 or any(r["skipped"] for r in rows):
        raise ValueError("V15_smoke_case_drift")
    write("results.json",dict(plan=plan,rows=rows,
        wall_median=median(r["wall_seconds"] for r in rows),wall_max=max(r["wall_seconds"] for r in rows),
        suite_median=median(r["suite_seconds"] for r in rows),suite_max=max(r["suite_seconds"] for r in rows),
        all_wall_below_085=all(r["wall_seconds"]<.85 for r in rows),
        all_wall_below_080=all(r["wall_seconds"]<.8 for r in rows),
        all_suite_below_085=all(r["suite_seconds"]<.85 for r in rows)))


def bridge_crosschecks(evidence):
    """Recompute source endpoints/volatility, including the 240-increment sensitivity."""
    from prop_v15_evidence import bars_for
    from independent_ledger_auditor import bridge_screen
    bars={a:bars_for(a) for a in ("XAUUSD","EURUSD")}
    changed=[];count=0
    for row in evidence["rows"]:
        b=bars[row["asset"]];i,j=map(int,b["t"].searchsorted([row["before"],row["after"]]))
        fields=("bc","bo") if row["side"]==1 else ("ac","ao")
        if (int(b[fields[0]][i]),int(b[fields[1]][j]))!=(row["before_price"],row["after_price"]):
            raise ValueError("V15_bridge_raw_endpoints")
        values=[]
        for k in range(max(1,i-239),i+1):
            if int(b["t"][k])-int(b["t"][k-1])==60000:
                values.append(int(b["bc"][k])-int(b["bc"][k-1]))
        sigma=stdev(values) if len(values)>=60 else None
        r=bridge_screen(row["side"],row["level"],row["before_price"],row["after_price"],
            row["missing_minutes"],sigma,row["adjacent_range"],row["envelope"],
            first=row["before"]+60000,end=row["after"])
        if r["status"]!=row["screen"]["status"]:
            changed.append(dict(trade=row["trade"],before=row["before"],after=row["after"],
                old=row["screen"]["status"],fixed_240=r["status"]))
        count+=1
    result=dict(passed=True,endpoints_recomputed=count,labels_changed_at_240=changed,
        implementation_note="Original estimator includes up to 241 increments; registered <=240 sensitivity is independently recomputed here.",
        financial_replay_changed=False)
    save("bridge-raw-crosscheck.json",result)
    if changed:raise ValueError("V15_bridge_240_window_changes_primary_screen")
    return result


def risk_usage(rows,trades):
    groups=defaultdict(list);rejects=Counter()
    for row in rows:
        rejects.update(row["rejections"])
        for a in row["accepted"]:
            actual=a["risk_state"]["new_stop_risk_milli_usd"]/1000
            groups[row["cell"][:4],a["phase"],trades[a["trade"]]["id"]].append((a["risk_usd"],actual))
    return dict(rejections_overlapping_accounts=dict(rejects),groups=[
        dict(cost=c,phase=p,id=i,admissions=len(v),requested_usd_min=min(x[0] for x in v),
            requested_usd_median=median(x[0] for x in v),requested_usd_max=max(x[0] for x in v),
            actual_stop_usd_min=min(x[1] for x in v),actual_stop_usd_median=median(x[1] for x in v),
            actual_stop_usd_max=max(x[1] for x in v)) for (c,p,i),v in sorted(groups.items())],
        scope="Counts across overlapping hypothetical accounts, not independent live trades.")


def collect():
    evidence=read(JOB/"bridge-evidence.json");selection=read(JOB/"Dev-selection.json")
    check=(read(JOB/"bridge-raw-crosscheck.json") if (JOB/"bridge-raw-crosscheck.json").exists()
        else bridge_crosschecks(evidence))
    if not check["passed"] or check["labels_changed_at_240"]:
        raise ValueError("V15_bridge_raw_crosscheck_not_passed")
    comparison=[];usage={};stress=[];path_audits=[];ledger_audits=[]
    for tag in ("OLHC","OHLC"):
        trades=read(JOB/f"Full-{tag}-PRIMARY-trades.json")
        baseline=[r for r in read(V14/f"{tag}-A-NEXT_QUOTE-accounts.json")
            if r["kind"] in ("CHALLENGE","STANDALONE_FULL")]
        newer=read(JOB/f"Full-{tag}-sizing-accounts.json")
        for label,rows in (("V14_ORIGINAL",baseline),("V14_PRIMARY_BRIDGE",baseline),
            ("V15_CALIBRATED",[r for r in newer if r["profile"]==selection["selected"]["name"]]),
            ("V15_CUSHION",[r for r in newer if r["profile"]=="CUSHION"])):
            for cost in ("SYM","ASYM"):
                selected=[r for r in rows if r["cell"].startswith(cost)]
                recent=[r for r in selected if r["start_msc"]>=DEV_END]
                comparison.append(dict(order=tag,column=label,cost=cost,**metrics(selected),
                    recent_2024_2026=metrics(recent) if recent else None))
            if tag=="OLHC" and label!="V14_PRIMARY_BRIDGE":usage[label]=risk_usage(rows,trades)
        strict_trades=read(JOB/f"Full-{tag}-ALL_UNCERTIFIED-trades.json")
        strict_rows=read(JOB/f"Full-{tag}-strict-accounts.json")
        old={(t["id"],t["parent_source_event"]):t for t in trades}
        changed=[];targeted=[];secondary=[]
        for t in strict_trades:
            original=old[t["id"],t["parent_source_event"]]
            difference=any(t[k]!=original[k] for k in ("exit_msc","exit_price_units","reason"))
            if difference:
                row=dict(id=t["id"],source_event=t["parent_source_event"],side=t["side"],
                    was_uncertain=original["original_source_uncertain"],old_reason=original["reason"],
                    new_reason=t["reason"],old_R=original["reference"]["SYM"]["net_R"],
                    new_R=t["reference"]["SYM"]["net_R"])
                changed.append(row)
                (targeted if row["was_uncertain"] else secondary).append(row)
        stress.append(dict(order=tag,signals=len(strict_trades),changed_exits=len(changed),
            changed_originally_uncertain=len(targeted),secondary_changes=len(secondary),
            originally_uncertain=sum(t["original_source_uncertain"] for t in strict_trades),
            unchanged_uncertain=sum(t["original_source_uncertain"] for t in strict_trades)-len(targeted),
            changes=changed,unit_R={c:sum(t["reference"][c]["net_R"] for t in strict_trades)
                for c in ("SYM","ASYM")},
            models=[dict(cost=c,**metrics([r for r in strict_rows if r["cell"].startswith(c)]))
                for c in ("SYM","ASYM")],mathematical_lower_bound=False))
        for scope,mode in (("Dev","PRIMARY"),("Full","PRIMARY"),("Full","ALL_UNCERTIFIED")):
            r=read(JOB/f"{scope}-{tag}-{mode}-independent-path-audit.json")
            if not r["passed"]:raise ValueError("V15_path_audit_incomplete")
            path_audits.append(dict(scope=scope,order=tag,mode=mode,**r))
        for scope,stage in (("Dev","grid"),("Dev","cushion"),("Full","sizing"),("Full","strict")):
            r=read(JOB/f"{scope}-{tag}-{stage}-audit.json")
            if not r["passed"]:raise ValueError("V15_ledger_audit_incomplete")
            ledger_audits.append(dict(scope=scope,order=tag,stage=stage,accounts=r["accounts"],passed=True))
        for suffix in ("baseline-reuse-audit","sleeve-books-audit"):
            name=f"Full-{tag}-{suffix}.json" if suffix.startswith("baseline") else f"{tag}-{suffix}.json"
            r=read(JOB/name)
            if not r["passed"]:raise ValueError("V15_reuse_or_sleeve_audit_incomplete")
            ledger_audits.append(dict(order=tag,stage=suffix,accounts=r["accounts"],passed=True))
    gap_counts={};uncertain_cohort_gaps={}
    freeze=read(V14/"candidate-freeze.json")
    original_core=[t for t in read(V14/"OLHC-strategy-trades.json") if t["id"] in freeze["candidate_A"]]
    for label,lo,hi in (("DEV",FIRST,DEV_END),("VALIDATION",DEV_END,END)):
        rows=[r for r in evidence["rows"] if lo<=r["entry"]<hi]
        kinds=Counter();minutes=Counter();unique=set()
        for r in rows:
            minutes.update(r["minutes_by_kind"])
            if r["source_uncertain"]:
                unknown=sum(v for k,v in r["minutes_by_kind"].items() if k not in ("DAILY_BREAK","WEEKEND","HOLIDAY"))
                kinds["UNKNOWN_TOTAL_GAP_LT15" if r["missing_minutes"]<15 else "UNKNOWN_TOTAL_GAP_GE15"]+=1
                unique.add((r["asset"],r["before"],r["after"]))
            else:kinds["KNOWN_CLOSURE_ONLY"]+=1
        gap_counts[label]=dict(trade_gap_occurrences=len(rows),gap_classes=dict(kinds),
            unknown_unique_gaps=len(unique),missing_minutes_by_kind=dict(minutes))
        selected=[r for r in rows if original_core[r["trade"]]["source_uncertain"]]
        cohort=Counter()
        for r in selected:
            for kind in r["minutes_by_kind"]:
                cohort["occurrences_with_"+kind]+=1
            if r["source_uncertain"]:
                short=r["missing_minutes"]<15
                hour=datetime.fromtimestamp(r["first_unknown"]/1000,timezone.utc).hour
                night=hour>=22 or hour<7
                cohort[("UNKNOWN_LT15_" if short else "UNKNOWN_GE15_")+("NIGHT" if night else "DAY")]+=1
        uncertain_cohort_gaps[label]=dict(occurrences=len(selected),counts=dict(cohort),
            night_definition="first unknown minute at 22:00–06:59 UTC; descriptive only")
    sleeves=read(JOB/"sleeve-attribution.json")["rows"]
    for s in sleeves:
        s["floating_R_DD"]={}
        for tag in ("OLHC","OHLC"):
            for r in read(JOB/f"{tag}-sleeve-books.json"):
                if r["sleeve_id"]==s["id"]:
                    s["floating_R_DD"][tag+"_"+r["cell"][:4]]=r["max_equity_R_DD"]
    summary=dict(schema="V15-results-v1",verdict="NOT_PROP_QUALIFIED_TIME_FIT_AND_SOURCE_UNCERTAINTY",
        code_freeze_commit="4b426ae",V14_merged="69bc7a6",B_retired=True,
        pricing=dict(Ask_proxy_XAU=.338,Ask_proxy_EUR_pips=1,swap_long_short_SYM=(-40,-40),
            swap_long_short_ASYM=(-45,-5),not_broker_quote_certified=True),
        split=dict(development="2018–2023",historical_validation="2024–13Oct2026",
            already_exposed_prices=True,new_sizing_selection_development_only=True),
        duration=evidence["groups"],gaps=gap_counts,uncertain_cohort_gaps=uncertain_cohort_gaps,
        bridge_crosscheck=check,
        bridge_unknown_screens=dict(Counter(r["screen"]["status"] for r in evidence["rows"] if r["source_uncertain"])),
        deterministic_market_certificates=0,comparison=comparison,risk_usage=usage,
        selection=selection,sleeves=sleeves,all_uncertified_sensitivity=stress,
        path_audits=path_audits,ledger_audits=ledger_audits,
        audit_path_total=sum(r["paths"] for r in path_audits),
        audit_ledger_total=sum(r["accounts"] for r in ledger_audits),
        storage=read(JOB/"dedup-dispositions.json"),space_map=read(JOB/"storage-map.json"),
        tests=read(JOB/("test-ID-preservation-after-runner.json"
            if (JOB/"test-ID-preservation-after-runner.json").exists() else "test-ID-preservation.json")),
        smoke=read(JOB/("smoke-optimized-results.json" if (JOB/"smoke-optimized-results.json").exists() else "smoke-results.json")),
        initial_smoke=read(JOB/"smoke-results.json"),
        private_job=str(JOB),broker_execution=False,actual_payout=False)
    # Large per-file manifests, quotes and ledger records remain at the private locator.
    summary["storage"]["rows"]=[{k:v for k,v in r.items() if k not in ("package",)}
        for r in summary["storage"]["rows"]]
    summary["artifact_hashes"]={p.name:sha(p) for p in JOB.glob("*.json")
        if p.name not in ("summary.json",)}
    save("summary-final.json" if (JOB/"summary.json").exists() else "summary.json",summary)
    raw=json.dumps(summary,ensure_ascii=False,indent=2)
    if len(raw.encode("utf-8"))>1048576:raise ValueError("V15_compact_report_over_1MiB")
    REPORT.with_suffix(".json").write_text(raw,encoding="utf-8")
    render(summary)
    event("V15_report_complete",paths=summary["audit_path_total"],ledgers=summary["audit_ledger_total"])


def render(s):
    out=[
        "# V15 — Khoảng thiếu giá, đóng góp từng nhánh và tốc độ đi vốn",
        "",
        "**Chưa nên mua Challenge.** SYM: mức 1,5× tăng số hoàn tất từ 48 lên 63/105 và giảm "
        "median từ 54 xuống 41,03 tháng; cushion đạt 66/105 và 34,85 tháng. "
        "Vẫn chưa đạt mục tiêu dưới 18 tháng. Stress mọi gap chưa được chứng nhận chỉ đạt 0/105 "
        "hoàn tất: bất định dữ liệu vẫn là rào cản lớn. Candidate B dừng tối ưu, hai nhánh thêm "
        "chỉ được giữ để giải thích kết quả.",
        "",
        "PR #93 đã merge `69bc7a6`; xóa nhánh V14. Đăng ký V15 tại `7ed51a5`, "
        "khóa sizing/code tại `4b426ae` sau khi kiểm toán Development và trước khi đo sizing mới "
        "trên 2024–13/10/2026. Giá và baseline giai đoạn này đã có exposure, không gọi là OOS nguyên vẹn.",
        "",
        "## 1. Có phải việc bỏ lệnh qua gap làm lệch mẫu?",
        "",
        "| Giai đoạn / nhóm | Lệnh | Giữ trung vị (giờ) | Thắng / thua | SYM Net R |",
        "|---|---:|---:|---:|---:|"]
    for period,groups in s["duration"].items():
        for name in ("NO_UNKNOWN_GAP","UNKNOWN_GAP"):
            g=groups[name]
            out.append(f"| {period} / {name} | {g['trades']} | {g['median_hours']:.2f} | {g['wins']}/{g['losses']} | {g['SYM_net_R']:+.2f} |")
    out+=["","Nhóm qua gap giữ lâu hơn, nhưng không phải toàn bộ là lệnh thắng. "
        "Đây là bằng chứng liên hệ giữa thời gian giữ và khả năng gặp gap; không phải chứng minh "
        "nhân quả, cũng không xác nhận rằng SL chưa chạm trong phút bị thiếu.",
        "",
        "| Giai đoạn | Lần giao cắt gap | Chỉ nghỉ đã biết | Gap có thiếu nguồn <15 / >=15 phút | Gap thiếu nguồn riêng biệt |",
        "|---|---:|---:|---:|---:|"]
    for p,r in s["gaps"].items():
        c=r["gap_classes"]
        out.append(f"| {p} | {r['trade_gap_occurrences']} | {c.get('KNOWN_CLOSURE_ONLY',0)} | "
            f"{c.get('UNKNOWN_TOTAL_GAP_LT15',0)} / {c.get('UNKNOWN_TOTAL_GAP_GE15',0)} | {r['unknown_unique_gaps']} |")
    out+=["","Riêng nhóm lệnh uncertain (44 Dev / 12 Validation):","",
        "| Giai đoạn | Lần giao cắt gap | Có phút nghỉ daily | Thiếu nguồn <15 phút đêm/ngày | Thiếu nguồn >=15 phút đêm/ngày |",
        "|---|---:|---:|---:|---:|"]
    for p,r in s["uncertain_cohort_gaps"].items():
        c=r["counts"]
        out.append(f"| {p} | {r['occurrences']} | {c.get('occurrences_with_DAILY_BREAK',0)} | "
            f"{c.get('UNKNOWN_LT15_NIGHT',0)}/{c.get('UNKNOWN_LT15_DAY',0)} | "
            f"{c.get('UNKNOWN_GE15_NIGHT',0)}/{c.get('UNKNOWN_GE15_DAY',0)} |")
    out+=["","Các khoảng có cả rollover và phút thiếu nguồn được tính là gap có thiếu nguồn; "
        "độ dài trên là toàn khoảng. Một gap có thể giao nhiều lệnh; không cộng các lần giao cắt "
        "như số sự kiện độc lập. Cột daily có thể trùng cột thiếu nguồn vì một gap có cả hai. "
        "Đêm được mô tả theo phút thiếu đầu tiên trong 22:00–06:59 UTC, không dùng làm filter. "
        "Chi tiết từng phút/loại nằm trong JSON gốc.",
        "",
        f"Trong {sum(s['bridge_unknown_screens'].values())} lần giao cắt thiếu nguồn toàn kỳ: "
        f"**{s['bridge_unknown_screens'].get('SOURCE_ENVELOPE_EXCLUDES_SL',0)}** được extrema tick native "
        "loại trừ SL có điều kiện trên tập quote đã xuất; "
        f"**{s['bridge_unknown_screens'].get('MODEL_LOW_RISK',0)}** chỉ được mô hình đánh giá rủi ro thấp. "
        "**0 chứng nhận biên giá thị trường tuyệt đối.** Metadata census không tìm được nguồn HTF "
        "standalone được admit; aggregate từ chính M1 thiếu không được coi là nguồn mới.",
        "",
        "Brownian bridge có đuôi xác suất dương; `3σ√t` không phải mức giá tối đa có thể xảy ra. "
        "Dùng khoảng cách có dấu để không bỏ sót endpoint đã xuyên SL. "
        "Mô hình cố định không chọn gap mơ hồ nào, nên cột bridge chính bằng baseline. "
        "Điều đó không có nghĩa đã lấp hoặc chứng nhận toàn bộ dữ liệu.",
        "",
        "Kiểm tra raw riêng đối chiếu lại hai endpoint của mọi gap. Estimator ban đầu lấy tối đa "
        "241 increments thay vì 240 như protocol; sensitivity đúng 240 không đổi bất kỳ nhãn nào, "
        "không đổi đường stress hay kết quả tài chính. Giữ nguyên artifact gốc.",
        "",
        "**Sensitivity bổ sung:** chèn một đường OHLC giả định dùng chung cho mọi vị thế cùng tài sản "
        "tại mọi gap chưa được chứng nhận thị trường. Giữ nguyên các bar quan sát, entry, SL và hạn giữ; "
        "P1 được replay nhân quả. Không gán độc lập mỗi lệnh một giá giả trái ngược nhau; "
        "đây cũng không phải biên dưới toán học của PnL.",
        "",
        "| Order | Tín hiệu / bar giả | Exit đổi (gap gốc / thứ cấp) | Net R SYM / ASYM | Cả hai vòng SYM / ASYM | Payout standalone SYM / ASYM |",
        "|---|---:|---:|---:|---:|---:|"]
    for r in s["all_uncertified_sensitivity"]:
        models=r["models"]
        out.append(f"| {r['order']} | {r['signals']} / 133 | {r['changed_exits']} ({r['changed_originally_uncertain']}/{r['secondary_changes']}) | "
            f"{r['unit_R']['SYM']:+.2f}/{r['unit_R']['ASYM']:+.2f} | "
            f"{models[0]['funded']}/105 / {models[1]['funded']}/105 | "
            f"${models[0]['standalone_payout']:.2f} / ${models[1]['standalone_payout']:.2f} |")
    out+=["","## 2. Từng nhánh đóng góp gì, và tăng risk giúp được bao nhiêu?",
        "",
        "Net R dưới đây là cộng đơn vị R của tín hiệu theo năm ra quyết định, không phải % tài khoản. "
        "Floating R-DD dùng sổ riêng mỗi sleeve ở risk cố định 150 USD, lot được làm tròn xuống; "
        "khác closed cumulative unit-R DD cũng có trong JSON.",
        "",
        "| Nhánh | Asset / family / horizon / exit | ID đầy đủ |",
        "|---|---|---|"]
    for i,r in enumerate(s["sleeves"],1):
        out.append(f"| S{i} | {r['asset']} / {r['family']} / {r['horizon']} / {r['mode']} | `{r['id']}` |")
    for cost in ("SYM","ASYM"):
        out+=["",f"**{cost} — mỗi ô: số tín hiệu / Net R.**","",
            "| Nhánh | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 YTD | Tổng R | Floating R-DD lớn nhất 2 order |",
            "|---|---|---|---|---|---|---|---|---|---|---:|---:|"]
        for i,r in enumerate(s["sleeves"],1):
            cells=" | ".join(f"{a['trades']}/{a['models'][cost]:+.2f}" for a in r["annual"])
            dd=max(v for k,v in r["floating_R_DD"].items() if cost in k)
            out.append(f"| S{i} | {cells} | {r['models'][cost]['total_R']:+.2f} | {dd:.2f} |")
    extra=sum(r["models"]["SYM"]["validation_R"] for r in s["sleeves"][3:])
    out+=["",f"S4+S5 cộng **{extra:+.4f}R SYM** vào 2024–2026: thêm lệnh nhưng làm tổng A "
        "từ +13,8926R xuống +6,1779R. Đây là lý do giữ A, không tiếp tục tìm weights/subset của B.",
        "",
        "V14 xin risk 200 / 175 / 125 USD = 0,40% / 0,35% / 0,25%, có throttle "
        "150 USD ở equity 48k và 90 USD ở 47k. Lot floor khiến số tiền tới SL thực thấp hơn "
        "ngân sách xin. V14 đã dùng đến **6,56362% static DD** và **0,910508% lỗ ngày** "
        "trong 105 starts; không phải mới dùng 3%. Không có breach lịch sử chưa chứng minh tăng risk là an toàn.",
        "",
        "| Chính sách Development | Worst pass cả 2 / 72 | Median chậm nhất (tháng, chỉ cửa sổ pass) | Worst static % | Worst daily % | Eligible |",
        "|---|---:|---:|---:|---:|---|"]
    for r in s["selection"]["cases"]:
        m=r["slowest_conditional_median"]
        out.append(f"| {r['profile']['name']} | {r['worst_completions']} | {m if m is None else round(m,2)} | "
            f"{r['maximum_static']:.4f} | {max(x['worst_daily'] for x in r['models']):.4f} | {r['eligible']} |")
    out+=["","Chọn **D1.5** theo đúng thứ tự đăng ký: đạt target static 7,5–8,2%, "
        "rồi tối đa hóa số hoàn tất yếu nhất qua hai phí/hai order. Risk 300 / 262,50 / 187,50 USD "
        "(0,60% / 0,525% / 0,375%). Equity <=47.500 cap risk 150 USD; <=46.500 cap 75 USD; "
        "open-stop cap 1.000 USD, reserve có funding >45.800 USD, daily realized halt -1.000 USD. "
        "D1 cũng khác V14 vì controls đã đổi. Các mức D2 trở lên không được chọn dù chạy nhanh hơn.",
        "",
        "Cushion là đúng một biến thể: chỉ Vòng 1, arm khi balance lãi >=1.500 USD; "
        "thêm min(20% lãi thực hiện, 250 USD), chỉ khi equity >50k; về balance <=50k thì disarm. "
        "Vòng 2/Funded không đổi. Cả throttle, cap và reserve vẫn áp dụng.",
        "",
        "**Bốn cột so sánh được đặt thành bốn dòng cho mỗi phí/order:**","",
        "| Order / phí | Cột | P1 / 105 | Cả 2 / 105 | Median tháng | Standalone payout USD | Post-challenge payout USD chồng lấn | Daily % | Static % | Breach |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in s["comparison"]:
        med="N/A" if r["median_months"] is None else f"{r['median_months']:.2f}"
        out.append(f"| {r['order']} / {r['cost']} | {r['column']} | {r['phase1']} | {r['funded']} | {med} | "
            f"{r['standalone_payout']:.2f} | {r['payout_windows_usd']:.2f} | "
            f"{r['worst_daily']:.4f} | {r['worst_static']:.4f} | {r['breaches']} |")
    out+=["","Payout post-challenge cộng các tài khoản giả định chồng lấn, **không thể cộng thành thu nhập**. "
        "105 starts là cùng một lịch sử, không phải 105 lần thử độc lập. Median chỉ tính những cửa sổ "
        "hoàn tất; các cửa sổ chưa xong vẫn được giữ là censored, không force-close cuối mẫu. "
        "Riêng 33 starts từ tháng 01/2024 đến 09/2026, cả bốn cột vẫn **0/33 hoàn tất hai vòng** "
        "tính đến 13/10/2026; SYM V15 có 4/33 qua Vòng 1, cushion 6/33. "
        "Median tốt hơn chủ yếu phản ánh những starts cũ, không chứng minh tài khoản mới sẽ pass trong 35 tháng. "
        "Mọi số tiền risk thực theo phase/sleeve nằm trong JSON.",
        "",
        "| Profile OLHC | Chặn cap (tổng các tài khoản chồng lấn) | Chặn reserve | Chặn do thu hoạch Funded |",
        "|---|---:|---:|---:|"]
    for name,u in s["risk_usage"].items():
        c=u["rejections_overlapping_accounts"]
        out.append(f"| {name} | {sum(v for k,v in c.items() if 'CAP' in k)} | "
            f"{sum(v for k,v in c.items() if 'RESERVE' in k)} | {c.get('HARVEST_ENTRY_FREEZE',0)} |")
    out+=["","Các ngưỡng trên là mô hình FTMO 2-Step đã khóa; swap và Ask là proxy, "
        "không phải lịch sử spec/bid-ask của tài khoản đích. Chưa có xác nhận lịch tin, "
        "khớp lệnh broker, owner handover, shadow/demo và chi phí challenge/retry.",
        "",
        "## 3. Đóng sổ 47 cây trùng và dung lượng D/E",
        "",
        "| Nhóm | Số targets | Cây không chồng nhau | Bytes không chồng nhau | Files không chồng nhau | Quyết định |",
        "|---|---:|---:|---:|---:|---|"]
    for group,g in s["storage"]["groups"].items():
        out.append(f"| {group} | {g['targets']} | {g['disjoint_trees']} | {g['disjoint_bytes']:,} | "
            f"{g['disjoint_files']} | {'Nén, thử restore, xóa bản dư' if group.startswith('HISTORICAL') else 'Giữ package/RECORD toàn vẹn'} |")
    z=s["storage"]
    out+=["",f"47 targets = **{z['disjoint_bytes']:,} bytes / {z['disjoint_files']} files** sau bỏ trùng subtree "
        f"(cộng thô có chồng là {z['raw_overlapping_bytes']:,} bytes). Hai cây `charting_library/bundles` "
        f"giảm {z['logical_removed_bytes']:,} bytes logic, archive mới {z['archive_bytes']:,} bytes; "
        f"chênh lệch logic {z['logical_removed_bytes']-z['archive_bytes']:,} bytes trước các receipts nghiên cứu mới. "
        "Không claim số bytes vật lý đã giải phóng.",
        "",
        "45 subtree package nhỏ được KEEP có quyết định rõ, không còn trạng thái chưa xử lý. "
        "RECORD và từng Merkle manifest nằm trong private job. Xóa một phần package trong khi giữ "
        "dist-info sẽ làm sai môi trường; D và E khác volume nên không hardlink xuyên ổ. "
        "Không lặp lại đợt xóa bốn cây V14. Các locator cũ được giữ nguyên trong bằng chứng lịch sử; "
        "disposition mới chỉ tới archive và D canonical.",
        "",
        "Bản đồ dung lượng là snapshot metadata khi các job đang chạy; các ledger được tạo sau snapshot "
        "không nằm trong số tổng này. Giới hạn chỉ hai project roots đã nêu, không phải toàn bộ ổ D/E.",
        "",
        "| Root | Decimal GB | GiB | Files | Folders | Lỗi metadata |",
        "|---|---:|---:|---:|---:|---:|"]
    for name,r in s["space_map"].items():
        t=r["total"]
        out.append(f"| {r['root']} | {t['bytes']/1e9:.3f} | {t['bytes']/1024**3:.3f} | {t['files']} | {t['folders']} | {len(r['errors'])} |")
    out+=["","Các nhóm dung lượng lớn không chồng nhau:","",
        "| Root / nhóm | GB | Files |","|---|---:|---:|"]
    for name,r in s["space_map"].items():
        for g in r["largest_disjoint"][:8]:
            out.append(f"| {name} / {g['group']} | {g['bytes']/1e9:.3f} | {g['files']} |")
    smoke=s["smoke"];tests=s["tests"]
    out+=["","## 4. Kiểm toán, hiệu năng và bàn giao","",
        f"Oracle độc lập về phép tính đã đối soát **{s['audit_path_total']} đường giá** và "
        f"**{s['audit_ledger_total']} sổ** trong V15; gồm cả full baseline được reuse trên cùng "
        "quote grid, mọi policy Development và full, strict stress và năm sleeve riêng. "
        "Đây là cùng implementer/feed, không phải người review hoặc nguồn giá độc lập. "
        "Auditor không import code tính tiền của producer.",
        "",
        f"**{tests['current_ids']} tests PASS, 0 skip**; giữ **{tests['baseline_ids']}/{tests['baseline_ids']} "
        f"ID cũ**, thêm {len(tests['added'])} kiểm thử signed bridge, Ask/extrema, nguồn thiếu, "
        "cushion arm/disarm/phase, lot floor số lẻ, shared path và đối soát sổ.",
        "",
        f"10 fresh-process liên tiếp giữ nguyên 78 smoke tests: suite median/max "
        f"**{smoke['suite_median']:.3f}/{smoke['suite_max']:.3f}s**, wall median/max "
        f"**{smoke['wall_median']:.3f}/{smoke['wall_max']:.3f}s**. "
        f"10/10 wall <0,85s: **{smoke['all_wall_below_085']}**; "
        f"10/10 wall <0,80s: **{smoke['all_wall_below_080']}**. "
        "Giữ mọi mẫu, không retry tìm streak đẹp hay bỏ test. "
        f"Lượt trước tối ưu giữ nguyên trong `smoke-results.json`: max wall "
        f"{s['initial_smoke']['wall_max']:.3f}s, có một lượt vượt 0,85s. "
        "Profile chỉ ra filesystem import probes; runner bỏ đường dẫn import lặp và "
        "chỉ import ThreadPool/subprocess khi chạy parallel. Không đổi modules, test IDs hay assertions.",
        "",
        "Luồng: nguồn V14 immutable → entry/SL/deadline tape cố định → kiểm gap và "
        "shared-path sensitivity → reuse engine V4/V6/costs → scalar Decimal audit → "
        "chọn sizing Dev → commit freeze → full historical evaluation. Không thêm alpha, TP hay exit grid.",
        "",
        "Hậu kiểm kỹ thuật: reuse baseline chỉ sau financial tape parity và đối soát lại sổ; "
        "mô hình xác suất không được nâng thành chứng nhận giá; không phá package để báo thành tích cleanup. "
        "Điểm còn cần xử lý trước Challenge là bằng chứng đường giá/tin tức/broker và tốc độ "
        "kiếm R bền vững, không tiếp tục tăng risk ngoài budget đã thử.",
        "",
        "PR #94 để review, **không merge**. Receipt 3 CI đúng HEAD và đối soát artifact test IDs "
        "được ghi sau push tại `ci-exact-head-reconciliation.json` trong private job; không sửa "
        "HEAD chỉ để tự tham chiếu hash CI trong chính commit đó.",
        "",
        f"JSON gọn: `{REPORT.name}.json` (<1 MiB). Private job: `{JOB}`. "
        "VI Dubber WIP và Trader pin giữ nguyên; không broker, không deploy, không tiền rút thực.",
        "",
        "Nguồn đối chiếu quy tắc hiện hành: FTMO Trading Objectives (2-Step) "
        "https://ftmo.com/en/trading-objectives/ và overnight/Standard FAQ "
        "https://ftmo.com/en/faq/do-i-have-to-close-my-positions-overnight/ . "
        "Các nguồn này không xác nhận dữ liệu giá hoặc khả năng pass tương lai.",
        ""]
    REPORT.with_suffix(".md").write_text("\n".join(out),encoding="utf-8")


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("verify_tests","smoke","collect"))
    p.add_argument("--smoke-label",default="")
    a=p.parse_args()
    smoke(a.smoke_label) if a.stage=="smoke" else globals()[a.stage]()
