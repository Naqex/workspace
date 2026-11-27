"""Naqex Multi-Agent Dev-Only Strategy Pareto Sweep & Red-Team Audit Workflow.

Executed via the Antigravity `run_workflow` tool (top-level `await` with injected
primitives: `phase`, `agent`, `parallel`, `pipeline`, `call_tool`, `log`, `args`,
and `WORKSPACES`).

Hard Invariants (Fail-Closed, python -O safe — zero bare `assert`):
  - Dev-only strictly `<= 2024-12-31` (`holdout_cutoff_utc = 2025-01-01T00:00:00Z`)
  - `holdout_rows_analysed == 0` on every worker and aggregate result
  - `order_send_count == 0`, `spend_vnd == 0`, `MT5_PROCS == 0` on PC Dev
  - Enforces Law-15 balanced metrics (WR, RR, EV/trade, EV/fee, PF, Max DD,
    Calmar, Sharpe, monthly Pass/Fail/Wait summing to 100%, break-even friction)
  - Rejects TOP1-SOLO-QUANT-MASTER-PLAN.md section 3.4 Forbidden List candidates
"""

from __future__ import annotations

import base64
import datetime
import json
import math
import re

ORDER_SEND_COUNT = 0
SPEND_VND = 0
HOLDOUT_CUTOFF_DAY = "2024-12-31"
HOLDOUT_CUTOFF_DATE = datetime.date(2024, 12, 31)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_MODEL_TIERS = frozenset({"inherit", "flash_lite", "flash", "pro"})
FORBIDDEN_ID_RE = re.compile(r"(?:2025|2026|holdout|grid|martingale)", re.IGNORECASE)
EXIT_OK_RE = re.compile(r"(?m)^Command exited with code 0\b")

FINITE_METRIC_KEYS = (
    "winrate_pct",
    "reward_risk_ratio",
    "ev_per_trade_r",
    "ev_per_fee_x",
    "profit_factor",
    "max_dd_pct",
    "worst_flashcrash_dd_pct",
    "calmar",
    "sharpe",
    "dsr",
    "pbo",
    "corr_vs_port7e",
    "breakeven_slippage_x",
)


def _require_exact_zero(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value != 0:
        raise RuntimeError(f"Invariant violation: {field_name}={value!r} must be exact integer 0 (not bool).")
    return 0


def _require_non_neg_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"Invalid integer: {field_name}={value!r} must be non-negative int (not bool).")
    return value


def _require_finite_float(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"NonFiniteMetricError: {field_name}={value!r} must be finite number (not bool).")
    return float(value)


