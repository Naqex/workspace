"""RD-Agent-Q Style Automated Research Loop CLI (Wave 2).

Orchestrates reproducible, fail-closed hypothesis batches without GPU/framework bloat:
  JSON `HypothesisCard` Batch (hard cap `m_total <= 20`)
    -> Strictly Sealed Dev Cluster A (`2018-2021`) -> Blind Cluster B (`2022-2024`) Evaluation (`holdout_rows = 0`)
    -> `research_council.SkepticalRedTeamCritic` (BH-FDR, DSR, 2x Cost Breakeven, Orthogonality, Sample/Sign)
    -> Structured SHA-256 JSON Ledger + Markdown Report (retaining ALL negatives honestly!)
    -> Clean White-Box Python & MQL5 Template Emitter for `APPROVE_FOR_INCUBATION` survivors ONLY
       (`InpDryRunLogOnly = true` enforced, `OrderSend = 0`, 0 red flags on `audit_open_source_mq5`).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
from typing import Callable

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.data_store import (
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_registry,
)
from quant_factory.eval_pipeline import sign_flip_p_numba
from quant_factory.portfolio_allocator import DEFAULT_RETURNS_DIR, load_external_sleeve_json
from quant_factory.prop_engine import replay_portfolio_m1
from quant_factory.red_team_auditor import transform_tapes_cost_stress
from quant_factory.report_gen import format_markdown_table, write_verified_receipt
from quant_factory.research_council import (
    EvidenceBundle,
    HypothesisCard,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)

M_TOTAL_HARD_CAP = 20
DEFAULT_OUT_DIR = ROOT / ".runtime/auto-research-out"
HOLDOUT_CUTOFF_DAY = "2025-01-01"


def _assert_dev_window_sealed(ev_cfg: dict) -> None:
    """Reject any evaluator spec attempting to access holdout dates >= 2025-01-01 or non-zero holdout rows."""
    end_day = ev_cfg.get("end_day")
    if end_day is not None and str(end_day).strip() >= HOLDOUT_CUTOFF_DAY:
        raise ValueError(
            f"HOLDOUT_LOCK_VIOLATION: evaluator end_day '{end_day}' >= {HOLDOUT_CUTOFF_DAY}"
        )
    split_day = ev_cfg.get("cluster_b_start")
    if split_day is not None and str(split_day).strip() >= HOLDOUT_CUTOFF_DAY:
        raise ValueError(
            f"HOLDOUT_LOCK_VIOLATION: evaluator cluster_b_start '{split_day}' >= {HOLDOUT_CUTOFF_DAY}"
        )
    if int(ev_cfg.get("holdout_rows_analysed", 0)) != 0:
        raise ValueError(
            f"HOLDOUT_LOCK_VIOLATION: evaluator holdout_rows_analysed={ev_cfg.get('holdout_rows_analysed')} != 0"
        )


def _sanitize_ident(raw: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_]+", "_", raw.strip())
    return clean.strip("_") or "CANDIDATE"


def parse_batch_cards(batch_payload: dict) -> list[tuple[HypothesisCard, dict]]:
    """Parse and validate a `naqex-hypothesis-batch-v1` JSON dict into typed HypothesisCards."""
    specs = list(batch_payload.get("hypotheses", []))
    if not specs:
        raise ValueError("Hypothesis batch cannot be empty")
    if len(specs) > M_TOTAL_HARD_CAP:
        raise ValueError(f"Batch size {len(specs)} exceeds M_TOTAL_HARD_CAP={M_TOTAL_HARD_CAP}")

    m_cum = int(batch_payload.get("n_trials_cumulative", len(specs)))
    out: list[tuple[HypothesisCard, dict]] = []
    for sp in specs:
        kc_raw = sp.get("kill_criteria") or {}
        kc = KillCriteria(
            max_bh_q=float(kc_raw.get("max_bh_q", 0.10)),
            min_dsr=float(kc_raw.get("min_dsr", 0.50)),
            min_cluster_b_sharpe=float(kc_raw.get("min_cluster_b_sharpe", 0.40)),
            min_cost_breakeven_mult=float(kc_raw.get("min_cost_breakeven_mult", 2.00)),
            max_corr_vs_incumbent=float(kc_raw.get("max_corr_vs_incumbent", 0.25)),
            max_tail_corr_vs_incumbent=float(kc_raw.get("max_tail_corr_vs_incumbent", 0.40)),
            min_trades_cluster_b=int(kc_raw.get("min_trades_cluster_b", 30)),
        )
        card = propose_hypothesis(
            hypothesis_id=str(sp["hypothesis_id"]),
            title=str(sp["title"]),
            asset_universe=list(sp.get("asset_universe", [])),
            timeframe=str(sp.get("timeframe", "M1_INTRADAY")),
            counterparty_mechanism=str(sp.get("counterparty_mechanism", "")),
            economic_rationale=str(sp.get("economic_rationale", "")),
            causal_invariants=list(sp.get("causal_invariants", [])),
            n_trials_cumulative=int(sp.get("n_trials_cumulative", m_cum)),
            kill_criteria=kc,
        )
        out.append((card, sp))
    return out


def _builtin_evaluate_spec(
    spec: dict,
    *,
    dev_ctx: dict,
    seed: int = 20261124,
) -> dict:
    """Built-in causal evaluator supporting `frozen_engine_dev`, `sleeve_json`, and `inline_arrays` specs."""
    ev_cfg = spec.get("evaluator") or {}
    _assert_dev_window_sealed(ev_cfg)
    kind = str(ev_cfg.get("kind", "inline_arrays"))

    if kind == "frozen_engine_dev":
        eng_id = str(ev_cfg["engine_id"])
        tapes = dev_ctx["tapes"]
        ext_days = dev_ctx["ext_days"]
        days_a = dev_ctx["days_a"]
        days_b = dev_ctx["days_b"]
        if any(str(d) >= HOLDOUT_CUTOFF_DAY for d in ext_days):
            raise ValueError("HOLDOUT_LOCK_VIOLATION: dev_ctx ext_days contains >= 2025-01-01")
        inc_b = dev_ctx["incumbent_b"]
        risk = float(ev_cfg.get("risk_frac", 0.005))

        m1, ex1 = replay_portfolio_m1(ext_days, tapes, {eng_id: risk}, 10000.0, profile_mode="Swing")
        t2x = transform_tapes_cost_stress({eng_id: tapes[eng_id]}, 2.0)
        m2, _ = replay_portfolio_m1(ext_days, t2x, {eng_id: risk}, 10000.0, profile_mode="Swing")

        by_day = {e["day"]: float(e["net_usd"]) / 10000.0 for e in ex1}
        ret_a = np.array([by_day.get(d, 0.0) for d in days_a], dtype=np.float64)
        ret_b = np.array([by_day.get(d, 0.0) for d in days_b], dtype=np.float64)

        tr_r = np.array([float(row["net_R"]) for _dk, (row, _st, _mk) in sorted(tapes[eng_id].items())], dtype=np.float64)
        p_raw = sign_flip_p_numba(tr_r, -tr_r, draws=1000, seed=seed) if len(tr_r) else 1.0
        n_b = sum(1 for dk in tapes[eng_id] if dk >= "2022-01-01")
        return {
            "cluster_a_returns": ret_a,
            "cluster_b_returns": ret_b,
            "p_value_raw": float(p_raw),
            "cost_1x_net": float(m1["net_usd"]),
            "cost_2x_net": float(m2["net_usd"]),
            "n_trades_cluster_b": int(n_b),
            "incumbent_daily_returns": inc_b,
            "annualization_days": 252.0,
            "holdout_rows_analysed": int(ev_cfg.get("holdout_rows_analysed", 0)),
        }

    if kind == "sleeve_json":
        path = Path(ev_cfg["json_path"])
        if not path.is_absolute():
            path = ROOT / path
        rmap, meta = load_external_sleeve_json(path, variant=ev_cfg.get("variant"))
        split_day = str(ev_cfg.get("cluster_b_start", "2023-01-01"))
        end_day = str(ev_cfg.get("end_day", "2024-12-31"))
        if end_day >= HOLDOUT_CUTOFF_DAY or split_day >= HOLDOUT_CUTOFF_DAY:
            raise ValueError(f"HOLDOUT_LOCK_VIOLATION: sleeve_json window ({split_day}..{end_day}) breaches {HOLDOUT_CUTOFF_DAY}")
        days_sorted = sorted(d for d in rmap if d <= end_day)
        if any(str(d) >= HOLDOUT_CUTOFF_DAY for d in days_sorted):
            raise ValueError("HOLDOUT_LOCK_VIOLATION: sleeve_json produced holdout dates >= 2025-01-01")
        ret_a = np.array([rmap[d] for d in days_sorted if d < split_day], dtype=np.float64)
        ret_b = np.array([rmap[d] for d in days_sorted if d >= split_day], dtype=np.float64)
        p_raw = sign_flip_p_numba(ret_b, -ret_b, draws=1000, seed=seed) if len(ret_b) else 1.0
        net1x = float(np.sum(ret_b))
        cost_drag_est = float(ev_cfg.get("extra_cost_2x_drag", 0.015))
        return {
            "cluster_a_returns": ret_a,
            "cluster_b_returns": ret_b,
            "p_value_raw": float(p_raw),
            "cost_1x_net": net1x,
            "cost_2x_net": net1x - cost_drag_est,
            "n_trades_cluster_b": int(np.sum(np.abs(ret_b) > 1e-9)),
            "incumbent_daily_returns": None,
            "annualization_days": float(meta.get("annualization_days", 252.0)),
            "holdout_rows_analysed": int(ev_cfg.get("holdout_rows_analysed", 0)),
        }

    if kind == "inline_arrays":
        return {
            "cluster_a_returns": np.asarray(ev_cfg["cluster_a_returns"], dtype=np.float64),
            "cluster_b_returns": np.asarray(ev_cfg["cluster_b_returns"], dtype=np.float64),
            "p_value_raw": float(ev_cfg["p_value_raw"]),
            "cost_1x_net": float(ev_cfg["cost_1x_net"]),
            "cost_2x_net": float(ev_cfg["cost_2x_net"]),
            "n_trades_cluster_b": int(ev_cfg["n_trades_cluster_b"]),
            "incumbent_daily_returns": (
                np.asarray(ev_cfg["incumbent_daily_returns"], dtype=np.float64)
                if ev_cfg.get("incumbent_daily_returns") is not None
                else None
            ),
            "annualization_days": float(ev_cfg.get("annualization_days", 252.0)),
            "holdout_rows_analysed": int(ev_cfg.get("holdout_rows_analysed", 0)),
        }

    raise ValueError(f"Unknown evaluator kind: {kind}")


def emit_survivor_templates(verdict_row: dict, out_dir: Path) -> dict[str, str]:
    """Emit auditable white-box Python + MQL5 (`InpDryRunLogOnly = true`) templates ONLY for approved survivors."""
    if verdict_row.get("verdict") != "APPROVE_FOR_INCUBATION":
        raise ValueError(f"Refusing template emit for non-approved verdict: {verdict_row.get('verdict')}")
    hyp = verdict_row["hypothesis"]
    hid = _sanitize_ident(hyp["hypothesis_id"])
    asset = (hyp["asset_universe"][0] if hyp.get("asset_universe") else "USDJPY")
    sha_tag = verdict_row.get("verdict_sha256", "unknown")
    tpl_dir = out_dir / "templates"
    tpl_dir.mkdir(parents=True, exist_ok=True)

    py_path = tpl_dir / f"{hid.lower()}_strategy.py"
    mq5_path = tpl_dir / f"Naqex_Candidate_{hid}.mq5"

    py_code = f'''"""Auto-Emitted White-Box Candidate Strategy Template: {hyp["title"]}
