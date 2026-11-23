"""Strictly read-only FTMO Free Trial Demo symbol spec & live spread probe (OrderSend = 0, isolated portable MT5).

Never logs, prints, or persists credentials; records only SHA256(login|server) account binding hash.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time

import ftmo_connection as conn
from ftmo_free_trial_adapter import account_hash

ALLOW_LIVE_ORDER_SEND = False

SPEC_KEYS = (
    "name", "description", "path", "digits", "point",
    "trade_contract_size", "trade_tick_size", "trade_tick_value",
    "trade_tick_value_profit", "trade_tick_value_loss",
    "volume_min", "volume_step", "volume_max",
    "trade_stops_level", "trade_freeze_level",
    "swap_long", "swap_short", "swap_mode", "swap_rollover3days",
    "trade_mode", "trade_calc_mode", "margin_initial", "margin_maintenance",
    "currency_base", "currency_profit", "currency_margin",
    "spread", "spread_float", "filling_mode",
)

DEFAULT_TARGETS = (
    "US100.cash", "GER40.cash", "BTCUSD", "US500.cash",
    "XAUUSD", "USDJPY", "GBPUSD", "EURUSD",
)


def _finite_or_none(v):
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def _resolve_symbol(sdk, requested: str) -> str | None:
    info = sdk.symbol_info(requested)
    if info is not None:
        return requested
    # Try safe prefix discovery only if exact name not present
    base = requested.split(".")[0].upper()
    candidates = sdk.symbols_get(f"*{base}*") or ()
    for item in candidates:
        if item.name.upper().startswith(base):
            return item.name
    return None


def probe_ftmo_specs(credentials_path: Path, targets: tuple[str, ...] = DEFAULT_TARGETS, sample_seconds: int = 15) -> dict:
    """Connect to isolated read-only FTMO Demo portable terminal and capture specs + short live spread sample."""
    import MetaTrader5 as mt5

    vals = conn.credentials(credentials_path)
    if vals is None:
        raise ValueError("MISSING_FTMO_CREDENTIALS")

    started_utc = datetime.now(timezone.utc).isoformat()
    with conn.trial_session(vals, sdk=mt5) as terminal_path:
        acct = mt5.account_info()
        if acct is None or acct.trade_mode != 0 or acct.currency != "USD":
            raise ValueError("VERIFIED_FTMO_DEMO_USD_REQUIRED")
        acct_d = acct._asdict()
        binding = {
            "account_hash": account_hash(acct_d["login"], acct_d["server"]),
            "server": acct_d["server"],
            "company": acct_d.get("company"),
            "currency": acct_d["currency"],
            "leverage": acct_d.get("leverage"),
            "balance": acct_d.get("balance"),
            "trade_mode": "DEMO",
            "order_send_count": 0,
            "execution_capability": False,
        }

        resolved = {}
        specs = {}
        samples = {}
        for req in targets:
            actual = _resolve_symbol(mt5, req)
            resolved[req] = actual
            if actual is None:
                specs[req] = {"status": "NOT_FOUND"}
                continue
            mt5.symbol_select(actual, True)
            samples[req] = []

        # Allow initial quote subscription warm-up
        time.sleep(1.5)
        t_end = time.monotonic() + max(3, int(sample_seconds))
        while time.monotonic() < t_end:
            for req, actual in resolved.items():
                if actual is None:
                    continue
                tk = mt5.symbol_info_tick(actual)
                if tk is not None and tk.bid > 0 and tk.ask >= tk.bid:
                    samples[req].append({
                        "time_msc": int(tk.time_msc),
                        "bid": float(tk.bid),
                        "ask": float(tk.ask),
                        "spread": round(float(tk.ask - tk.bid), 8),
                    })
            time.sleep(0.25)

        for req, actual in resolved.items():
            if actual is None:
                continue
            info = mt5.symbol_info(actual)
            if info is None:
                specs[req] = {"status": "INFO_UNAVAILABLE", "actual_symbol": actual}
                continue
            d = info._asdict()
            row = {k: _finite_or_none(d.get(k)) for k in SPEC_KEYS}
            row["actual_symbol"] = actual
            row["status"] = "CAPTURED"

            tick = mt5.symbol_info_tick(actual)
            ref_ask = float(tick.ask) if (tick is not None and tick.ask > 0) else None
            ref_bid = float(tick.bid) if (tick is not None and tick.bid > 0) else None
            row["last_bid"] = ref_bid
            row["last_ask"] = ref_ask

            # Exact broker-reported margin for 1.00 lot and volume_min (pure read-only query)
            if ref_ask is not None:
                m_one = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, actual, 1.0, ref_ask)
                m_min = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, actual, float(row["volume_min"] or 0.01), ref_ask)
                row["margin_1lot_usd"] = round(float(m_one), 4) if m_one is not None else None
                row["margin_minlot_usd"] = round(float(m_min), 4) if m_min is not None else None
                # Also compute profit for a +1.0 price move on 1.0 lot via broker engine
                p_one = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, actual, 1.0, ref_ask, ref_ask + 1.0)
                row["profit_per_1pt_1lot_usd"] = round(float(p_one), 6) if p_one is not None else None

            s_list = sorted(x["spread"] for x in samples.get(req, []))
            if s_list:
                n = len(s_list)
                row["spread_sample"] = {
                    "n_obs": n,
                    "min": s_list[0],
                    "p50": s_list[n // 2],
                    "p95": s_list[min(n - 1, int(0.95 * n))],
                    "max": s_list[-1],
                }
            else:
                row["spread_sample"] = {"n_obs": 0}
            specs[req] = row

    finished_utc = datetime.now(timezone.utc).isoformat()
    out = {
        "schema": "ftmo-readonly-spec-probe-v1",
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "sample_seconds": int(sample_seconds),
        "order_send_count": 0,
        "account_binding": binding,
        "resolved_symbols": resolved,
        "specs": specs,
    }
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials-file", type=Path, default=Path("config/ftmo_free_trial.env"))
    parser.add_argument("--seconds", type=int, default=15)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    res = probe_ftmo_specs(args.credentials_file, sample_seconds=args.seconds)
    args.output.mkdir(parents=True, exist_ok=True)
    target_file = args.output / "ftmo_indices_spec_snapshot.json"
    body = json.dumps(res, indent=2, ensure_ascii=False)
    target_file.write_text(body, encoding="utf-8", newline="\n")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    (args.output / "ftmo_indices_spec_snapshot.sha256").write_text(f"{digest}  ftmo_indices_spec_snapshot.json\n", encoding="utf-8")

    b = res["account_binding"]
    print(f"FTMO_PROBE_OK server={b['server']} lev=1:{b['leverage']} bal={b['balance']} hash={b['account_hash'][:12]} sha256={digest[:12]}", flush=True)
    for req, sp in res["specs"].items():
        if sp.get("status") != "CAPTURED":
            print(f"  {req:12s} | {sp.get('status')}", flush=True)
            continue
        ss = sp["spread_sample"]
        print(
            f"  {req:12s} ({sp['actual_symbol']:10s}) | cs={sp['trade_contract_size']} tick={sp['trade_tick_size']}/{sp['trade_tick_value']} "
            f"| 1pt1lot=${sp.get('profit_per_1pt_1lot_usd')} | vol={sp['volume_min']}/{sp['volume_step']}/{sp['volume_max']} "
            f"| mgn1=${sp.get('margin_1lot_usd')} | stops={sp['trade_stops_level']} | swap={sp['swap_long']}/{sp['swap_short']} "
            f"| spr_p50={ss.get('p50')} (n={ss.get('n_obs')}, p95={ss.get('p95')})",
            flush=True,
        )


if __name__ == "__main__":
    main()