def _require_mode_a_workers(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 2:
        raise ValueError(f"Mode-A violation: max_workers={value!r} must be integer 1 or 2 (not bool).")
    return value


def _require_model_tier(value: object) -> str:
    if not isinstance(value, str) or value not in ALLOWED_MODEL_TIERS:
        raise ValueError(f"Invalid model_tier={value!r}; allowed: {sorted(ALLOWED_MODEL_TIERS)}.")
    return value


def _require_pre_holdout_iso_date(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not ISO_DATE_RE.fullmatch(value):
        raise ValueError(f"HoldoutLockError: {field_name}={value!r} must be strict YYYY-MM-DD ISO date.")
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"HoldoutLockError: {field_name}={value!r} is not a valid calendar date.") from exc
    if parsed > HOLDOUT_CUTOFF_DATE:
        raise ValueError(f"HoldoutLockError: {field_name}={value!r} exceeds sealed Dev cutoff {HOLDOUT_CUTOFF_DAY}.")
    return value


cfg = globals().get("args")
if cfg is None:
    cfg = {}
if not isinstance(cfg, dict):
    raise ValueError("Workflow Args must be a JSON object.")

dev_cutoff_utc = _require_pre_holdout_iso_date(cfg.get("dev_cutoff_utc", HOLDOUT_CUTOFF_DAY), "dev_cutoff_utc")
max_workers = _require_mode_a_workers(cfg.get("max_workers", 2))
target_max_shock_dd_pct = _require_finite_float(cfg.get("target_max_shock_dd_pct", 4.50), "target_max_shock_dd_pct")
max_pbo_gate = _require_finite_float(cfg.get("max_pbo_gate", 0.50), "max_pbo_gate")
min_breakeven_slippage_x = _require_finite_float(
    cfg.get("min_breakeven_slippage_x", 1.75),
    "min_breakeven_slippage_x",
)
model_tier = _require_model_tier(cfg.get("model_tier", "flash"))
py_exe = r".\.runtime\quant-audit-v24\Scripts\python.exe"

default_candidates = [
    {
        "candidate_id": "shield_a_cap200",
        "family": "PORT_7E_DEFENSE",
        "description": (
            "Shield A: Total simultaneous open-account risk cap = 2.00% on frozen_9e_tapes_v2 (<= 2024-12-31)."
        ),
        "data_source": ".runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.npz",
    },
    {
        "candidate_id": "shield_a_cap250",
        "family": "PORT_7E_DEFENSE",
        "description": (
            "Shield A: Total simultaneous open-account risk cap = 2.50% on frozen_9e_tapes_v2 (<= 2024-12-31)."
        ),
        "data_source": ".runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.npz",
    },
    {
        "candidate_id": "shield_a_cap300",
        "family": "PORT_7E_DEFENSE",
        "description": "Shield A: Total simultaneous open-account risk cap = 3.00% aligned with risk_profiles.json.",
        "data_source": ".runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.npz",
    },
    {
        "candidate_id": "shield_c_combined_6ccy",
        "family": "PORT_7E_DEFENSE",
        "description": (
            "Shield C: Total open-risk cap + directional cluster cap + M1 SpreadGuard + 6-CCY red-news shield."
        ),
        "data_source": ".runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.npz",
    },
]

candidates = cfg.get("candidates", default_candidates)
if not isinstance(candidates, list) or not candidates:
    raise ValueError("candidates must be a non-empty list of candidate dicts.")
for c in candidates:
    if not isinstance(c, dict):
        raise ValueError(f"Each candidate entry must be a dict, got {type(c).__name__}.")
    cid = str(c.get("candidate_id", ""))
    if not cid or FORBIDDEN_ID_RE.search(cid):
        raise ValueError(f"Forbidden or empty candidate_id rejected fail-closed: {cid!r}")

CANDIDATE_METRIC_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_id": {"type": "string"},
        "evidence_stage": {"type": "string", "enum": ["DEV_BACKTEST_2018_2024"]},
        "dev_max_day": {"type": "string"},
        "holdout_rows_analysed": {"type": "integer"},
        "order_send_count": {"type": "integer"},
        "winrate_pct": {"type": "number"},
        "reward_risk_ratio": {"type": "number"},
        "ev_per_trade_r": {"type": "number"},
        "ev_per_fee_x": {"type": "number"},
        "profit_factor": {"type": "number"},
        "max_dd_pct": {"type": "number"},
        "worst_flashcrash_dd_pct": {"type": "number"},
        "calmar": {"type": "number"},
        "sharpe": {"type": "number"},
        "pass_pct": {"type": "number"},
        "fail_pct": {"type": "number"},
        "wait_pct": {"type": "number"},
        "dsr": {"type": "number"},
        "pbo": {"type": "number"},
        "corr_vs_port7e": {"type": "number"},
        "breakeven_slippage_x": {"type": "number"},
        "forbidden_list_violations": {"type": "integer"},
        "notes": {"type": "string"},
    },
    "required": [
        "candidate_id",
        "evidence_stage",
        "dev_max_day",
        "holdout_rows_analysed",
        "order_send_count",
        "winrate_pct",
        "reward_risk_ratio",
        "ev_per_trade_r",
        "ev_per_fee_x",
        "profit_factor",
        "max_dd_pct",
        "worst_flashcrash_dd_pct",
        "calmar",
        "sharpe",
        "pass_pct",
        "fail_pct",
        "wait_pct",
        "dsr",
        "pbo",
        "corr_vs_port7e",
        "breakeven_slippage_x",
        "forbidden_list_violations",
        "notes",
    ],
}

REDTEAM_AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_id": {"type": "string"},
        "verdict": {"type": "string", "enum": ["SURVIVED_REDTEAM", "REJECTED_REDTEAM"]},
        "failed_angles": {"type": "array", "items": {"type": "string"}},
        "critical_risks": {"type": "array", "items": {"type": "string"}},
        "next_dev_check": {"type": "string"},
    },
    "required": ["candidate_id", "verdict", "failed_angles", "critical_risks", "next_dev_check"],
}