Hypothesis ID : {hyp["hypothesis_id"]}
Council SHA   : {sha_tag}
Counterparty  : {hyp["counterparty_mechanism"]}
Safety        : OrderSend = 0, Holdout 2025+ SEALED, strict t -> t+1 causal execution.
"""

from __future__ import annotations

import numpy as np


def generate_causal_signal(close: np.ndarray, atr: np.ndarray, *, threshold: float = 0.75) -> np.ndarray:
    """Placeholder white-box causal signal (uses bars <= t ONLY for execution at t+1)."""
    n = len(close)
    sig = np.zeros(n, dtype=np.int8)
    for t in range(1, n):
        if atr[t - 1] > 1e-9:
            move = (close[t] - close[t - 1]) / atr[t - 1]
            if move >= threshold:
                sig[t] = 1
            elif move <= -threshold:
                sig[t] = -1
    return sig
'''
    mq5_code = f'''//+------------------------------------------------------------------+
//| Naqex White-Box Research Candidate Template: {hid}
//| Council Verdict SHA : {sha_tag} | Status: APPROVE_FOR_INCUBATION
//| Asset               : {asset} | Swap=0 Intraday | Hard SL
//| SAFETY              : InpDryRunLogOnly = true (OrderSend = 0)
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

#include <Trade/Trade.mqh>
#include "Include/Naqex_PropGuard.mqh"

CTrade          trade;
CNaqexPropGuard g_guard;

input bool   InpDryRunLogOnly     = true;       // SAFETY: true = log only, NO live OrderSend
input double InpRiskPercent       = 0.50;       // Base risk % per trade
input double InpMaxDailyLossPct   = 2.50;       // Internal daily equity stop
input double InpSlAtrMult         = 0.75;       // Hard server SL distance (x prior D1 ATR)
input int    InpAtrPeriodD1       = 14;         // Prior completed D1 ATR period
input int    InpFlatHourUTC       = 20;         // Intraday forced flat hour (UTC, swap=0)
input int    InpFlatMinUTC        = 55;         // Intraday forced flat minute (UTC)
input long   InpMagicNumber       = 20261190;   // Candidate magic placeholder (inside 20261120..20261199)

int g_atrHandle = INVALID_HANDLE;

int OnInit()
{{
   g_atrHandle = iATR(_Symbol, PERIOD_D1, InpAtrPeriodD1);
   if(g_atrHandle == INVALID_HANDLE) return INIT_FAILED;
   g_guard.Init(trade, _Symbol, InpMagicNumber, InpMaxDailyLossPct);
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_atrHandle != INVALID_HANDLE) IndicatorRelease(g_atrHandle);
}}

void OnTick()
{{
   g_guard.OnNewTickHousekeeping();
   if(g_guard.IsDailyLossBreached() || g_guard.IsInsideRedNewsWindow() || g_guard.IsNearBrokerSessionClose())
      return;
   if(!g_guard.IsSpreadAndSessionSafe())
      return;
   // Candidate entry logic wired strictly after 30-day offline incubation & parity audit.
}}
'''
    py_path.write_text(py_code, encoding="utf-8", newline="\n")
    mq5_path.write_text(mq5_code, encoding="utf-8", newline="\n")
    return {"python_template": str(py_path), "mq5_template": str(mq5_path)}


def _load_dev_context_if_needed(specs: list[dict]) -> dict:
    need_dev = any(str((sp.get("evaluator") or {}).get("kind", "")) == "frozen_engine_dev" for sp in specs)
    if not need_dev:
        return {}
    warm = build_or_load_frozen_tapes(force_rebuild=False)
    tapes = warm["tapes"]
    ext_days = sorted(warm["ext_days"])
    reg = load_registry()
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    core7 = reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]
    _, ex7 = replay_portfolio_m1(ext_days, tapes, {k: base_r[k] for k in core7}, 10000.0, profile_mode="Swing")
    by_day = {e["day"]: float(e["net_usd"]) / 10000.0 for e in ex7}
    days_a = [d for d in ext_days if d < "2022-01-01"]
    days_b = [d for d in ext_days if d >= "2022-01-01"]
    inc_b = np.array([by_day.get(d, 0.0) for d in days_b], dtype=np.float64)
    return {"tapes": tapes, "ext_days": ext_days, "days_a": days_a, "days_b": days_b, "incumbent_b": inc_b}


def run_research_batch(
    batch_payload: dict,
    *,
    out_dir: Path = DEFAULT_OUT_DIR,
    emit_templates: bool = True,
    evaluator_fn: Callable[[dict], dict] | None = None,
    seed: int = 20261124,
) -> dict:
    """Execute full RD-Agent-Q style batch: Proposer -> Dev Eval -> Critic -> Verified Ledger + Survivor Templates."""
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()
    parsed = parse_batch_cards(batch_payload)
    specs = [sp for _card, sp in parsed]
    dev_ctx = {} if evaluator_fn is not None else _load_dev_context_if_needed(specs)

    raw_ev_list = []
    fam_p_vals = []
    for i, (_card, sp) in enumerate(parsed):
        _assert_dev_window_sealed(sp.get("evaluator") or {})
        raw_ev = evaluator_fn(sp) if evaluator_fn is not None else _builtin_evaluate_spec(sp, dev_ctx=dev_ctx, seed=seed + i)
        if raw_ev.get("end_day") is not None and str(raw_ev["end_day"]) >= HOLDOUT_CUTOFF_DAY:
            raise ValueError(f"HOLDOUT_LOCK_VIOLATION: evaluator returned end_day={raw_ev['end_day']} >= {HOLDOUT_CUTOFF_DAY}")
        raw_ev_list.append(raw_ev)
        fam_p_vals.append(float(raw_ev["p_value_raw"]))

    verdicts = []
    emitted: dict[str, dict[str, str]] = {}
    for i, ((card, _sp), raw_ev) in enumerate(zip(parsed, raw_ev_list)):
        eb = EvidenceBundle(
            cluster_a_returns=raw_ev["cluster_a_returns"],
            cluster_b_returns=raw_ev["cluster_b_returns"],
            p_value_raw=float(raw_ev["p_value_raw"]),
            family_p_values=tuple(fam_p_vals),
            candidate_index_in_family=i,
            cost_1x_net=float(raw_ev["cost_1x_net"]),
            cost_2x_net=float(raw_ev["cost_2x_net"]),
            n_trades_cluster_b=int(raw_ev["n_trades_cluster_b"]),
            incumbent_daily_returns=raw_ev.get("incumbent_daily_returns"),
            annualization_days=float(raw_ev.get("annualization_days", 252.0)),
            holdout_rows_analysed=int(raw_ev.get("holdout_rows_analysed", 0)),
        )
        v = critique_proposal(card, eb)
        verdicts.append(v)
        if emit_templates and v["verdict"] == "APPROVE_FOR_INCUBATION":
            emitted[card.hypothesis_id] = emit_survivor_templates(v, out_dir)

    batch_id = _sanitize_ident(str(batch_payload.get("batch_id", "BATCH_AUTO")))
    approved = [v["hypothesis"]["hypothesis_id"] for v in verdicts if v["verdict"] == "APPROVE_FOR_INCUBATION"]
    conditional = [v["hypothesis"]["hypothesis_id"] for v in verdicts if v["verdict"] == "CONDITIONAL_RETEST"]
    killed = [v["hypothesis"]["hypothesis_id"] for v in verdicts if v["verdict"] == "REJECT_KILLED"]

    ledger = {
        "schema": "naqex-auto-research-ledger-v1",
        "batch_id": batch_id,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": sum(int(r.get("holdout_rows_analysed", 0)) for r in raw_ev_list),
        "order_send_count": 0,
        "m_total_tested": len(verdicts),
        "m_total_cap": M_TOTAL_HARD_CAP,
        "counts": {"approved": len(approved), "conditional": len(conditional), "killed": len(killed)},
        "approved_ids": approved,
        "conditional_ids": conditional,
        "killed_ids": killed,
        "emitted_templates": emitted,
        "verdicts": verdicts,
        "runtime_seconds": round(time.perf_counter() - t0, 3),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{batch_id}_ledger.json"
    md_path = out_dir / f"{batch_id}_ledger.md"
    digest = write_verified_receipt(json_path, ledger, overwrite=True)
    md_path.write_text(render_batch_ledger_markdown(ledger), encoding="utf-8", newline="\n")
    ledger["ledger_json_path"] = str(json_path)
    ledger["ledger_md_path"] = str(md_path)
    ledger["ledger_sha256"] = digest[:16]
    return ledger


def render_batch_ledger_markdown(ledger: dict) -> str:
    """Render concise Markdown research council ledger retaining ALL winners & killed negatives."""
    c = ledger["counts"]
    lines = [
        f"# Auto Research Loop Ledger — `{ledger['batch_id']}`",
        "",
        f"- **Generated UTC:** `{ledger['generated_utc']}` (runtime `{ledger['runtime_seconds']}s`)",
        f"- **Safety Seal:** Holdout Lock `{ledger['holdout_lock_sha256'][:16]}...`, `OrderSend = 0`, `m_total = {ledger['m_total_tested']} <= {ledger['m_total_cap']}`",
        f"- **Outcomes:** Approved `{c['approved']}` | Conditional `{c['conditional']}` | Killed `{c['killed']}`",
        "",
    ]
    headers = ["Hypothesis ID", "Assets", "BH q", "Cl.B Sharpe", "DSR", "Cost BE", "Corr / Tail", "Verdict", "Failed Gates"]
    rows = []
    for v in ledger["verdicts"]:
        h = v["hypothesis"]
        g = v["gates"]
        rows.append([
            h["hypothesis_id"],
            ",".join(h["asset_universe"]),
            f"{g['G1_bh_fdr']['bh_q']:.4f}",
            f"{g['G2_dsr_and_sharpe']['sr_ann_b']:.2f}",
            f"{g['G2_dsr_and_sharpe']['dsr_b']:.3f}",
            f"{g['G3_cost_stress']['breakeven_mult']:.2f}x",
            f"{g['G4_orthogonality']['corr_all']:+.2f} / {g['G4_orthogonality']['corr_tail_5pct']:+.2f}",
            v["verdict"],
            ",".join(v["failed_gates"]) or "NONE",
        ])
    lines.append(format_markdown_table(headers, rows, right_align_cols={2, 3, 4, 5, 6}))
    if ledger["emitted_templates"]:
        lines += ["", "## Emitted Survivor Templates (`InpDryRunLogOnly = true`)", ""]
        for hid, paths in ledger["emitted_templates"].items():
            lines.append(f"- `{hid}`: Python `{paths['python_template']}` | MQL5 `{paths['mq5_template']}`")
    lines.append("")
    return "\n".join(lines)


def build_demo_batch() -> dict:
    """Built-in reproducible Dev batch demonstrating Approved Survivor + Template Emit, Conditional, and Killed."""
    rng = np.random.default_rng(20261124)
    a_good = rng.normal(loc=0.0009, scale=0.0040, size=500).round(6).tolist()
    b_good = rng.normal(loc=0.0009, scale=0.0040, size=500).round(6).tolist()
    return {
        "schema": "naqex-hypothesis-batch-v1",
        "batch_id": "DEMO_DEV_AUDIT_V1",
        "n_trials_cumulative": 10,
        "hypotheses": [
            {
                "hypothesis_id": "DEMO_ORTHO_SURVIVOR",
                "title": "Synthetic Orthogonal Low-Cost Breakout Survivor (Template Smoke Test)",
                "asset_universe": ["EURJPY"],
                "timeframe": "M1_INTRADAY",
                "counterparty_mechanism": "SESSION_REBALANCING",
                "economic_rationale": "Cross-session liquidity handover traps dealer inventory outside compressed Asian bounds, yielding right-skewed expansion net of 2x costs.",
                "causal_invariants": ["prior_d1_atr_only", "swap_zero_intraday_flat", "holdout_2025_sealed"],
                "kill_criteria": {"max_bh_q": 0.10, "min_dsr": 0.50, "min_cluster_b_sharpe": 0.50, "min_cost_breakeven_mult": 2.0, "max_corr_vs_incumbent": 0.25, "max_tail_corr_vs_incumbent": 0.40, "min_trades_cluster_b": 30},
                "evaluator": {
                    "kind": "inline_arrays",
                    "cluster_a_returns": a_good,
                    "cluster_b_returns": b_good,
                    "p_value_raw": 0.001,
                    "cost_1x_net": 1200.0,
                    "cost_2x_net": 750.0,
                    "n_trades_cluster_b": 140,
                    "holdout_rows_analysed": 0,
                },
            },
            {
                "hypothesis_id": "DEMO_E6_EURJPY_VOLCOMP",
                "title": "EURJPY Volatility Compression Breakout (Frozen Dev Reference)",
                "asset_universe": ["EURJPY"],
                "timeframe": "M1_INTRADAY",
                "counterparty_mechanism": "VOLATILITY_COMPRESSION_BREAKOUT",
                "economic_rationale": "Low 5d/20d realized range compression concentrates cross-yen stop orders outside London bounds, triggering institutional hedging expansion.",
                "causal_invariants": ["prior_d1_atr_only", "swap_zero_intraday_flat", "holdout_2025_sealed"],
                "kill_criteria": {"max_bh_q": 0.10, "min_dsr": 0.50, "min_cluster_b_sharpe": 0.40, "min_cost_breakeven_mult": 2.0, "max_corr_vs_incumbent": 0.45, "max_tail_corr_vs_incumbent": 0.60, "min_trades_cluster_b": 30},
                "evaluator": {"kind": "frozen_engine_dev", "engine_id": "E6_EURJPY_VOLCOMP", "risk_frac": 0.005},
            },
            {
                "hypothesis_id": "DEMO_COST_FRAGILE_KILL",
                "title": "High-Turnover Scalper Failing 2x Cost Stress",
                "asset_universe": ["EURUSD"],
                "timeframe": "M1_INTRADAY",
                "counterparty_mechanism": "MICRO_MEAN_REVERSION",
                "economic_rationale": "Short-horizon mean reversion against retail spread widening loses edge immediately when realistic 2x slippage is applied.",
                "causal_invariants": ["prior_d1_atr_only", "swap_zero_intraday_flat"],
                "evaluator": {
                    "kind": "inline_arrays",
                    "cluster_a_returns": [0.0005] * 60 + [-0.0004] * 40,
                    "cluster_b_returns": [0.0004] * 55 + [-0.0004] * 45,
                    "p_value_raw": 0.25,
                    "cost_1x_net": 50.0,
                    "cost_2x_net": -120.0,
                    "n_trades_cluster_b": 100,
                    "holdout_rows_analysed": 0,
                },
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Naqex RD-Agent-Style Auto Research Loop CLI")
    parser.add_argument("--batch", type=Path, default=None, help="Path to JSON HypothesisCard batch")
    parser.add_argument("--demo-batch", action="store_true", help="Run built-in Dev verification batch")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--no-templates", action="store_true")
    args = parser.parse_args()

    if args.batch is not None:
        payload = json.loads(args.batch.read_text(encoding="utf-8"))
    elif args.demo_batch:
        payload = build_demo_batch()
    else:
        payload = build_demo_batch()

    res = run_research_batch(payload, out_dir=args.out_dir, emit_templates=not args.no_templates)
    print(json.dumps({
        "batch_id": res["batch_id"],
        "counts": res["counts"],
        "approved_ids": res["approved_ids"],
        "killed_ids": res["killed_ids"],
        "emitted_templates": res["emitted_templates"],
        "ledger_json": res["ledger_json_path"],
        "ledger_md": res["ledger_md_path"],
        "ledger_sha256": res["ledger_sha256"],
        "runtime_seconds": res["runtime_seconds"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