SYNTHESIS_SCHEMA = {
    "type": "object",
    "properties": {
        "recommended_candidate_id": {"type": "string"},
        "pareto_count": {"type": "integer"},
        "holdout_rows_analysed": {"type": "integer"},
        "order_send_count": {"type": "integer"},
        "summary_vi": {"type": "string"},
    },
    "required": [
        "recommended_candidate_id",
        "pareto_count",
        "holdout_rows_analysed",
        "order_send_count",
        "summary_vi",
    ],
}


def _py_cmd(code: str) -> str:
    """Wrap multi-line Python code safely for PowerShell via base64."""
    b64 = base64.b64encode(code.strip().encode("utf-8")).decode("ascii")
    return f"{py_exe} -X utf8 -c \"import base64; exec(base64.b64decode('{b64}').decode('utf-8'))\""


def _validate_candidate_result(row: dict) -> None:
    cid = str(row.get("candidate_id", ""))
    _require_exact_zero(row.get("holdout_rows_analysed"), f"{cid}.holdout_rows_analysed")
    _require_exact_zero(row.get("order_send_count"), f"{cid}.order_send_count")
    _require_non_neg_int(row.get("forbidden_list_violations"), f"{cid}.forbidden_list_violations")
    _require_pre_holdout_iso_date(row.get("dev_max_day"), f"{cid}.dev_max_day")

    probs: list[float] = []
    for pkey in ("pass_pct", "fail_pct", "wait_pct"):
        pval = _require_finite_float(row.get(pkey), f"{cid}.{pkey}")
        if pval < 0.0 or pval > 100.0:
            raise ValueError(f"Law15Error: {cid}.{pkey}={pval:.2f}% must be in [0.0, 100.0].")
        probs.append(pval)
    prob_sum = sum(probs)
    if abs(prob_sum - 100.0) > 0.25:
        raise ValueError(f"Law15Error: {cid} Pass+Fail+Wait={prob_sum:.2f}% must sum to 100.0%.")

    for key in FINITE_METRIC_KEYS:
        _require_finite_float(row.get(key), f"{cid}.{key}")


def _dominates(a: dict, b: dict) -> bool:
    """Return True if candidate `a` Pareto-dominates `b` across reward & defense objectives."""
    a_vec = (
        float(a["ev_per_fee_x"]),
        float(a["calmar"]),
        float(a["sharpe"]),
        -float(a["worst_flashcrash_dd_pct"]),
        -float(a["max_dd_pct"]),
    )
    b_vec = (
        float(b["ev_per_fee_x"]),
        float(b["calmar"]),
        float(b["sharpe"]),
        -float(b["worst_flashcrash_dd_pct"]),
        -float(b["max_dd_pct"]),
    )
    return all(x >= y for x, y in zip(a_vec, b_vec, strict=True)) and any(
        x > y for x, y in zip(a_vec, b_vec, strict=True)
    )


def _compute_pareto_frontier(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    eligible = [
        r
        for r in rows
        if not isinstance(r["forbidden_list_violations"], bool)
        and isinstance(r["forbidden_list_violations"], int)
        and r["forbidden_list_violations"] == 0
        and float(r["worst_flashcrash_dd_pct"]) <= target_max_shock_dd_pct
        and float(r["pbo"]) <= max_pbo_gate
        and float(r["breakeven_slippage_x"]) >= min_breakeven_slippage_x
    ]
    rejected = [r for r in rows if r not in eligible]
    frontier = [
        cand
        for cand in eligible
        if not any(_dominates(other, cand) for other in eligible if other["candidate_id"] != cand["candidate_id"])
    ]
    frontier.sort(key=lambda r: (float(r["ev_per_fee_x"]), float(r["calmar"])), reverse=True)
    return frontier, rejected


def _verify_synthesis(synthesis: dict, frontier: list[dict]) -> None:
    _require_exact_zero(synthesis.get("holdout_rows_analysed"), "synthesis.holdout_rows_analysed")
    _require_exact_zero(synthesis.get("order_send_count"), "synthesis.order_send_count")
    pcount = synthesis.get("pareto_count")
    if isinstance(pcount, bool) or not isinstance(pcount, int) or pcount != len(frontier):
        raise RuntimeError(f"Synthesis mismatch: pareto_count={pcount!r} != deterministic {len(frontier)}.")
    rec_id = synthesis.get("recommended_candidate_id")
    if frontier:
        allowed_ids = {str(c["candidate_id"]) for c in frontier}
        if rec_id not in allowed_ids:
            raise RuntimeError(f"Synthesis mismatch: recommended_candidate_id={rec_id!r} not in frontier.")
    elif rec_id != "NONE":
        raise RuntimeError(
            f"Synthesis mismatch: empty frontier must set recommended_candidate_id='NONE', got {rec_id!r}."
        )


PREFLIGHT_CODE = r"""
import datetime, hashlib, json, pathlib, re, sys

lock_p = pathlib.Path('planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json')
meta_p = pathlib.Path('.runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.json')
npz_p = pathlib.Path('.runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.npz')
lock_bytes = lock_p.read_bytes() if lock_p.is_file() else b''
lock_sha = hashlib.sha256(lock_bytes).hexdigest() if lock_bytes else ''
meta = json.loads(meta_p.read_text(encoding='utf-8')) if meta_p.is_file() else {}
ext_days = meta.get('ext_days') or []
max_day = str(max(ext_days)) if ext_days else str(meta.get('max_day', 'MISSING'))
date_ok = bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', max_day))
if date_ok:
    try:
        date_ok = datetime.date.fromisoformat(max_day) <= datetime.date(2024, 12, 31)
    except ValueError:
        date_ok = False
npz_sha = hashlib.sha256(npz_p.read_bytes()).hexdigest() if npz_p.is_file() else ''
npz_ok = bool(npz_sha) and npz_sha == str(meta.get('npz_sha256', ''))
lock_ok = bool(lock_sha) and lock_sha == str(meta.get('holdout_lock_sha256', ''))
dev_ok = lock_ok and npz_ok and date_ok
print(json.dumps({
    'holdout_lock_verified': lock_ok,
    'npz_sha_verified': npz_ok,
    'ext_days_count': len(ext_days),
    'frozen_tapes_max_day': max_day,
    'dev_ok': dev_ok,
}))
sys.exit(0 if dev_ok else 1)
"""

phase("Phase 1: Read-Only Preflight (Holdout Seal, Frozen Tapes & MT5_PROCS=0)")
preflight_out = await call_tool(
    "run_command",
    CommandLine=(
        f"{_py_cmd(PREFLIGHT_CODE)}; if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}; "
        "$mt5 = @(Get-Process terminal64, metatester64 -ErrorAction SilentlyContinue).Count; "
        'Write-Output "MT5_PROCS=$mt5"; if ($mt5 -ne 0) { exit 1 }'
    ),
    WaitMsBeforeAsync=10000,
    toolSummary="Verify Dev preflight and Holdout seal",
)
if not EXIT_OK_RE.search(preflight_out):
    raise RuntimeError(f"Preflight failed; aborting sweep fail-closed:\n{preflight_out[-1200:]}")
log("Preflight verified: Holdout 2025+ SEALED, frozen_9e_tapes_v2 <= 2024-12-31, MT5_PROCS=0.")

phase(f"Phase 2: Parallel Dev-Only Candidate Evaluation ({len(candidates)} candidates, <= {dev_cutoff_utc})")
eval_results = await parallel(
    candidates,
    lambda c: agent(
        prompt=(
            f"Evaluate Dev-only candidate `{c['candidate_id']}` ({c['family']}).\n"
            f"Specification: {c['description']}\n"
            f"Primary data source: {c['data_source']}\n\n"
            "HARD RULES (FAIL-CLOSED):\n"
            f"1. Strictly slice all data <= {dev_cutoff_utc} (`holdout_rows_analysed = 0`, ISO `YYYY-MM-DD`).\n"
            "2. NEVER unlock Holdout 2025+, NEVER run OrderSend (`order_send_count = 0`), NEVER modify repo files.\n"
            f"3. PC Dev Mode A: use `{py_exe}` ONLY, NEVER `uv run` in root, "
            f"NEVER `pytest -n auto` (max `-n {max_workers}`).\n"
            "4. Check TOP1-SOLO-QUANT-MASTER-PLAN.md section 3.4 Forbidden List (no <4H taker crypto, "
            "no negative-swap overnight CFD, no grid/martingale, no Brier<=0 ML filters).\n"
            "5. Return exact Law-15 balanced metrics where pass_pct, fail_pct, wait_pct in [0, 100] sum to 100.0."
        ),
        schema=CANDIDATE_METRIC_SCHEMA,
        role=f"Eval {c['candidate_id']}",
        workspace="inherit",
        model=model_tier,
    ),
)

for row in eval_results:
    _validate_candidate_result(row)
log(f"Validated {len(eval_results)}/{len(candidates)} candidate evaluations (holdout_rows_analysed=0).")

phase("Phase 3: Deterministic Pareto Frontier Filtering")
frontier, rejected = _compute_pareto_frontier(eval_results)
log(
    f"Pareto filter complete: {len(frontier)} non-dominated finalist(s), "
    f"{len(rejected)} rejected by hard gates (shock_dd <= {target_max_shock_dd_pct}%, "
    f"PBO <= {max_pbo_gate}, breakeven >= {min_breakeven_slippage_x}x)."
)

phase("Phase 4: Sequential 7-Angle Adversarial Red-Team Audit (Stateful Auditor)")
auditor = agent(
    prompt=(
        "You are an independent Naqex adversarial red-team auditor (falsification-first, "
        "following `.agents/skills/adversarial-self-audit/SKILL.md`).\n"
        "For each candidate presented, attack across all 7 angles:\n"
        "  1) Causal timing / lookahead leakage\n"
        "  2) Holdout 2025+ seal & python -O guard integrity\n"
        "  3) Unclamped Flash-Crash / gap DD (P1/P2/Funded)\n"
        "  4) Friction / slippage sensitivity & break-even multiple\n"
        "  5) Multiple-testing overfit (DSR, PBO/CSCV, CPCV)\n"
        "  6) MQL5 <-> Python parity & swap=0 compliance\n"
        "  7) TOP1-SOLO-QUANT-MASTER-PLAN.md section 3.4 Forbidden List\n"
        "Be brutally honest: mark REJECTED_REDTEAM if any material flaw exists."
    ),
    role="Adversarial Red-Team Auditor",
    workspace="inherit",
    model=model_tier,
)

audit_targets = frontier if frontier else eval_results[:2]
redteam_reports = await pipeline(
    audit_targets,
    lambda cand: auditor(
        prompt=(
            f"Audit candidate `{cand['candidate_id']}` strictly from these Dev-only metrics:\n"
            f"{json.dumps(cand, ensure_ascii=False, indent=2)}\n"
            "Do NOT touch Holdout 2025+ or edit any files. Return structured verdict."
        ),
        schema=REDTEAM_AUDIT_SCHEMA,
    ),
)
del auditor

phase("Phase 5: Law-15 Plain-Vietnamese Summary Synthesis (Deterministically Enforced)")
bundle = {
    "schema": "naqex-pareto-sweep-result-v1",
    "dev_cutoff_utc": dev_cutoff_utc,
    "holdout_rows_analysed": 0,
    "order_send_count": ORDER_SEND_COUNT,
    "spend_vnd": SPEND_VND,
    "hard_gates": {
        "target_max_shock_dd_pct": target_max_shock_dd_pct,
        "max_pbo_gate": max_pbo_gate,
        "min_breakeven_slippage_x": min_breakeven_slippage_x,
    },
    "evaluated": eval_results,
    "pareto_frontier": frontier,
    "rejected_by_gates": [r["candidate_id"] for r in rejected],
    "redteam_audits": redteam_reports,
}

synthesis = await agent(
    prompt=(
        "Produce a concise plain-Vietnamese Law-15 summary of this Dev-only Pareto sweep.\n"
        f"HARD RULES: pareto_count MUST equal {len(frontier)}, "
        "recommended_candidate_id MUST be from pareto_frontier (or 'NONE' if empty), "
        "explicit stage DEV_BACKTEST_2018_2024 (NOT Holdout/live), zero bare currency symbols (use USD/VND), "
        "zero raw IPs/secrets, report Pass/Fail/Wait=100%, gap to Top 1%, "
        "order_send_count=0, holdout_rows_analysed=0.\n"
        f"Data:\n{json.dumps(bundle, ensure_ascii=False, indent=2)}"
    ),
    schema=SYNTHESIS_SCHEMA,
    role="Law-15 Sweep Synthesizer",
    workspace="inherit",
    model=model_tier,
)

_verify_synthesis(synthesis, frontier)

log(f"Sweep finished: recommended={synthesis['recommended_candidate_id']} (frontier={synthesis['pareto_count']})")
print(json.dumps({"bundle": bundle, "synthesis": synthesis}, ensure_ascii=False, indent=2))
