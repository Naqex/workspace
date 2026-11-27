"""Total Offensive #3 — Stage 3 Blind Cluster B Validation, Dual-Ledger BH-FDR/PBO & 3-Tier Funnel.

Implements gates `G3-BLIND-CLB`, `G3-FDR-LEDGER`, `G3-ROBUST-NULL`, and `G3-TIER-CLASS`
strictly on sealed Dev data (`CLUSTER_A_YEARS = 2018..2020`, `CLUSTER_B_YEARS = 2021..2024`,
`holdout_rows_analysed == 0`, `ORDER_SEND_CAPABLE = False`).

Hard invariants (`[ARCH-02]`, `B4`, `M5`, `G01`, `G05`, `G08`, `H5`):
  - ZERO bare `assert` statements (all guards stay active under `python -O`).
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `holdout_rows_analysed = 0`.
  - ONE SINGLE BLIND PASS on `CLUSTER_B_YEARS = (2021, 2022, 2023, 2024)` per candidate
    across `1x`, `1.5x`, `2.0x` friction, `real_swap`, `zero_pos_swap`, and `fade`.
  - Records 100% of Cluster B trials (pass + fail) into `ExperimentLedger` (SQLite hash
    chain + DuckDB) under TWO distinct campaign `family_id`s:
      1. `offensive3_primary_m200` (<= 200 pre-registered primary trials, for Tier 1)
      2. `offensive3_exploratory_m1200` (<= 1200 full campaign pool, reported honestly with N_eff)
  - ALWAYS passes an explicit 2D `pbo_returns_matrix` into `research_council.critique_proposal()`
    so `G7_pbo_cscv` (`PBO <= 0.50`) ALWAYS executes and is NEVER silently skipped (`B4`).
  - Overrides `KillCriteria` to exact `G08` and strictly rejects `CONDITIONAL_RETEST`.
  - Enforces compact tracked funnel JSON strictly `< 300 KB` programmatically before write.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[2]
REPO_ROOT = AI_ENGINES.parents[1]
for _p in (AI_ENGINES, REPO_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_core.holdout_guard import enforce_pre_holdout_dates, enforce_pre_holdout_ts  # noqa: E402
from quant_core.metrics import compute_pbo_cscv, deflated_sharpe_ratio_empirical  # noqa: E402

from quant_factory.data_store import (  # noqa: E402
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_registry,
)
from quant_factory.eval_pipeline import benjamini_hochberg, sign_flip_p_numba  # noqa: E402
from quant_factory.experiment_ledger import (  # noqa: E402
    DEFAULT_DUCKDB_PATH,
    DEFAULT_REGISTRY_PATH,
    ExperimentLedger,
)
from quant_factory.offensive3.common_contract import (  # noqa: E402
    ALL_DEV_YEARS,
    CLUSTER_A_YEARS,
    CLUSTER_B_YEARS,
    RES_D1_YAHOO_SANCTIONED,
    RES_NATIVE_M1_BIDASK,
    TIER_12OLD,
    TIER_NEW7,
    TIER_NEW9,
    _build_weekday_calendar,
    enforce_dev_date_bound,
    load_family_candidates,
    load_universe_28,
    normalize_symbol,
    resolve_workspace_root,
)
from quant_factory.prop_engine import compute_cluster_a_invdd_weights, replay_portfolio_m1  # noqa: E402
from quant_factory.research_council import (  # noqa: E402
    EvidenceBundle,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)
from quant_factory.robustness_gate import (  # noqa: E402
    RobustnessThresholds,
    _random_entry_mc_ohlc_kernel,
    _random_entry_mc_ohlc_swing_kernel,
    evaluate_crisis_stress_windows,
    evaluate_robustness_gate,
    matched_hold_timing_permutation_p,
    random_entry_mc_on_bars,
    resample_m1_quotes_to_m5_mid,
)

# ---------------------------------------------------------------------------
# Hard Invariants & Campaign Constants
# ---------------------------------------------------------------------------

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
HOLDOUT_CUTOFF_DAY: str = "2025-01-01"
_NO_WINDOW_FLAGS: int = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0

CAMPAIGN_PRIMARY_FAMILY_ID: str = "offensive3_primary_m200"
CAMPAIGN_EXPLORATORY_FAMILY_ID: str = "offensive3_exploratory_m1200"

MAX_PRIMARY_CANDIDATES: int = 200
MAX_EXPLORATORY_CANDIDATES: int = 1200

SIGN_FLIP_DRAWS: int = 50_000
TIMING_PERM_DRAWS: int = 5_000
MC_DRAWS_DEFAULT: int = 1_000
PBO_N_SLICES_DEFAULT: int = 16
MAX_TRACKED_FUNNEL_BYTES: int = 300_000  # Strictly < 300 KB (both SI 300,000 B & binary 307,200 B)

TIER_1_FTMO_READY: str = "TIER_1_FTMO_READY"
TIER_2_PERSONAL_VAULT: str = "TIER_2_PERSONAL_VAULT"
TIER_3_DEAD_NO_EDGE: str = "TIER_3_DEAD_NO_EDGE"

TAG_M1_NATIVE_VERIFIED: str = "M1_NATIVE_VERIFIED"
TAG_PROVISIONAL_AWAITING_M1: str = "PROVISIONAL_AWAITING_OWNER_M1_EXPORT"

TIER_MIXED_12OLD_NEW9: str = "MIXED_12OLD_AND_NEW9"
TIER_MIXED_12OLD_NEW7: str = "MIXED_12OLD_AND_TRUE_BLIND_7"
TIER_MIXED_NEW9_NEW7: str = "MIXED_NEW9_AND_TRUE_BLIND_7"
TIER_MIXED_ALL_3: str = "MIXED_ALL_3_TIERS"

CANONICAL_BLINDNESS_TIERS: frozenset[str] = frozenset(
    {
        TIER_12OLD,
        TIER_NEW9,
        TIER_NEW7,
        TIER_MIXED_12OLD_NEW9,
        TIER_MIXED_12OLD_NEW7,
        TIER_MIXED_NEW9_NEW7,
        TIER_MIXED_ALL_3,
    }
)

DEFAULT_CANDIDATES_DIR: Path = REPO_ROOT / ".runtime" / "offensive3" / "candidates"
DEFAULT_FULL_RESULTS_PATH: Path = REPO_ROOT / ".runtime" / "offensive3" / "blind_clb_full_results.json"
DEFAULT_TRACKED_FUNNEL_PATH: Path = REPO_ROOT / "planning" / "research" / "OFFENSIVE3-ALPHA-FUNNEL-20261127.json"

# Canonical 12-family module map (also supports dynamic discovery via fam*.py scanning)
CANONICAL_FAMILY_MODULES: dict[str, str] = {
    "F01": "fam01_lowfreq_catalyst",
    "F02": "fam02_index_sweep_reversal",
    "F03": "fam03_fx_fix_orderflow",
    "F04": "fam04_energy_metals_micro",
    "F05": "fam05_index_intermarket",
    "F06": "fam06_swing_tsmom_28",
    "F07": "fam07_swing_xsec_basket",
    "F08": "fam08_swing_trend_pullback",
    "F09": "fam09_swing_calendar_drift",
    "F10": "fam10_true_blind_cross7",
    "F11": "fam11_statarb_pairs_prop",
    "F12": "fam12_cleanroom_intel_top",
}

_FAM_CODE_RE = re.compile(r"^(?:fam|F)(\d{2})(?:[^0-9]|$)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Pure-Math Analytical Statistics (Zero SciPy Imports — [ARCH-01])
# ---------------------------------------------------------------------------


def _betacf(a: float, b: float, x: float) -> float:
    """Modified Lentz continued fraction for incomplete beta I_x(a, b) (~1e-12 precision)."""
    max_iter = 200
    eps = 3.0e-12
    fpmin = 1.0e-30
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _regularized_incomplete_beta(x: float, a: float, b: float) -> float:
    """Regularized incomplete beta function I_x(a, b) in [0, 1]."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_bt = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    bt = math.exp(ln_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return max(0.0, min(1.0, bt * _betacf(a, b, x) / a))
    return max(0.0, min(1.0, 1.0 - bt * _betacf(b, a, 1.0 - x) / b))


def student_t_one_sided_p(t_stat: float, df: int) -> float:
    """Exact one-sided upper-tail Student-t p-value `P(T_df >= t_stat)` without SciPy."""
    if not math.isfinite(t_stat) or df < 1:
        return 1.0
    if t_stat == 0.0:
        return 0.5
    x = float(df) / (float(df) + t_stat * t_stat)
    ib = _regularized_incomplete_beta(x, 0.5 * float(df), 0.5)
    p_tail = 0.5 * ib
    if t_stat > 0.0:
        return max(1e-15, min(1.0, p_tail))
    return max(1e-15, min(1.0, 1.0 - p_tail))


def compute_student_t_and_newey_west_p(
    daily_returns: np.ndarray,
    *,
    max_lag: int | None = None,
) -> dict[str, Any]:
    """Analytical Student-t and Newey-West (1987) Bartlett-HAC one-sided p-values (`H0: mu <= 0`)."""
    r = np.asarray(daily_returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    n = int(r.size)
    if n < 5:
        return {
            "n_obs": n,
            "t_student": 0.0,
            "p_student_t": 1.0,
            "t_newey_west": 0.0,
            "p_newey_west": 1.0,
            "nw_lag": 0,
        }

    mu = float(np.mean(r))
    centered = r - mu
    sd = float(np.std(r, ddof=1))
    if sd <= 1e-15:
        t_st = 0.0
        p_st = 1.0 if mu <= 0.0 else 1e-15
    else:
        t_st = mu / (sd / math.sqrt(float(n)))
        p_st = student_t_one_sided_p(t_st, n - 1)

    lag = int(max_lag) if max_lag is not None else max(1, int(math.floor(4.0 * ((n / 100.0) ** (2.0 / 9.0)))))
    lag = min(lag, n - 2)
    gamma0 = float(np.dot(centered, centered)) / float(n)
    lrv = gamma0
    for ell in range(1, lag + 1):
        weight = 1.0 - float(ell) / float(lag + 1)
        gamma_l = float(np.dot(centered[ell:], centered[:-ell])) / float(n)
        lrv += 2.0 * weight * gamma_l

    # Small-sample degrees-of-freedom correction & non-negative variance floor
    lrv_adj = max(lrv * (float(n) / float(max(1, n - 1))), 0.0)
    if lrv_adj <= 1e-24:
        t_nw = t_st
        p_nw = p_st
    else:
        se_nw = math.sqrt(lrv_adj / float(n))
        t_nw = mu / se_nw
        p_nw = student_t_one_sided_p(t_nw, n - 1)

    return {
        "n_obs": n,
        "t_student": round(float(t_st), 4),
        "p_student_t": round(float(p_st), 8),
        "t_newey_west": round(float(t_nw), 4),
        "p_newey_west": round(float(p_nw), 8),
        "nw_lag": int(lag),
    }


def compute_effective_independent_trials(returns_matrix: np.ndarray) -> dict[str, Any]:
    """Compute effective independent trials `N_eff = (sum(lam))^2 / sum(lam^2)` on daily Cl.B corr matrix."""
    mat = np.asarray(returns_matrix, dtype=np.float64)
    if mat.ndim != 2:
        raise ValueError(f"returns_matrix must be 2D (T, M), got shape {mat.shape}")
    n_obs, n_total = mat.shape
    if n_total == 0 or n_obs < 2:
        return {
            "n_eff": 0.0,
            "n_candidates_total": int(n_total),
            "n_candidates_active": 0,
            "top1_variance_share": 0.0,
            "top3_variance_share": 0.0,
        }

    stds = np.std(mat, axis=0, ddof=1)
    active_mask = np.isfinite(stds) & (stds > 1e-12)
    n_active = int(np.sum(active_mask))
    if n_active == 0:
        return {
            "n_eff": 0.0,
            "n_candidates_total": int(n_total),
            "n_candidates_active": 0,
            "top1_variance_share": 0.0,
            "top3_variance_share": 0.0,
        }
    if n_active == 1:
        return {
            "n_eff": 1.0,
            "n_candidates_total": int(n_total),
            "n_candidates_active": 1,
            "top1_variance_share": 1.0,
            "top3_variance_share": 1.0,
        }

    sub = mat[:, active_mask]
    corr = np.corrcoef(sub, rowvar=False)
    corr = np.where(np.isfinite(corr), corr, 0.0)
    corr = 0.5 * (corr + corr.T)
    np.fill_diagonal(corr, 1.0)

    eigvals = np.linalg.eigvalsh(corr)
    lam = np.maximum(eigvals, 0.0)
    sum_lam = float(np.sum(lam))
    sum_lam_sq = float(np.sum(lam * lam))
    if sum_lam_sq <= 1e-18 or sum_lam <= 1e-18:
        n_eff = 1.0
        top1 = 1.0
        top3 = 1.0
    else:
        n_eff = (sum_lam * sum_lam) / sum_lam_sq
        n_eff = max(1.0, min(float(n_active), n_eff))
        lam_desc = np.sort(lam)[::-1]
        top1 = float(lam_desc[0]) / sum_lam
        top3 = float(np.sum(lam_desc[: min(3, len(lam_desc))])) / sum_lam

    return {
        "n_eff": round(float(n_eff), 4),
        "n_candidates_total": int(n_total),
        "n_candidates_active": int(n_active),
        "top1_variance_share": round(float(top1), 4),
        "top3_variance_share": round(float(top3), 4),
    }


def compute_sign_flip_p_50k(
    daily_1x: np.ndarray,
    fade_daily_1x: np.ndarray | None = None,
    *,
    draws: int = SIGN_FLIP_DRAWS,
    seed: int = 20261127,
) -> dict[str, Any]:
    """Run `sign_flip_p_numba` with `draws=50_000` on active Cluster B days (exact zero-invariant speedup)."""
    if isinstance(draws, bool) or int(draws) < 1:
        raise ValueError(f"draws must be >= 1, got {draws!r}")
    v = np.asarray(daily_1x, dtype=np.float64)
    if v.ndim != 1 or not bool(np.all(np.isfinite(v))):
        raise ValueError("daily_1x must be a finite 1D array")

    has_fade = fade_daily_1x is not None
    if has_fade:
        f = np.asarray(fade_daily_1x, dtype=np.float64)
        if f.shape != v.shape or not bool(np.all(np.isfinite(f))):
            raise ValueError(f"fade_daily_1x shape/finiteness mismatch: {f.shape} vs {v.shape}")
        active = (np.abs(v) > 1e-12) | (np.abs(f) > 1e-12)
        va = np.ascontiguousarray(v[active], dtype=np.float64)
        fa = np.ascontiguousarray(f[active], dtype=np.float64)
    else:
        active = np.abs(v) > 1e-12
        va = np.ascontiguousarray(v[active], dtype=np.float64)
        fa = np.empty(0, dtype=np.float64)

    n_act = int(va.size)
    if n_act == 0:
        return {
            "p_value": 1.0,
            "p_sign_flip_zero": 1.0,
            "p_sign_flip_fade": 1.0 if has_fade else None,
            "draws": int(draws),
            "n_active_days": 0,
        }

    obs_sum = float(np.sum(va))
    p_zero = float(sign_flip_p_numba(va, -va, draws=int(draws), seed=int(seed)))
    p_fade = (
        float(sign_flip_p_numba(va, fa, draws=int(draws), seed=int(seed + 13)))
        if has_fade
        else None
    )

    if obs_sum <= 0.0:
        p_comb = 1.0
    elif p_fade is not None:
        p_comb = max(p_zero, p_fade)
    else:
        p_comb = p_zero

    p_comb = max(1.0 / float(int(draws) + 1), min(1.0, float(p_comb)))
    return {
        "p_value": round(p_comb, 8),
        "p_sign_flip_zero": round(p_zero, 8),
        "p_sign_flip_fade": round(p_fade, 8) if p_fade is not None else None,
        "draws": int(draws),
        "n_active_days": n_act,
    }


# ---------------------------------------------------------------------------
# Helpers: Calendar Alignment, Incumbent PORT_7E, Git/Data Provenance, Atomic IO
# ---------------------------------------------------------------------------


def _atomic_write_bytes(path: Path, raw_bytes: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(raw_bytes)
            fh.flush()
            os.fsync(fh.fileno())
            tmp = Path(fh.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _atomic_write_json(path: Path, payload: Mapping[str, Any], *, compact: bool = False) -> int:
    if compact:
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    else:
        text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    raw = text.encode("utf-8")
    _atomic_write_bytes(path, raw)
    return len(raw)


def _resolve_git_sha(root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            creationflags=_NO_WINDOW_FLAGS,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return "offline-uncommitted"


def _normalize_daily_pnl_map(
    raw_daily: Any,
    calendar_dates: Sequence[str],
    *,
    context: str,
) -> tuple[dict[str, float], np.ndarray]:
    """Normalize family `daily_pnl_*` (`{day: R}` or `{'dates': ..., 'pnl': ...}`) onto `calendar_dates`."""
    enforce_pre_holdout_dates(calendar_dates, context=f"{context}.calendar")
    out_map: dict[str, float] = {str(d): 0.0 for d in calendar_dates}
    if raw_daily is None:
        return out_map, np.zeros(len(calendar_dates), dtype=np.float64)

    if isinstance(raw_daily, Mapping):
        if "dates" in raw_daily and "pnl" in raw_daily and isinstance(raw_daily["dates"], (list, tuple)):
            d_list = [str(d) for d in raw_daily["dates"]]
            p_arr = np.asarray(raw_daily["pnl"], dtype=np.float64)
            if len(d_list) != len(p_arr):
                raise ValueError(f"{context}: dates ({len(d_list)}) != pnl ({len(p_arr)})")
            enforce_pre_holdout_dates(d_list, context=f"{context}.dates")
            for dk, val in zip(d_list, p_arr, strict=True):
                if dk in out_map and math.isfinite(float(val)):
                    out_map[dk] = float(val)
        else:
            keys = [str(k) for k in raw_daily]
            enforce_pre_holdout_dates(keys, context=f"{context}.keys")
            for k, val in raw_daily.items():
                dk = str(k)
                if dk in out_map and val is not None and not isinstance(val, bool):
                    fv = float(val)
                    if math.isfinite(fv):
                        out_map[dk] = fv
    elif isinstance(raw_daily, (np.ndarray, list, tuple)):
        arr = np.asarray(raw_daily, dtype=np.float64)
        if arr.ndim != 1 or arr.size != len(calendar_dates):
            raise ValueError(
                f"{context}: array daily_pnl length ({arr.size}) != calendar length ({len(calendar_dates)})"
            )
        for dk, fv in zip(calendar_dates, arr, strict=True):
            if math.isfinite(float(fv)):
                out_map[str(dk)] = float(fv)
    else:
        raise ValueError(f"{context}: unsupported daily_pnl type {type(raw_daily).__name__}")

    aligned = np.array([out_map[str(d)] for d in calendar_dates], dtype=np.float64)
    return out_map, aligned


def load_port7e_incumbent_clb_daily(
    *,
    cluster_b_years: tuple[int, ...] = CLUSTER_B_YEARS,
) -> dict[str, float]:
    """Compute exact `PORT_7E` incumbent daily returns on `2021-2024` from `frozen_9e_tapes_v2` (< 2025-01-01)."""
    assert_holdout_locked()
    warm = build_or_load_frozen_tapes(force_rebuild=False)
    tapes = warm["tapes"]
    ext_days = sorted(str(d) for d in warm["ext_days"])
    strict_a = sorted(str(d) for d in warm["strict_cluster_a_days"])
    enforce_pre_holdout_dates(ext_days, context="stage3.port7e_ext_days")
    enforce_pre_holdout_dates(strict_a, context="stage3.port7e_strict_a")

    clb_year_set = {str(y) for y in cluster_b_years}
    clb_days = [d for d in ext_days if d[:4] in clb_year_set]
    if not clb_days:
        raise ValueError(f"No PORT_7E incumbent days found for cluster_b_years={cluster_b_years}")
    enforce_pre_holdout_dates(clb_days, context="stage3.port7e_clb_days")

    reg = load_registry()
    base_risks = {str(e["id"]): float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    core7 = list(reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"])
    invdd7 = compute_cluster_a_invdd_weights(strict_a, tapes, core7, sum(base_risks[k] for k in core7))
    _, exits = replay_portfolio_m1(
        clb_days,
        tapes,
        invdd7,
        10_000.0,
        profile_mode="Swing",
        max_symbol_concurrent_risk=0.010,
        red_news_cal=None,
    )

    cal_clb = _build_weekday_calendar(tuple(sorted(cluster_b_years)))
    enforce_pre_holdout_dates(cal_clb, context="stage3.port7e_cal_clb")
    out: dict[str, float] = {d: 0.0 for d in cal_clb}
    for row in exits:
        dk = str(row["day"])
        enforce_dev_date_bound(dk, context="stage3.port7e_exit_day")
        if dk in out:
            out[dk] = float(row["net_usd"]) / 10_000.0
    return out


# ---------------------------------------------------------------------------
# Dynamic 12-Family Module Discovery & Checkpoint Loader
# ---------------------------------------------------------------------------


def _extract_family_code(identifier: str) -> str | None:
    m = _FAM_CODE_RE.match(str(identifier).strip())
    if not m:
        return None
    return f"F{m.group(1)}"


def discover_family_modules(
    modules_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Dynamically load all available `fam01..fam12` modules exposing `evaluate_candidate`."""
    base_dir = Path(modules_dir) if modules_dir is not None else Path(__file__).resolve().parent
    if not base_dir.is_dir():
        raise FileNotFoundError(f"Family modules directory missing: {base_dir}")

    is_default_pkg = base_dir.resolve() == Path(__file__).resolve().parent.resolve()
    registry: dict[str, Any] = {}

    for py_path in sorted(base_dir.glob("fam*.py")):
        stem = py_path.stem
        if is_default_pkg:
            mod = importlib.import_module(f"quant_factory.offensive3.{stem}")
        else:
            unique_mod_name = f"_off3_dyn_{stem}_{hashlib.sha256(str(py_path.resolve()).encode()).hexdigest()[:8]}"
            spec = importlib.util.spec_from_file_location(unique_mod_name, py_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Unable to build module spec for {py_path}")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

        if not callable(getattr(mod, "evaluate_candidate", None)):
            raise ValueError(f"Family module {py_path.name} missing callable evaluate_candidate(spec, universe, years)")

        # Register under module stem, F01..F12 prefix, and explicit FAMILY_ID / FAMILY_IDS if declared
        registry[stem] = mod
        fcode = _extract_family_code(stem)
        if fcode:
            registry[fcode] = mod
        fam_id = getattr(mod, "FAMILY_ID", None)
        if isinstance(fam_id, str) and fam_id.strip():
            registry[fam_id.strip()] = mod
            registry[fam_id.strip().upper()] = mod
        fam_ids = getattr(mod, "FAMILY_IDS", None)
        if isinstance(fam_ids, (list, tuple, set)):
            for fid in fam_ids:
                if isinstance(fid, str) and fid.strip():
                    registry[fid.strip()] = mod
                    registry[fid.strip().upper()] = mod

    return registry


def resolve_module_for_family(family_id: str, module_registry: Mapping[str, Any]) -> Any:
    """Resolve the family module corresponding to `family_id` (exact match, upper, or F01..F12 prefix)."""
    fid = str(family_id).strip()
    if fid in module_registry:
        return module_registry[fid]
    if fid.upper() in module_registry:
        return module_registry[fid.upper()]
    fcode = _extract_family_code(fid)
    if fcode and fcode in module_registry:
        return module_registry[fcode]
    if fcode and fcode in CANONICAL_FAMILY_MODULES:
        stem = CANONICAL_FAMILY_MODULES[fcode]
        if stem in module_registry:
            return module_registry[stem]
    raise KeyError(f"No family module found for checkpoint family_id={family_id!r} (code={fcode!r})")


def _unwrap_candidate_spec(cand: Mapping[str, Any]) -> dict[str, Any]:
    """Merge nested `cand['spec']` (when a family stores spec nested) with outer checkpoint metadata."""
    outer = dict(cand)
    inner = outer.get("spec")
    if isinstance(inner, Mapping):
        merged = {k: v for k, v in outer.items() if k != "spec"}
        merged.update(inner)
        return merged
    return outer


def load_all_family_checkpoints(
    candidates_dir: str | Path | None = None,
    *,
    family_ids: Sequence[str] | None = None,
    verify_sha: bool = True,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Load and enforce campaign-wide caps across Cluster A family checkpoints (`2018-2020` ONLY)."""
    ws = resolve_workspace_root(root)
    cdir = Path(candidates_dir) if candidates_dir is not None else (ws / ".runtime/offensive3/candidates")
    if not cdir.is_dir():
        raise FileNotFoundError(f"Candidates checkpoint directory missing: {cdir}")

    if family_ids is not None:
        target_fids = [str(f).strip() for f in family_ids]
    else:
        target_fids = sorted(p.stem for p in cdir.glob("*.json") if not p.name.startswith("."))

    if not target_fids:
        raise ValueError(f"No family candidate checkpoints found in {cdir}")

    checkpoints: dict[str, dict[str, Any]] = {}
    primary_records: list[dict[str, Any]] = []
    exploratory_records: list[dict[str, Any]] = []
    seen_strategy_ids: set[str] = set()
    sha_parts: list[str] = []

    for fid in target_fids:
        doc = load_family_candidates(fid, candidates_dir=cdir, verify_sha=verify_sha, root=ws)
        if doc.get("discovery_years") != list(CLUSTER_A_YEARS):
            raise ValueError(
                f"CLUSTER_B_LEAK_BLOCKED [{fid}]: discovery_years={doc.get('discovery_years')!r} != [2018, 2019, 2020]"
            )
        if doc.get("order_send_count") != 0 or doc.get("holdout_rows_analysed") != 0:
            raise ValueError(f"SAFETY_VIOLATION [{fid}]: non-zero order_send or holdout_rows_analysed")

        checkpoints[fid] = doc
        sha_parts.append(f"{fid}:{doc.get('payload_sha256', '')}")

        for cand in doc.get("primary_candidates") or []:
            cdict = _unwrap_candidate_spec(cand)
            cid = str(cdict["candidate_id"]).strip()
            sid = cid if cid.startswith(f"{fid}::") else f"{fid}::{cid}"
            if sid in seen_strategy_ids:
                raise ValueError(f"DUPLICATE_STRATEGY_ID: {sid!r}")
            seen_strategy_ids.add(sid)
            rec = {
                "strategy_id": sid,
                "alpha_family_id": fid,
                "candidate_id": cid,
                "pool_tier": "PRIMARY",
                "is_primary": True,
                "spec": cdict,
            }
            primary_records.append(rec)
            exploratory_records.append(rec)

        for cand in doc.get("exploratory_candidates") or []:
            cdict = _unwrap_candidate_spec(cand)
            cid = str(cdict["candidate_id"]).strip()
            sid = cid if cid.startswith(f"{fid}::") else f"{fid}::{cid}"
            if sid in seen_strategy_ids:
                raise ValueError(f"DUPLICATE_STRATEGY_ID: {sid!r}")
            seen_strategy_ids.add(sid)
            rec = {
                "strategy_id": sid,
                "alpha_family_id": fid,
                "candidate_id": cid,
                "pool_tier": "EXPLORATORY",
                "is_primary": False,
                "spec": cdict,
            }
            exploratory_records.append(rec)

    if len(primary_records) > MAX_PRIMARY_CANDIDATES:
        raise ValueError(
            f"CAMPAIGN_PRIMARY_CAP_EXCEEDED: len(primary)={len(primary_records)} > {MAX_PRIMARY_CANDIDATES}"
        )
    if len(exploratory_records) > MAX_EXPLORATORY_CANDIDATES:
        raise ValueError(
            f"CAMPAIGN_EXPLORATORY_CAP_EXCEEDED: len(exploratory)={len(exploratory_records)} > "
            f"{MAX_EXPLORATORY_CANDIDATES}"
        )

    campaign_data_sha = hashlib.sha256("|".join(sorted(sha_parts)).encode("utf-8")).hexdigest()
    return {
        "candidates_dir": str(cdir),
        "family_ids": target_fids,
        "checkpoints": checkpoints,
        "primary_records": primary_records,
        "all_records": exploratory_records,
        "primary_count": len(primary_records),
        "exploratory_total_count": len(exploratory_records),
        "campaign_data_sha": campaign_data_sha,
    }


# ---------------------------------------------------------------------------
# G08 KillCriteria, Swing Detection & Robustness Helpers
# ---------------------------------------------------------------------------


def build_g08_kill_criteria(*, is_intraday: bool) -> KillCriteria:
    """Return exact `G08` `KillCriteria` (override defaults to strict `|r|<=0.15`, `tail<=0.35`, `PBO<=0.50`)."""
    return KillCriteria(
        max_bh_q=0.10,
        min_dsr=0.50,
        min_cluster_b_sharpe=0.40,
        min_cost_breakeven_mult=2.0,
        max_corr_vs_incumbent=0.15,
        max_tail_corr_vs_incumbent=0.35,
        min_trades_cluster_b=50 if is_intraday else 30,
        max_pbo=0.50,
        require_incumbent=True,
        require_robustness_gate=True,
    )


def _infer_is_swing_candidate(
    spec: Mapping[str, Any],
    eval_res: Mapping[str, Any],
    trades: Sequence[Mapping[str, Any]],
) -> bool:
    """Determine whether a candidate is multi-day Swing (`True`) vs Intraday swap=0 (`False`)."""
    track = str(spec.get("prop_track") or spec.get("track") or eval_res.get("prop_track") or "").upper()
    if "SWING" in track and "INTRADAY" not in track:
        return True
    if "INTRADAY" in track and "SWING" not in track:
        return False
    tf = str(spec.get("timeframe") or "").upper()
    if tf in ("D1", "H4", "W1", "DAILY"):
        return True
    for tr in trades:
        ed = str(tr.get("entry_date") or "")
        xd = str(tr.get("exit_date") or "")
        if ed and xd and xd > ed:
            return True
        if "swap_zero_pos_R" in tr or "hold_bars" in tr:
            return True
    return False


def normalize_blindness_tier(tiers_or_labels: str | Sequence[str] | set[str] | frozenset[str]) -> str:
    """Map any atomic tier set or legacy/composite label strictly into the 7 canonical enum values.

    NEVER concatenates pre-formatted `MIXED_*` labels together (`P1-03` fail-closed fix).
    """
    raw_items: list[str]
    if isinstance(tiers_or_labels, str):
        raw_items = [tiers_or_labels]
    else:
        raw_items = [str(x) for x in tiers_or_labels if isinstance(x, str)]

    atomic: set[str] = set()
    for raw in raw_items:
        up = raw.strip().upper()
        if not up or up == "UNKNOWN":
            continue
        if up == TIER_MIXED_ALL_3 or "ALL_3_TIERS" in up:
            atomic.update((TIER_12OLD, TIER_NEW9, TIER_NEW7))
            continue
        if TIER_12OLD in up or "12OLD" in up:
            atomic.add(TIER_12OLD)
        if TIER_NEW9 in up or "NEW9" in up:
            atomic.add(TIER_NEW9)
        if TIER_NEW7 in up or "TRUE_BLIND_7" in up or "NEW7" in up:
            atomic.add(TIER_NEW7)

    if not atomic:
        return "UNKNOWN"
    if len(atomic) == 1:
        return next(iter(atomic))
    if atomic == {TIER_12OLD, TIER_NEW9}:
        return TIER_MIXED_12OLD_NEW9
    if atomic == {TIER_12OLD, TIER_NEW7}:
        return TIER_MIXED_12OLD_NEW7
    if atomic == {TIER_NEW9, TIER_NEW7}:
        return TIER_MIXED_NEW9_NEW7
    return TIER_MIXED_ALL_3


def _collect_symbol_tokens(raw_val: Any, out: list[str], seen: set[str]) -> None:
    if isinstance(raw_val, str) and raw_val.strip():
        for part in raw_val.replace("/", ",").split(","):
            tok = part.strip()
            if not tok:
                continue
            su = normalize_symbol(tok)
            if su not in seen:
                seen.add(su)
                out.append(su)
    elif isinstance(raw_val, (list, tuple, set)):
        for item in raw_val:
            _collect_symbol_tokens(item, out, seen)


def _extract_candidate_symbols(
    spec: Mapping[str, Any],
    trades: Sequence[Mapping[str, Any]],
    *,
    include_leaders: bool = True,
) -> list[str]:
    """Extract ALL participating symbols across `trades` and `spec` (optionally including leaders/graphs).

    When `include_leaders=True` (default), returns the full union of traded targets, pair legs,
    leader symbols (`leader_symbol`/`leader_symbols`, top-level or inside `params`), and network
    peer `graph_symbols` so `blindness_tier` and `data_resolution` NEVER under-report consumed inputs!
    """
    syms: list[str] = []
    seen: set[str] = set()

    for tr in trades:
        for k in ("leg_a", "leg_b", "symbol", "asset"):
            v = tr.get(k)
            if v:
                _collect_symbol_tokens(v, syms, seen)

    def _scan_spec(obj: Mapping[str, Any]) -> None:
        base_keys = ("symbols", "asset_universe", "symbol", "asset", "pairs")
        leader_keys = ("leader_symbols", "leader_symbol", "graph_symbols")
        for k in base_keys:
            if k in obj and obj[k]:
                _collect_symbol_tokens(obj[k], syms, seen)
        if include_leaders:
            for k in leader_keys:
                if k in obj and obj[k]:
                    _collect_symbol_tokens(obj[k], syms, seen)
        prm = obj.get("params")
        if isinstance(prm, Mapping):
            for k in ("symbols", "pairs"):
                if k in prm and prm[k]:
                    _collect_symbol_tokens(prm[k], syms, seen)
            if include_leaders:
                for k in ("leader_symbol", "leader_symbols", "graph_symbols"):
                    if k in prm and prm[k]:
                        _collect_symbol_tokens(prm[k], syms, seen)
        inner = obj.get("spec")
        if isinstance(inner, Mapping):
            _scan_spec(inner)

    _scan_spec(spec)
    return syms or ["UNKNOWN"]


def _resolve_resolution_and_blindness(
    spec: Mapping[str, Any],
    eval_res: Mapping[str, Any],
    trades: Sequence[Mapping[str, Any]],
    universe: Mapping[str, Any] | None,
) -> tuple[str, str]:
    """Determine canonical `(data_resolution, blindness_tier)` over ALL participating symbols.

    Fail-conservative resolution: ANY D1 Yahoo or MIXED symbol forces `D1_YAHOO_SANCTIONED`.
    Leader-inclusive canonical blindness tier (`P1-02`/`P1-03`): computes atomic per-symbol tiers
    over target + leader + pair + graph union from `universe['assets']` first (falling back to
    decomposed string labels only when no asset entry matches), returning strictly one of the
    7 `CANONICAL_BLINDNESS_TIERS` (or `'UNKNOWN'`).
    """
    res_set: set[str] = set()
    universe_atomic_tiers: set[str] = set()
    fallback_tier_labels: list[str] = []

    for src in (eval_res, spec):
        rv = src.get("data_resolution")
        if isinstance(rv, str) and rv.strip():
            res_set.add(rv.strip())
        tv = src.get("blindness_tier")
        if isinstance(tv, str) and tv.strip():
            fallback_tier_labels.append(tv.strip())

    for tr in trades:
        rv = tr.get("data_resolution")
        if isinstance(rv, str) and rv.strip():
            res_set.add(rv.strip())
        tv = tr.get("blindness_tier")
        if isinstance(tv, str) and tv.strip():
            fallback_tier_labels.append(tv.strip())

    participating_syms = _extract_candidate_symbols(spec, trades, include_leaders=True)
    if universe is not None and isinstance(universe.get("assets"), Mapping):
        assets = universe["assets"]
        for sym in participating_syms:
            aobj = assets.get(sym)
            if isinstance(aobj, Mapping):
                if aobj.get("data_resolution"):
                    res_set.add(str(aobj["data_resolution"]))
                if aobj.get("blindness_tier"):
                    universe_atomic_tiers.add(str(aobj["blindness_tier"]))

    # Fail-conservative resolution: ANY D1 Yahoo or MIXED symbol forces D1_YAHOO_SANCTIONED provisional tag!
    if RES_D1_YAHOO_SANCTIONED in res_set or any("D1" in r.upper() or "MIXED" in r.upper() for r in res_set):
        data_res = RES_D1_YAHOO_SANCTIONED
    elif RES_NATIVE_M1_BIDASK in res_set:
        data_res = RES_NATIVE_M1_BIDASK
    else:
        data_res = RES_D1_YAHOO_SANCTIONED

    if universe_atomic_tiers:
        b_tier = normalize_blindness_tier(universe_atomic_tiers)
    else:
        b_tier = normalize_blindness_tier(fallback_tier_labels)
    return data_res, b_tier


def _split_pair_symbol(raw_sym: str) -> tuple[str, str] | None:
    """Split a slash-joined pair identifier `'SYM_A/SYM_B'` into normalized `(sym_a, sym_b)`."""
    s = str(raw_sym or "").strip()
    if "/" not in s:
        return None
    parts = [p.strip() for p in s.split("/") if p.strip()]
    if len(parts) != 2:
        return None
    return normalize_symbol(parts[0]), normalize_symbol(parts[1])


def _extract_trade_symbol_key(tr: Mapping[str, Any]) -> str:
    """Extract canonical single symbol `'SYM'` or pair key `'SYM_A/SYM_B'` from a trade record."""
    leg_a = str(tr.get("leg_a") or "").strip()
    leg_b = str(tr.get("leg_b") or "").strip()
    if leg_a and leg_b:
        return f"{normalize_symbol(leg_a)}/{normalize_symbol(leg_b)}"
    raw = str(tr.get("symbol") or tr.get("asset") or "").strip()
    if not raw:
        return ""
    pair = _split_pair_symbol(raw)
    if pair is not None:
        return f"{pair[0]}/{pair[1]}"
    return normalize_symbol(raw)


def _extract_trade_side(tr: Mapping[str, Any]) -> int:
    """Extract trade direction (`+1` or `-1`), supporting pair trades emitting `spread_dir`."""
    raw = tr.get("side")
    if raw is None:
        raw = tr.get("spread_dir", 1)
    return 1 if int(raw) >= 0 else -1


def _build_underlying_market_daily_returns(
    symbols: Sequence[str],
    universe: Mapping[str, Any] | None,
    calendar_dates: Sequence[str],
) -> dict[str, float]:
    """Build equal-weighted underlying asset (or pair spread `'SYM_A/SYM_B'`) daily return map."""
    out: dict[str, float] = {str(d): 0.0 for d in calendar_dates}
    if universe is None or not isinstance(universe.get("assets"), Mapping):
        return out
    assets = universe["assets"]
    counts: dict[str, int] = {str(d): 0 for d in calendar_dates}
    d1_ret_cache: dict[str, dict[str, float]] = {}

    def _get_d1_ret_map(sym: str) -> dict[str, float]:
        if sym in d1_ret_cache:
            return d1_ret_cache[sym]
        ret_map: dict[str, float] = {}
        aobj = assets.get(sym)
        if isinstance(aobj, Mapping) and isinstance(aobj.get("d1"), Mapping):
            d1 = aobj["d1"]
            raw_dates = d1.get("dates")
            raw_closes = d1.get("close")
            if raw_dates is not None and raw_closes is not None:
                dates_s = [str(d) for d in raw_dates]
                closes_s = np.asarray(raw_closes, dtype=np.float64)
                if len(dates_s) >= 2 and len(dates_s) == len(closes_s):
                    enforce_pre_holdout_dates(dates_s, context=f"stage3.mkt_ret:{sym}")
                    for i in range(1, len(dates_s)):
                        dk = dates_s[i]
                        if dk in out and closes_s[i - 1] > 0.0 and closes_s[i] > 0.0:
                            rv = (float(closes_s[i]) / float(closes_s[i - 1])) - 1.0
                            if math.isfinite(rv):
                                ret_map[dk] = rv
        d1_ret_cache[sym] = ret_map
        return ret_map

    for raw_sym in symbols:
        pair = _split_pair_symbol(str(raw_sym))
        if pair is not None:
            sym_a, sym_b = pair
            ra = _get_d1_ret_map(sym_a)
            rb = _get_d1_ret_map(sym_b)
            if ra and rb:
                for dk in out:
                    if dk in ra and dk in rb:
                        out[dk] += ra[dk] - rb[dk]
                        counts[dk] += 1
            elif ra:
                for dk, rv in ra.items():
                    out[dk] += rv
                    counts[dk] += 1
            elif rb:
                for dk, rv in rb.items():
                    out[dk] += rv
                    counts[dk] += 1
            continue

        sym = normalize_symbol(str(raw_sym))
        rs = _get_d1_ret_map(sym)
        for dk, rv in rs.items():
            out[dk] += rv
            counts[dk] += 1

    for dk in out:
        if counts[dk] > 0:
            out[dk] /= float(counts[dk])
    return out


def _run_candidate_random_entry_mc(
    *,
    trades: Sequence[Mapping[str, Any]],
    is_swing: bool,
    universe: Mapping[str, Any] | None,
    m5_cache: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
    clb_year_set: set[int],
    draws: int,
    seed: int,
) -> tuple[dict[str, Any] | None, float]:
    """Run Swing-safe or Intraday real-market Random-Entry MC across 1, N, or pair (`'SYM_A/SYM_B'`) symbols."""
    if not trades:
        return None, 0.0

    r_list: list[float] = []
    s_list: list[int] = []
    dur_list: list[int] = []
    sl_list: list[float] = []
    fric_list: list[float] = []
    sym_list: list[str] = []
    swap_per_day_list: list[float] = []

    for tr in trades:
        rv = tr.get("net_R_1x", tr.get("net_R", 0.0))
        r_list.append(float(rv))
        s_list.append(_extract_trade_side(tr))
        ep = float(tr.get("entry_price", 0.0))
        sl_dist = float(tr.get("sl_dist", 0.0))
        if sl_dist <= 0.0 and ep > 0.0 and tr.get("sl_price") is not None:
            sl_dist = abs(ep - float(tr["sl_price"]))
        if ep > 1e-9 and sl_dist > 0.0:
            sl_frac = max(0.0005, sl_dist / ep)
        else:
            leg_sl_fracs: list[float] = []
            for ek, sk in (("entry_price_a", "sl_price_a"), ("entry_price_b", "sl_price_b")):
                ev_leg = tr.get(ek)
                sv_leg = tr.get(sk)
                if ev_leg is not None and sv_leg is not None:
                    e_f = float(ev_leg)
                    s_f = float(sv_leg)
                    if e_f > 1e-9 and abs(e_f - s_f) > 0.0:
                        leg_sl_fracs.append(abs(e_f - s_f) / e_f)
            sl_frac = max(0.0005, float(np.mean(leg_sl_fracs))) if leg_sl_fracs else 0.01
        sl_list.append(sl_frac)

        f1x = float(tr.get("friction_over_sl_1x", tr.get("friction_over_sl", 0.02)))
        fric_list.append(min(0.45, max(0.0, f1x)))

        if is_swing:
            hb = tr.get("hold_bars")
            if hb is None and tr.get("entry_ts") is not None and tr.get("exit_ts") is not None:
                hb = max(1, int(round((int(tr["exit_ts"]) - int(tr["entry_ts"])) / 86400.0)))
            dur_val = max(1, int(hb if hb is not None else 2))
            sw_r = float(tr.get("swap_real_R", tr.get("swap_R", 0.0)))
            if sw_r < 0.0:
                swap_per_day_list.append((-sw_r) / float(max(1, dur_val)))
            else:
                swap_per_day_list.append(0.0)
        else:
            hm = tr.get("hold_minutes")
            if hm is None and tr.get("entry_ts") is not None and tr.get("exit_ts") is not None:
                hm = max(5, int((int(tr["exit_ts"]) - int(tr["entry_ts"])) // 60))
            dur_val = max(1, int(round(float(hm if hm is not None else 30) / 5.0)))
        dur_list.append(dur_val)
        sym_list.append(_extract_trade_symbol_key(tr))

    swap_drag_per_day_r = float(np.mean(swap_per_day_list)) if (is_swing and swap_per_day_list) else 0.0

    r_arr = np.asarray(r_list, dtype=np.float64)
    s_arr = np.asarray(s_list, dtype=np.int64)
    d_arr = np.asarray(dur_list, dtype=np.int64)
    sl_arr = np.asarray(sl_list, dtype=np.float64)
    f_arr = np.asarray(fric_list, dtype=np.float64)

    assets = universe.get("assets") if (universe is not None and isinstance(universe.get("assets"), Mapping)) else {}

    def _has_bars_for_key(sym_key: str) -> bool:
        if not sym_key:
            return False
        if sym_key in assets:
            return True
        pair = _split_pair_symbol(sym_key)
        return pair is not None and (pair[0] in assets or pair[1] in assets)

    uniq_syms = sorted({s for s in sym_list if _has_bars_for_key(s)})
    if not uniq_syms:
        return None, swap_drag_per_day_r

    def _get_single_symbol_bars(
        sym: str, *, force_d1: bool = False
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int] | None:
        aobj = assets.get(sym)
        if not isinstance(aobj, Mapping):
            return None
        if not force_d1 and not is_swing and isinstance(aobj.get("m1"), Mapping):
            if sym not in m5_cache:
                m1 = aobj["m1"]
                ts_m1 = np.asarray(m1["times_sec"], dtype=np.int64)
                q_m1 = np.asarray(m1["quotes"], dtype=np.float64)
                enforce_pre_holdout_ts(ts_m1, context=f"stage3.mc_m1:{sym}")
                m5_cache[sym] = resample_m1_quotes_to_m5_mid(ts_m1, q_m1)
            ts5, o5, h5, l5, c5 = m5_cache[sym]
            yr_start = int(datetime(min(clb_year_set), 1, 1, tzinfo=UTC).timestamp())
            yr_end = int(datetime(max(clb_year_set) + 1, 1, 1, tzinfo=UTC).timestamp())
            mask = (ts5 >= yr_start) & (ts5 < yr_end)
            if int(np.sum(mask)) >= 50:
                return ts5[mask], o5[mask], h5[mask], l5[mask], c5[mask], 300
        d1 = aobj.get("d1")
        if isinstance(d1, Mapping):
            ts_d = np.asarray(d1["times_sec"], dtype=np.int64)
            o_d = np.asarray(d1["open"], dtype=np.float64)
            h_d = np.asarray(d1["high"], dtype=np.float64)
            l_d = np.asarray(d1["low"], dtype=np.float64)
            c_d = np.asarray(d1["close"], dtype=np.float64)
            yrs_d = np.asarray(d1["years"], dtype=np.int32)
            enforce_pre_holdout_ts(ts_d, context=f"stage3.mc_d1:{sym}")
            mask = np.isin(yrs_d, list(clb_year_set))
            if int(np.sum(mask)) >= 20:
                return ts_d[mask], o_d[mask], h_d[mask], l_d[mask], c_d[mask], 86400
            if ts_d.size >= 20:
                return ts_d, o_d, h_d, l_d, c_d, 86400
        return None

    def _get_symbol_bars(
        sym_key: str,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int] | None:
        pair = _split_pair_symbol(sym_key)
        if pair is None:
            return _get_single_symbol_bars(sym_key)
        sym_a, sym_b = pair
        bars_a = _get_single_symbol_bars(sym_a)
        bars_b = _get_single_symbol_bars(sym_b)
        if bars_a is None:
            return bars_b
        if bars_b is None:
            return bars_a
        if bars_a[5] != bars_b[5]:
            bars_a = _get_single_symbol_bars(sym_a, force_d1=True) or bars_a
            bars_b = _get_single_symbol_bars(sym_b, force_d1=True) or bars_b
            if bars_a[5] != bars_b[5]:
                return bars_a
        ts_a, oa, ha, la, ca, bsec = bars_a
        ts_b, ob, hb, lb, cb, _ = bars_b
        common_ts, ia, ib = np.intersect1d(ts_a, ts_b, assume_unique=False, return_indices=True)
        min_req = 50 if bsec == 300 else 20
        if common_ts.size < min_req:
            return bars_a
        oa_c, ha_c, la_c, ca_c = oa[ia], ha[ia], la[ia], ca[ia]
        ob_c, hb_c, lb_c, cb_c = ob[ib], hb[ib], lb[ib], cb[ib]
        valid = (
            (oa_c > 1e-12)
            & (ob_c > 1e-12)
            & (ha_c > 1e-12)
            & (hb_c > 1e-12)
            & (la_c > 1e-12)
            & (lb_c > 1e-12)
            & (ca_c > 1e-12)
            & (cb_c > 1e-12)
        )
        if int(np.sum(valid)) < min_req:
            return bars_a
        ts_c = np.ascontiguousarray(common_ts[valid], dtype=np.int64)
        oa_v, ha_v, la_v, ca_v = oa_c[valid], ha_c[valid], la_c[valid], ca_c[valid]
        ob_v, hb_v, lb_v, cb_v = ob_c[valid], hb_c[valid], lb_c[valid], cb_c[valid]
        a0 = float(oa_v[0])
        b0 = float(ob_v[0])
        s_o = 100.0 * (oa_v / a0) / (ob_v / b0)
        s_c = 100.0 * (ca_v / a0) / (cb_v / b0)
        s_hh = 100.0 * (ha_v / a0) / (hb_v / b0)
        s_ll = 100.0 * (la_v / a0) / (lb_v / b0)
        s_h = np.maximum.reduce([s_o, s_c, s_hh, s_ll])
        s_l = np.minimum.reduce([s_o, s_c, s_hh, s_ll])
        return (
            ts_c,
            np.ascontiguousarray(s_o, dtype=np.float64),
            np.ascontiguousarray(s_h, dtype=np.float64),
            np.ascontiguousarray(s_l, dtype=np.float64),
            np.ascontiguousarray(s_c, dtype=np.float64),
            bsec,
        )

    if len(uniq_syms) == 1:
        bars = _get_symbol_bars(uniq_syms[0])
        if bars is None:
            return None, swap_drag_per_day_r
        ts_b, o_b, h_b, l_b, c_b, bar_sec = bars
        eff_allow_wk = bool(is_swing or bar_sec >= 86400)
        eff_durs = d_arr if (is_swing or bar_sec == 300) else np.ones(len(r_arr), dtype=np.int64)
        mc = random_entry_mc_on_bars(
            ts=ts_b,
            bar_o=o_b,
            bar_h=h_b,
            bar_l=l_b,
            bar_c=c_b,
            bar_sec=bar_sec,
            trade_r=r_arr,
            trade_sides=s_arr,
            trade_durs=eff_durs,
            trade_sl_fracs=sl_arr,
            trade_frics=f_arr,
            draws=int(draws),
            seed=int(seed),
            allow_weekend_gaps=eff_allow_wk,
            swap_drag_per_day_r=swap_drag_per_day_r if is_swing else 0.0,
        )
        return mc, swap_drag_per_day_r

    # Multi-symbol basket: aggregate independent per-symbol MC draw vectors!
    tot_unb = np.zeros(int(draws), dtype=np.float64)
    tot_same = np.zeros(int(draws), dtype=np.float64)
    buy_tot = np.zeros(int(draws), dtype=np.float64)
    sell_tot = np.zeros(int(draws), dtype=np.float64)
    matched_any = False

    for a_idx, sym in enumerate(uniq_syms):
        bars = _get_symbol_bars(sym)
        if bars is None:
            continue
        ts_b, o_b, h_b, l_b, c_b, bar_sec = bars
        amask = np.array([s == sym for s in sym_list], dtype=np.bool_)
        if not np.any(amask):
            continue
        matched_any = True
        eff_allow_wk = bool(is_swing or bar_sec >= 86400)
        eff_d = d_arr[amask] if (is_swing or bar_sec == 300) else np.ones(int(np.sum(amask)), dtype=np.int64)
        sw_drag = swap_drag_per_day_r if is_swing else 0.0

        if eff_allow_wk or abs(sw_drag) > 1e-15:
            _, u_vec = _random_entry_mc_ohlc_swing_kernel(
                ts_b, o_b, h_b, l_b, c_b, bar_sec,
                s_arr[amask], eff_d, sl_arr[amask], f_arr[amask],
                float(np.sum(r_arr[amask])), 0, int(draws), int(seed + a_idx * 13),
                eff_allow_wk, sw_drag,
            )
            _, sm_vec = _random_entry_mc_ohlc_swing_kernel(
                ts_b, o_b, h_b, l_b, c_b, bar_sec,
                s_arr[amask], eff_d, sl_arr[amask], f_arr[amask],
                float(np.sum(r_arr[amask])), 1, int(draws), int(seed + a_idx * 13 + 7),
                eff_allow_wk, sw_drag,
            )
        else:
            _, u_vec = _random_entry_mc_ohlc_kernel(
                ts_b, o_b, h_b, l_b, c_b, bar_sec,
                s_arr[amask], eff_d, sl_arr[amask], f_arr[amask],
                float(np.sum(r_arr[amask])), 0, int(draws), int(seed + a_idx * 13),
            )
            _, sm_vec = _random_entry_mc_ohlc_kernel(
                ts_b, o_b, h_b, l_b, c_b, bar_sec,
                s_arr[amask], eff_d, sl_arr[amask], f_arr[amask],
                float(np.sum(r_arr[amask])), 1, int(draws), int(seed + a_idx * 13 + 7),
            )
        tot_unb += u_vec
        tot_same += sm_vec

        bm = amask & (s_arr > 0)
        if np.any(bm):
            bd = d_arr[bm] if (is_swing or bar_sec == 300) else np.ones(int(np.sum(bm)), dtype=np.int64)
            _, b_vec = _random_entry_mc_ohlc_swing_kernel(
                ts_b, o_b, h_b, l_b, c_b, bar_sec,
                s_arr[bm], bd, sl_arr[bm], f_arr[bm],
                float(np.sum(r_arr[bm])), 1, int(draws), int(seed + a_idx * 13 + 19),
                eff_allow_wk, sw_drag,
            )
            buy_tot += b_vec
        sm = amask & (s_arr < 0)
        if np.any(sm):
            sd_arr = d_arr[sm] if (is_swing or bar_sec == 300) else np.ones(int(np.sum(sm)), dtype=np.int64)
            _, s_vec = _random_entry_mc_ohlc_swing_kernel(
                ts_b, o_b, h_b, l_b, c_b, bar_sec,
                s_arr[sm], sd_arr, sl_arr[sm], f_arr[sm],
                float(np.sum(r_arr[sm])), 1, int(draws), int(seed + a_idx * 13 + 29),
                eff_allow_wk, sw_drag,
            )
            sell_tot += s_vec

    if not matched_any:
        return None, swap_drag_per_day_r

    obs_sum = float(np.sum(r_arr))
    b_obs = float(np.sum(r_arr[s_arr > 0]))
    s_obs = float(np.sum(r_arr[s_arr < 0]))
    return {
        "mc_mode": "real_market_bars_swing_multi_asset" if is_swing else "real_market_bars_multi_asset",
        "allow_weekend_gaps": bool(is_swing),
        "swap_drag_per_day_r": round(swap_drag_per_day_r, 6),
        "draws": int(draws),
        "obs_sum_r": round(obs_sum, 2),
        "beat_rate_unbiased": round(float(np.mean(obs_sum > tot_unb + 1e-12)), 4),
        "null_unbiased_median_r": round(float(np.median(tot_unb)), 2),
        "null_unbiased_p90_r": round(float(np.quantile(tot_unb, 0.90)), 2),
        "beat_rate_same_side": round(float(np.mean(obs_sum > tot_same + 1e-12)), 4),
        "null_same_side_median_r": round(float(np.median(tot_same)), 2),
        "null_same_side_p90_r": round(float(np.quantile(tot_same, 0.90)), 2),
        "buy_beat_rate_vs_random_buy": (
            round(float(np.mean(b_obs > buy_tot + 1e-12)), 4) if int(np.sum(s_arr > 0)) >= 10 else None
        ),
        "buy_null_median_r": round(float(np.median(buy_tot)), 2) if int(np.sum(s_arr > 0)) >= 10 else None,
        "sell_beat_rate_vs_random_sell": (
            round(float(np.mean(s_obs > sell_tot + 1e-12)), 4) if int(np.sum(s_arr < 0)) >= 10 else None
        ),
        "sell_null_median_r": round(float(np.median(sell_tot)), 2) if int(np.sum(s_arr < 0)) >= 10 else None,
    }, swap_drag_per_day_r


# ---------------------------------------------------------------------------
# 3-Tier Funnel Classifier (`G3-TIER-CLASS`)
# ---------------------------------------------------------------------------


def classify_candidate_tier(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Classify a candidate into `TIER_1_FTMO_READY`, `TIER_2_PERSONAL_VAULT`, or `TIER_3_DEAD_NO_EDGE`.

    - `TIER_1_FTMO_READY`: passes ALL `G08` + Robustness + Timing + Fade + Swap + DD/Margin + 3-Crisis gates,
      belongs to `offensive3_primary_m200`, `research_council` verdict == `APPROVE_FOR_INCUBATION`
      (strictly rejecting `CONDITIONAL_RETEST`!), and `G7_pbo_cscv` executed & passed!
      Sub-tagged `M1_NATIVE_VERIFIED` if `data_resolution == NATIVE_M1_BIDASK`, else
      `PROVISIONAL_AWAITING_OWNER_M1_EXPORT`.
    - `TIER_2_PERSONAL_VAULT`: genuine standalone edge passing `BH-FDR` (`q <= 0.10`),
      `Random-Entry MC >= 90%`, `2x` friction net > 0 (`breakeven >= 2.0x`), Fade beat,
      Trim-5% Winners `PF > 1.0`, `zero_pos_swap > 0` (for Swing), and sample/sign floor,
      but failing ONLY Prop-specific constraints (`|r| < 0.15`, tail corr `< 0.35`, Swing margin,
      Prop DD / crisis floor, `CONDITIONAL_RETEST`, or Exploratory-only pool).
    - `TIER_3_DEAD_NO_EDGE`: killed honestly with full failure gate anatomy.
    """
    is_primary = bool(audit["is_primary"])
    is_swing = bool(audit["is_swing"])
    min_trades = int(audit["min_trades_cluster_b"])
    data_res = str(audit["data_resolution"])

    bh_q_prim = audit.get("bh_q_primary")
    bh_q_expl = audit.get("bh_q_exploratory")
    bh_edge_ok = (bh_q_prim is not None and float(bh_q_prim) <= 0.10) or (
        bh_q_expl is not None and float(bh_q_expl) <= 0.10
    )

    rb = audit["robustness_gate"]
    mc = rb["pillars"]["R1_random_entry_mc"]
    trim = rb["pillars"]["R3_top5_outlier_trim"]
    mc_ok = (
        float(mc.get("beat_rate_unbiased", 0.0)) >= 0.90
        and float(mc.get("beat_rate_same_side", 0.0)) >= 0.90
    )
    trim_ok = (
        float(trim.get("trimmed_winners_pf", 0.0)) > 1.0
        and float(trim.get("trimmed_winners_sum_r", 0.0)) > 0.0
    )

    net_1x = float(audit["net_r_1x"])
    net_2x = float(audit["net_r_2x"])
    net_zpos = float(audit["net_r_zero_pos_swap"])
    fade_1x = float(audit["fade_net_r_1x"])
    be_mult = float(audit["cost_breakeven_mult"])
    n_trades_b = int(audit["n_trades_clb"])

    failed_core: list[str] = []
    if not bh_edge_ok:
        failed_core.append("CORE_BH_FDR_GT_010")
    if not mc_ok:
        failed_core.append("CORE_RANDOM_ENTRY_MC_LT_90")
    if not (net_2x > 0.0 and be_mult >= 2.0):
        failed_core.append("CORE_COST_2X_FAIL")
    if not (net_1x > fade_1x):
        failed_core.append("CORE_FADE_BEAT_FAIL")
    if is_swing and not (net_zpos > 0.0):
        failed_core.append("CORE_ZERO_POS_SWAP_FAIL")
    if not trim_ok:
        failed_core.append("CORE_TRIM5_WINNERS_PF_LE_1")
    if not (n_trades_b >= min_trades and net_1x > 0.0):
        failed_core.append("CORE_SAMPLE_OR_SIGN_FAIL")

    # Strict G08 / FTMO Prop gates (separate from core edge so genuine Own-Book alpha lands in Tier 2!)
    council = audit["research_council"]
    council_verdict = str(council.get("verdict", "REJECT_KILLED"))
    council_gates = council.get("gates") or {}
    conditional_rejected = council_verdict == "CONDITIONAL_RETEST"

    g4 = council_gates.get("G4_orthogonality") or {}
    g7 = council_gates.get("G7_pbo_cscv")
    g2 = council_gates.get("G2_dsr_and_sharpe") or {}

    failed_prop: list[str] = []
    if not (is_primary and bh_q_prim is not None and float(bh_q_prim) <= 0.10):
        failed_prop.append("PROP_PRIMARY_M200_BH_FDR")
    if council_verdict != "APPROVE_FOR_INCUBATION":
        failed_prop.append(
            "PROP_COUNCIL_CONDITIONAL_RETEST_REJECTED"
            if conditional_rejected
            else f"PROP_COUNCIL_{council_verdict}"
        )
    if g7 is None:
        failed_prop.append("PROP_G7_PBO_MISSING")
    elif not bool(g7.get("passed", False)):
        failed_prop.append("PROP_G7_PBO_GT_050")

    corr_all = float(g4.get("corr_all", 1.0))
    corr_tail = float(g4.get("corr_tail_5pct", 1.0))
    if not (bool(g4.get("passed", False)) and abs(corr_all) < 0.15 and corr_tail < 0.35):
        failed_prop.append("PROP_PORT7E_ORTHOGONALITY")

    if not bool(g2.get("passed", False)):
        failed_prop.append("PROP_DSR_OR_SHARPE_FLOOR")
    dsr_emp_val = audit.get("dsr_empirical")
    if dsr_emp_val is not None and float(dsr_emp_val) < 0.50:
        failed_prop.append("PROP_DSR_EMPIRICAL_LT_050")
    if str(mc.get("mc_mode") or "") == "sign_flip_fallback":
        failed_prop.append("PROP_MC_SIGN_FLIP_FALLBACK_BLOCKED")
    if str(rb.get("verdict")) != "PASS_ROBUST":
        failed_prop.append(f"PROP_ROBUSTNESS_{rb.get('verdict')}")

    timing_perm = audit["timing_permutation"]
    if not (bool(timing_perm.get("passed", False)) and float(timing_perm.get("p_value", 1.0)) < 0.05):
        failed_prop.append("PROP_MATCHED_HOLD_TIMING_P_GE_005")

    max_dd_pct = float(audit["prop_max_dd_pct_at_risk"])
    worst_1d_pct = float(audit["prop_worst_1d_pct_at_risk"])
    if not (max_dd_pct < 10.0 and worst_1d_pct < 5.0):
        failed_prop.append("PROP_FTMO_DD_LIMIT_BREACH")

    if bool(audit.get("margin_breached", False)) or float(audit.get("peak_margin_util_frac", 0.0)) > 0.80 + 1e-9:
        failed_prop.append("PROP_SWING_MARGIN_BREACH")

    crisis = audit["crisis_stress_2018_2024"]
    if not bool(crisis.get("passed", False)):
        failed_prop.append("PROP_CRISIS_3WIN_FAIL")

    failed_all = [*failed_core, *failed_prop]
    if not failed_core and not failed_prop:
        tier = TIER_1_FTMO_READY
        sub_tag = TAG_M1_NATIVE_VERIFIED if data_res == RES_NATIVE_M1_BIDASK else TAG_PROVISIONAL_AWAITING_M1
        kill_reason = "PASSED_ALL_G08_AND_ROBUSTNESS_GATES"
    elif not failed_core:
        tier = TIER_2_PERSONAL_VAULT
        sub_tag = None
        kill_reason = "GENUINE_EDGE_FAILED_PROP_CONSTRAINTS: " + ", ".join(failed_prop)
    else:
        tier = TIER_3_DEAD_NO_EDGE
        sub_tag = None
        kill_reason = "KILLED_CORE_EDGE: " + ", ".join(failed_core)

    return {
        "tier": tier,
        "tier1_resolution_tag": sub_tag,
        "failed_core_gates": failed_core,
        "failed_prop_gates": failed_prop,
        "failed_all_gates": failed_all,
        "council_conditional_rejected": conditional_rejected,
        "kill_reason": kill_reason,
    }


# ---------------------------------------------------------------------------
# Compact Tracked Funnel Serialization (< 300 KB Programmatic Guarantee)
# ---------------------------------------------------------------------------


def _compact_candidate_card(rec: Mapping[str, Any], *, minimal: bool = False) -> dict[str, Any]:
    cls = rec["classification"]
    rc = rec["research_council"]
    gates = rc.get("gates") or {}
    g4 = gates.get("G4_orthogonality") or {}
    g7 = gates.get("G7_pbo_cscv") or {}
    rb_p = rec["robustness_gate"]["pillars"]
    mc = rb_p["R1_random_entry_mc"]
    tr = rb_p["R3_top5_outlier_trim"]
    card: dict[str, Any] = {
        "strategy_id": rec["strategy_id"],
        "alpha_family_id": rec["alpha_family_id"],
        "pool_tier": rec["pool_tier"],
        "tier": cls["tier"],
        "tier1_resolution_tag": cls["tier1_resolution_tag"],
        "data_resolution": rec["data_resolution"],
        "blindness_tier": normalize_blindness_tier(str(rec.get("blindness_tier", ""))),
        "is_swing": rec["is_swing"],
        "n_trades_clb": rec["n_trades_clb"],
        "net_r_1x": round(float(rec["net_r_1x"]), 3),
        "net_r_15x": round(float(rec["net_r_15x"]), 3),
        "net_r_2x": round(float(rec["net_r_2x"]), 3),
        "net_r_zero_pos_swap": round(float(rec["net_r_zero_pos_swap"]), 3),
        "fade_net_r_1x": round(float(rec["fade_net_r_1x"]), 3),
        "sharpe_clb": round(float(rec["sharpe_clb"]), 3),
        "dsr_council": round(float(rec["dsr_council"]), 4),
        "dsr_empirical": round(float(rec["dsr_empirical"]), 4),
        "p_sign_flip_50k": rec["p_sign_flip_50k"],
        "p_newey_west": rec["analytical_p"]["p_newey_west"],
        "bh_q_primary": rec["bh_q_primary"],
        "bh_q_exploratory": rec["bh_q_exploratory"],
        "pbo_cscv": g7.get("pbo"),
        "corr_port7e": g4.get("corr_all"),
        "tail_corr_port7e": g4.get("corr_tail_5pct"),
        "mc_unb": mc.get("beat_rate_unbiased"),
        "mc_same": mc.get("beat_rate_same_side"),
        "timing_p": rec["timing_permutation"]["p_value"],
        "trim5_win_pf": tr.get("trimmed_winners_pf"),
        "crisis_passed": rec["crisis_stress_2018_2024"]["passed"],
        "council_verdict": rc.get("verdict"),
    }
    if not minimal:
        card["symbols"] = rec["symbols"]
        card["failed_core_gates"] = cls["failed_core_gates"]
        card["failed_prop_gates"] = cls["failed_prop_gates"]
        card["worst_crisis_dd_r"] = rec["crisis_stress_2018_2024"]["worst_crisis_dd_r"]
    return card


def build_compact_funnel_payload(full_results: Mapping[str, Any]) -> dict[str, Any]:
    """Construct compact tracked funnel summary strictly bounded under `MAX_TRACKED_FUNNEL_BYTES`."""
    cands = list(full_results["candidates"])
    tier1 = [c for c in cands if c["classification"]["tier"] == TIER_1_FTMO_READY]
    tier2 = [c for c in cands if c["classification"]["tier"] == TIER_2_PERSONAL_VAULT]
    tier3 = [c for c in cands if c["classification"]["tier"] == TIER_3_DEAD_NO_EDGE]

    tier1.sort(key=lambda c: float(c["sharpe_clb"]), reverse=True)
    tier2.sort(key=lambda c: float(c["sharpe_clb"]), reverse=True)
    tier3.sort(key=lambda c: float(c["sharpe_clb"]), reverse=True)

    core_fail_counts: Counter[str] = Counter()
    prop_fail_counts: Counter[str] = Counter()
    eval_by_blind_counts: Counter[str] = Counter()
    for c in cands:
        eval_by_blind_counts[normalize_blindness_tier(str(c.get("blindness_tier", "")))] += 1
        for g in c["classification"]["failed_core_gates"]:
            core_fail_counts[g] += 1
        for g in c["classification"]["failed_prop_gates"]:
            prop_fail_counts[g] += 1
    evaluated_by_blindness_tier = dict(sorted(eval_by_blind_counts.items()))
    funnel_counts = dict(full_results["funnel_counts"])
    funnel_counts["evaluated_by_blindness_tier"] = evaluated_by_blindness_tier

    return {
        "schema_version": "naqex-offensive3-alpha-funnel-v1",
        "generated_utc": full_results["generated_utc"],
        "campaign_run_id": full_results["campaign_run_id"],
        "git_sha": full_results["git_sha"],
        "data_sha": full_results["data_sha"],
        "holdout_lock_sha256": full_results["holdout_lock_sha256"],
        "holdout_rows_analysed": 0,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "cluster_a_years": list(CLUSTER_A_YEARS),
        "cluster_b_years": list(CLUSTER_B_YEARS),
        "statistical_config": full_results["statistical_config"],
        "duckdb_ledger_summary": full_results["duckdb_ledger_summary"],
        "effective_trials_n_eff": full_results["effective_trials_n_eff"],
        "campaign_pbo": full_results["campaign_pbo"],
        "evaluated_by_blindness_tier": evaluated_by_blindness_tier,
        "funnel_counts": funnel_counts,
        "family_summaries": full_results["family_summaries"],
        "gate_failure_anatomy": {
            "core_gate_failures": dict(core_fail_counts.most_common()),
            "prop_gate_failures": dict(prop_fail_counts.most_common()),
        },
        "tier1_ftmo_ready": [_compact_candidate_card(c) for c in tier1],
        "tier2_personal_vault": [_compact_candidate_card(c) for c in tier2],
        "tier3_dead_top20_near_misses": [_compact_candidate_card(c, minimal=True) for c in tier3[:20]],
    }


def write_compact_funnel_json(
    full_results: Mapping[str, Any],
    output_path: str | Path,
    *,
    max_bytes: int = MAX_TRACKED_FUNNEL_BYTES,
) -> dict[str, Any]:
    """Serialize and atomically write compact funnel JSON enforcing `< max_bytes` fail-closed."""
    if isinstance(max_bytes, bool) or int(max_bytes) < 4096:
        raise ValueError(f"max_bytes must be >= 4096, got {max_bytes!r}")

    payload = build_compact_funnel_payload(full_results)

    def _encode(doc: Mapping[str, Any], *, compact: bool) -> bytes:
        if compact:
            txt = json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        else:
            txt = json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        return txt.encode("utf-8")

    raw = _encode(payload, compact=False)
    compaction_level = 0
    if len(raw) >= max_bytes:
        # Level 1: minimize Tier 2 & drop Tier 3 near-miss rows (preserving 100% of Tier 1 + counts + anatomy)
        compaction_level = 1
        cands = list(full_results["candidates"])
        tier2 = sorted(
            [c for c in cands if c["classification"]["tier"] == TIER_2_PERSONAL_VAULT],
            key=lambda c: float(c["sharpe_clb"]),
            reverse=True,
        )
        payload["tier2_personal_vault"] = [_compact_candidate_card(c, minimal=True) for c in tier2]
        payload["tier3_dead_top20_near_misses"] = []
        raw = _encode(payload, compact=False)

    if len(raw) >= max_bytes:
        # Level 2: compact separators
        compaction_level = 2
        raw = _encode(payload, compact=True)

    if len(raw) >= max_bytes:
        # Level 3: cap Tier 2 cards to top 100 while preserving full Tier 1 & aggregate counts
        compaction_level = 3
        payload["tier2_truncated_count"] = max(0, len(payload["tier2_personal_vault"]) - 100)
        payload["tier2_personal_vault"] = payload["tier2_personal_vault"][:100]
        raw = _encode(payload, compact=True)

    if len(raw) >= max_bytes:
        raise ValueError(f"FUNNEL_SIZE_LIMIT_EXCEEDED: serialized bytes ({len(raw)}) >= limit ({max_bytes})")

    out_p = Path(output_path)
    _atomic_write_bytes(out_p, raw)
    return {
        "path": str(out_p),
        "bytes": len(raw),
        "max_bytes": int(max_bytes),
        "compaction_level": compaction_level,
    }


# ---------------------------------------------------------------------------
# Main Stage 3 Blind Cluster B Orchestrator
# ---------------------------------------------------------------------------


def _select_pbo_slices(n_obs: int, preferred: int = PBO_N_SLICES_DEFAULT) -> int:
    """Choose valid even `n_slices >= 4` so `compute_pbo_cscv` ALWAYS executes cleanly."""
    if n_obs < 8:
        raise ValueError(f"Insufficient Cluster B observations ({n_obs}) for CSCV PBO (need >= 8)")
    target = int(preferred)
    if target < 4 or target % 2 != 0:
        target = 16
    while target >= 4:
        if n_obs >= target and (target // 2) * (n_obs // target) >= 2:
            return target
        target -= 2
    return 4


def run_stage3_blind_clb(
    *,
    candidates_dir: str | Path | None = None,
    modules_dir: str | Path | None = None,
    family_modules: Mapping[str, Any] | None = None,
    family_ids: Sequence[str] | None = None,
    universe: Mapping[str, Any] | None = None,
    incumbent_daily_returns: Mapping[str, float] | None = None,
    duckdb_path: str | Path = DEFAULT_DUCKDB_PATH,
    registry_path: str | Path | None = None,
    full_results_path: str | Path | None = DEFAULT_FULL_RESULTS_PATH,
    tracked_funnel_path: str | Path | None = DEFAULT_TRACKED_FUNNEL_PATH,
    campaign_run_id: str | None = None,
    sign_flip_draws: int = SIGN_FLIP_DRAWS,
    timing_perm_draws: int = TIMING_PERM_DRAWS,
    mc_draws: int = MC_DRAWS_DEFAULT,
    pbo_n_slices: int = PBO_N_SLICES_DEFAULT,
    risk_frac: float = 0.005,
    verify_sha: bool = True,
    seed: int = 20261127,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Execute ONE SINGLE BLIND PASS of Stage 3 Cluster B validation, Dual-Ledger BH-FDR/PBO & 3-Tier Funnel."""
    t0 = time.perf_counter()
    ws = resolve_workspace_root(root)
    lock_sha = assert_holdout_locked()

    if isinstance(risk_frac, bool) or not math.isfinite(float(risk_frac)) or float(risk_frac) <= 0.0:
        raise ValueError(f"risk_frac must be finite > 0, got {risk_frac!r}")

    # 1. Load & validate all Cluster A candidate checkpoints (enforcing <=200 primary, <=1200 exploratory, 2018-2020)
    ckpt_bundle = load_all_family_checkpoints(
        candidates_dir=candidates_dir,
        family_ids=family_ids,
        verify_sha=verify_sha,
        root=ws,
    )
    all_records: list[dict[str, Any]] = ckpt_bundle["all_records"]
    if not all_records:
        raise ValueError("Zero candidates loaded from Cluster A checkpoints")

    # 2. Load dynamic family modules (`fam01..fam12`) & verify every checkpoint family resolves cleanly
    mod_reg = dict(family_modules) if family_modules is not None else discover_family_modules(modules_dir=modules_dir)
    resolved_mods: dict[str, Any] = {}
    for fid in ckpt_bundle["family_ids"]:
        resolved_mods[fid] = resolve_module_for_family(fid, mod_reg)

    # 3. Load 28-symbol sealed Dev universe & PORT_7E incumbent daily returns (strictly < 2025-01-01)
    eff_universe = (
        universe
        if universe is not None
        else load_universe_28(load_m1=True, load_d1=True, years=ALL_DEV_YEARS, verify_sha=verify_sha, root=ws)
    )
    cal_clb = _build_weekday_calendar(CLUSTER_B_YEARS)
    cal_cla = _build_weekday_calendar(CLUSTER_A_YEARS)
    cal_all = [*cal_cla, *cal_clb]
    enforce_pre_holdout_dates(cal_all, context="stage3.dev_calendar")

    if incumbent_daily_returns is not None:
        inc_map, inc_vec = _normalize_daily_pnl_map(
            incumbent_daily_returns, cal_clb, context="stage3.incumbent_override"
        )
    else:
        inc_raw = load_port7e_incumbent_clb_daily(cluster_b_years=CLUSTER_B_YEARS)
        inc_map, inc_vec = _normalize_daily_pnl_map(inc_raw, cal_clb, context="stage3.port7e_incumbent")
    _ = inc_map

    # 4. ONE SINGLE BLIND PASS on CLUSTER_B_YEARS = (2021, 2022, 2023, 2024) per candidate!
    evaluated_clb_ids: set[str] = set()
    staged: list[dict[str, Any]] = []
    clb_year_set = set(CLUSTER_B_YEARS)

    for idx, rec in enumerate(all_records):
        sid = rec["strategy_id"]
        if sid in evaluated_clb_ids:
            raise RuntimeError(f"DOUBLE_BLIND_EVAL_BLOCKED: candidate {sid!r} attempted >1 Cluster B evaluation")
        evaluated_clb_ids.add(sid)

        fid = rec["alpha_family_id"]
        spec = rec["spec"]
        mod = resolved_mods[fid]

        eval_b = mod.evaluate_candidate(spec, eff_universe, CLUSTER_B_YEARS)
        if not isinstance(eval_b, Mapping):
            raise ValueError(f"evaluate_candidate for {sid!r} must return a mapping")

        trades_b = list(eval_b.get("trades") or [])
        for tr in trades_b:
            if tr.get("exit_ts") is not None:
                enforce_pre_holdout_ts(int(tr["exit_ts"]), context=f"stage3.clb_trade_exit_ts:{sid}")
            if tr.get("entry_ts") is not None:
                enforce_pre_holdout_ts(int(tr["entry_ts"]), context=f"stage3.clb_trade_entry_ts:{sid}")
            for dkey in ("entry_date", "exit_date"):
                if tr.get(dkey):
                    enforce_pre_holdout_dates([str(tr[dkey])], context=f"stage3.clb_trade_{dkey}:{sid}")

        dmap_1x, vec_1x = _normalize_daily_pnl_map(
            eval_b.get("daily_pnl_1x"), cal_clb, context=f"stage3.clb_1x:{sid}"
        )
        _, vec_15x = _normalize_daily_pnl_map(
            eval_b.get("daily_pnl_15x"), cal_clb, context=f"stage3.clb_15x:{sid}"
        )
        _, vec_2x = _normalize_daily_pnl_map(
            eval_b.get("daily_pnl_2x"), cal_clb, context=f"stage3.clb_2x:{sid}"
        )
        _, vec_zpos = _normalize_daily_pnl_map(
            eval_b.get("daily_pnl_zero_pos_swap", eval_b.get("daily_pnl_1x")),
            cal_clb,
            context=f"stage3.clb_zpos:{sid}",
        )
        fade_raw = eval_b.get("fade_daily_pnl_1x")
        if fade_raw is not None:
            _, vec_fade = _normalize_daily_pnl_map(fade_raw, cal_clb, context=f"stage3.clb_fade:{sid}")
        else:
            vec_fade = None

        is_swing = _infer_is_swing_candidate(spec, eval_b, trades_b)
        symbols = _extract_candidate_symbols(spec, trades_b, include_leaders=True)
        traded_symbols = _extract_candidate_symbols(spec, trades_b, include_leaders=False)
        data_res, b_tier = _resolve_resolution_and_blindness(spec, eval_b, trades_b, eff_universe)
        allow_uni = bool(eval_b.get("allow_unidirectional", spec.get("allow_unidirectional", False)))

        net_1x = float(np.sum(vec_1x))
        net_15x = float(np.sum(vec_15x))
        net_2x = float(np.sum(vec_2x))
        net_zpos = float(np.sum(vec_zpos))
        fade_1x = float(np.sum(vec_fade)) if vec_fade is not None else -net_1x

        sd_1x = float(np.std(vec_1x, ddof=1)) if vec_1x.size >= 2 else 0.0
        sharpe_b = (float(np.mean(vec_1x)) / sd_1x) * math.sqrt(252.0) if sd_1x > 1e-12 else 0.0
        eq_b = np.cumsum(vec_1x)
        pk_b = np.maximum(0.0, np.maximum.accumulate(eq_b))
        max_dd_r_b = float(np.max(pk_b - eq_b)) if eq_b.size else 0.0
        worst_1d_r_b = float(np.min(vec_1x)) if vec_1x.size else 0.0

        cost_drag_1x = net_1x - net_2x
        if cost_drag_1x > 1e-9:
            be_mult = 1.0 + net_1x / cost_drag_1x
        else:
            be_mult = 99.0 if net_1x > 0.0 else 0.0

        # Sign-flip permutation p-value (`draws=50,000`) + Student-t & Newey-West HAC cross-check
        sf_info = compute_sign_flip_p_50k(vec_1x, vec_fade, draws=int(sign_flip_draws), seed=int(seed + idx * 31))
        an_info = compute_student_t_and_newey_west_p(vec_1x)

        # Margin audit extraction (Swing leverage safety)
        margin_audit = eval_b.get("margin_audit") if isinstance(eval_b.get("margin_audit"), Mapping) else {}
        peak_margin_util = float(margin_audit.get("peak_portfolio_margin_util_frac", 0.0))
        if peak_margin_util <= 0.0 and trades_b:
            peak_margin_util = max(float(tr.get("margin_util_frac", 0.0)) for tr in trades_b)
        margin_breached = bool(margin_audit.get("portfolio_margin_breached", False)) or (peak_margin_util > 0.80 + 1e-9)

        staged.append(
            {
                "index": idx,
                "strategy_id": sid,
                "alpha_family_id": fid,
                "candidate_id": rec["candidate_id"],
                "pool_tier": rec["pool_tier"],
                "is_primary": bool(rec["is_primary"]),
                "spec": spec,
                "eval_b": eval_b,
                "trades_b": trades_b,
                "n_trades_clb": len(trades_b),
                "is_swing": is_swing,
                "min_trades_cluster_b": 30 if is_swing else 50,
                "symbols": symbols,
                "traded_symbols": traded_symbols,
                "data_resolution": data_res,
                "blindness_tier": b_tier,
                "allow_unidirectional": allow_uni,
                "daily_map_1x_b": dmap_1x,
                "vec_1x_b": vec_1x,
                "vec_15x_b": vec_15x,
                "vec_2x_b": vec_2x,
                "vec_zpos_b": vec_zpos,
                "vec_fade_b": vec_fade,
                "net_r_1x": net_1x,
                "net_r_15x": net_15x,
                "net_r_2x": net_2x,
                "net_r_zero_pos_swap": net_zpos,
                "fade_net_r_1x": fade_1x,
                "cost_breakeven_mult": be_mult,
                "sharpe_clb": sharpe_b,
                "max_dd_r_clb": max_dd_r_b,
                "worst_1d_r_clb": worst_1d_r_b,
                "prop_max_dd_pct_at_risk": round(max_dd_r_b * float(risk_frac) * 100.0, 3),
                "prop_worst_1d_pct_at_risk": round(abs(min(0.0, worst_1d_r_b)) * float(risk_frac) * 100.0, 3),
                "peak_margin_util_frac": round(peak_margin_util, 6),
                "margin_breached": margin_breached,
                "sign_flip": sf_info,
                "p_sign_flip_50k": float(sf_info["p_value"]),
                "analytical_p": an_info,
            }
        )

    # 5. Build aligned Cl.B return matrices for N_eff, Empirical DSR, and mandatory G7 CSCV PBO (B4!)
    all_mat = np.column_stack([s["vec_1x_b"] for s in staged])  # (T_clb, M_all)
    prim_items = [s for s in staged if s["is_primary"]]
    prim_mat = (
        np.column_stack([s["vec_1x_b"] for s in prim_items])
        if prim_items
        else np.empty((len(cal_clb), 0), dtype=np.float64)
    )

    n_eff_exploratory = compute_effective_independent_trials(all_mat)
    n_eff_primary = compute_effective_independent_trials(prim_mat)

    eff_pbo_slices = _select_pbo_slices(len(cal_clb), preferred=int(pbo_n_slices))
    fam_pbo_matrices: dict[str, np.ndarray] = {}
    fam_pbo_results: dict[str, dict[str, Any]] = {}
    n_eff_by_family: dict[str, dict[str, Any]] = {}

    for fid in ckpt_bundle["family_ids"]:
        f_items = [s for s in staged if s["alpha_family_id"] == fid]
        if not f_items:
            continue
        f_mat = np.column_stack([s["vec_1x_b"] for s in f_items])
        n_eff_by_family[fid] = compute_effective_independent_trials(f_mat)
        # B4 invariant: PBO matrix MUST have >= 2 columns so G7_pbo_cscv NEVER skips!
        if f_mat.shape[1] >= 2:
            pbo_mat = f_mat
        elif all_mat.shape[1] >= 2:
            pbo_mat = all_mat
        else:
            # Degenerate 1-candidate campaign fallback: pair with zero-return benchmark column
            pbo_mat = np.column_stack([f_mat[:, 0], np.zeros(len(cal_clb), dtype=np.float64)])
        fam_pbo_matrices[fid] = pbo_mat
        pres = compute_pbo_cscv(pbo_mat, n_slices=eff_pbo_slices)
        fam_pbo_results[fid] = {
            "pbo": round(float(pres.pbo), 4),
            "is_overfit": bool(pres.is_overfit),
            "n_slices": int(pres.n_slices),
            "n_trials": int(pres.n_trials),
            "n_combinations": int(pres.n_combinations),
            "prob_oos_nonpositive_sr": round(float(pres.prob_oos_nonpositive_sr), 4),
        }

    camp_pbo_prim: dict[str, Any] | None = None
    if prim_mat.shape[1] >= 2:
        pr_p = compute_pbo_cscv(prim_mat, n_slices=eff_pbo_slices)
        camp_pbo_prim = {
            "pbo": round(float(pr_p.pbo), 4),
            "is_overfit": bool(pr_p.is_overfit),
            "n_slices": int(pr_p.n_slices),
            "n_trials": int(pr_p.n_trials),
        }
    camp_pbo_expl: dict[str, Any] | None = None
    if all_mat.shape[1] >= 2:
        pr_e = compute_pbo_cscv(all_mat, n_slices=eff_pbo_slices)
        camp_pbo_expl = {
            "pbo": round(float(pr_e.pbo), 4),
            "is_overfit": bool(pr_e.is_overfit),
            "n_slices": int(pr_e.n_slices),
            "n_trials": int(pr_e.n_trials),
        }

    # Empirical trial-variance DSR cross-check across Primary & Exploratory pools
    prim_sharpes = [float(s["sharpe_clb"]) for s in prim_items]
    expl_sharpes = [float(s["sharpe_clb"]) for s in staged]

    for s in staged:
        pool_sh = prim_sharpes if (s["is_primary"] and len(prim_sharpes) >= 2) else expl_sharpes
        if len(pool_sh) >= 2 and float(np.std(s["vec_1x_b"], ddof=1)) > 1e-12:
            dsr_emp_res = deflated_sharpe_ratio_empirical(
                s["vec_1x_b"],
                trial_sharpes=pool_sh,
                n_trials=len(pool_sh),
                annualization_days=252,
                sharpes_are_annualized=True,
            )
            s["dsr_empirical"] = round(float(dsr_emp_res.dsr), 4)
        else:
            s["dsr_empirical"] = 0.0

    # 6. Record 100% of Cluster B trials (pass + fail!) into ExperimentLedger under BOTH family_ids!
    git_sha = _resolve_git_sha(ws)
    data_sha = ckpt_bundle["campaign_data_sha"]
    run_ts = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    eff_campaign_run_id = campaign_run_id or f"off3-clb-{run_ts}-{data_sha[:8]}"

    ledger = ExperimentLedger(duckdb_path=duckdb_path, registry_path=registry_path)
    try:
        for s in staged:
            sid = s["strategy_id"]
            fid = s["alpha_family_id"]
            pbo_val = float(fam_pbo_results[fid]["pbo"])
            base_kwargs = {
                "git_sha": git_sha,
                "data_sha": data_sha,
                "strategy_id": sid,
                "sharpe": float(s["sharpe_clb"]),
                "dsr": float(s["dsr_empirical"]),
                "pbo": pbo_val,
                "p_value": float(s["p_sign_flip_50k"]),
            }
            if s["is_primary"]:
                ledger.record_experiment(
                    run_id=f"{eff_campaign_run_id}__prim__{sid}",
                    family_id=CAMPAIGN_PRIMARY_FAMILY_ID,
                    **base_kwargs,
                )
            ledger.record_experiment(
                run_id=f"{eff_campaign_run_id}__expl__{sid}",
                family_id=CAMPAIGN_EXPLORATORY_FAMILY_ID,
                **base_kwargs,
            )

        integrity_info = ledger.verify_integrity()
        m_primary_ledger = int(ledger.get_cumulative_trial_count(CAMPAIGN_PRIMARY_FAMILY_ID))
        m_exploratory_ledger = int(ledger.get_cumulative_trial_count(CAMPAIGN_EXPLORATORY_FAMILY_ID))

        # Authoritative global BH-FDR from DuckDB ledger for BOTH campaign pools!
        prim_rows = ledger.query_family(CAMPAIGN_PRIMARY_FAMILY_ID)
        expl_rows = ledger.query_family(CAMPAIGN_EXPLORATORY_FAMILY_ID)
        prim_q_vec = benjamini_hochberg([float(r["p_value"]) for r in prim_rows])
        expl_q_vec = benjamini_hochberg([float(r["p_value"]) for r in expl_rows])

        bh_q_primary_by_sid: dict[str, float] = {}
        for row, qv in zip(prim_rows, prim_q_vec, strict=True):
            sid_r = str(row["strategy_id"])
            bh_q_primary_by_sid[sid_r] = max(bh_q_primary_by_sid.get(sid_r, 0.0), float(qv))

        bh_q_exploratory_by_sid: dict[str, float] = {}
        for row, qv in zip(expl_rows, expl_q_vec, strict=True):
            sid_r = str(row["strategy_id"])
            bh_q_exploratory_by_sid[sid_r] = max(bh_q_exploratory_by_sid.get(sid_r, 0.0), float(qv))

        # 7. Run RobustnessGate, Timing Permutation, Research Council (with G7 PBO!), Crisis Stress, & 3-Tier Classifier
        m5_cache: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
        final_candidates: list[dict[str, Any]] = []

        for s in staged:
            sid = s["strategy_id"]
            fid = s["alpha_family_id"]
            spec = s["spec"]
            trades_b = s["trades_b"]
            is_swing = bool(s["is_swing"])
            idx = int(s["index"])

            # Cluster A returns (strictly 2018-2020 — NEVER touches Cluster B again!)
            cla_raw = spec.get("cluster_a_daily_pnl")
            if cla_raw is not None:
                dmap_1x_a, vec_1x_a = _normalize_daily_pnl_map(
                    cla_raw, cal_cla, context=f"stage3.cla_ckpt:{sid}"
                )
            else:
                eval_a = resolved_mods[fid].evaluate_candidate(spec, eff_universe, CLUSTER_A_YEARS)
                dmap_1x_a, vec_1x_a = _normalize_daily_pnl_map(
                    eval_a.get("daily_pnl_1x"), cal_cla, context=f"stage3.cla_eval:{sid}"
                )

            # Real-market Random-Entry MC (Swing-safe with allow_weekend_gaps & swap drag for Swing!)
            mc_res, swap_drag_r = _run_candidate_random_entry_mc(
                trades=trades_b,
                is_swing=is_swing,
                universe=eff_universe,
                m5_cache=m5_cache,
                clb_year_set=clb_year_set,
                draws=int(mc_draws),
                seed=int(seed + idx * 101),
            )

            t_r = np.array([float(tr.get("net_R_1x", tr.get("net_R", 0.0))) for tr in trades_b], dtype=np.float64)
            t_sides = np.array([_extract_trade_side(tr) for tr in trades_b], dtype=np.int64)
            t_days = [str(tr.get("exit_date") or tr.get("entry_date")) for tr in trades_b]
            t_holds = [
                max(
                    1,
                    int(
                        tr.get("hold_bars")
                        if tr.get("hold_bars") is not None
                        else (
                            max(1, int(round((int(tr["exit_ts"]) - int(tr["entry_ts"])) / 86400.0)))
                            if (is_swing and tr.get("entry_ts") is not None and tr.get("exit_ts") is not None)
                            else 1
                        )
                    ),
                )
                for tr in trades_b
            ]

            rb_thresholds = RobustnessThresholds(
                mc_draws=int(mc_draws),
                allow_unidirectional=bool(s["allow_unidirectional"]),
                outlier_trim_basis="winners",
                min_trimmed_pf=1.0,
                allow_weekend_gaps=is_swing,
                swap_drag_per_day_r=swap_drag_r if is_swing else 0.0,
                allow_sign_flip_fallback=False,
            )

            # Fallback close series if symbol wasn't in universe assets
            closes_fb: np.ndarray | None = None
            if mc_res is None and eff_universe is not None and isinstance(eff_universe.get("assets"), Mapping):
                for sym in s["symbols"]:
                    aobj = eff_universe["assets"].get(sym)
                    if isinstance(aobj, Mapping) and isinstance(aobj.get("d1"), Mapping):
                        closes_fb = np.asarray(aobj["d1"]["close"], dtype=np.float64)
                        break

            if len(t_r) > 0:
                rb_report = evaluate_robustness_gate(
                    strategy_id=sid,
                    trade_r=t_r,
                    trade_sides=t_sides,
                    trade_days=t_days,
                    mc_result=mc_res,
                    closes=closes_fb,
                    trade_durs=t_holds if is_swing else None,
                    thresholds=rb_thresholds,
                    seed=int(seed + idx * 37),
                )
            else:
                rb_report = {
                    "schema": "naqex-robustness-gate-v1",
                    "strategy_id": sid,
                    "order_send_capable": ORDER_SEND_CAPABLE,
                    "holdout_rows_analysed": 0,
                    "n_trades": 0,
                    "total_sum_r": 0.0,
                    "profit_factor": 0.0,
                    "passed": False,
                    "verdict": "FAIL_FRAGILE",
                    "failed_pillars": [
                        "R1_random_entry_mc",
                        "R2_buy_sell_symmetry",
                        "R3_top5_outlier_trim",
                        "R4_worst_year_stability",
                    ],
                    "ranking_score_worst_year_p10_r": 0.0,
                    "pillars": {
                        "R1_random_entry_mc": {"beat_rate_unbiased": 0.0, "beat_rate_same_side": 0.0, "passed": False},
                        "R2_buy_sell_symmetry": {"passed": False},
                        "R3_top5_outlier_trim": {
                            "passed": False,
                            "trimmed_winners_pf": 0.0,
                            "trimmed_winners_sum_r": 0.0,
                        },
                        "R4_worst_year_stability": {"passed": False},
                    },
                }

            # Matched-Hold Timing Permutation (`p < 0.05`; preserve pair `'SYM_A/SYM_B'` keys for spread returns)
            pair_keys_for_timing: list[str] = []
            seen_pair_keys: set[str] = set()
            for tr in trades_b:
                tkey = _extract_trade_symbol_key(tr)
                if "/" in tkey and tkey not in seen_pair_keys:
                    seen_pair_keys.add(tkey)
                    pair_keys_for_timing.append(tkey)
            timing_syms = pair_keys_for_timing if pair_keys_for_timing else s["traded_symbols"]
            mkt_daily_clb = _build_underlying_market_daily_returns(timing_syms, eff_universe, cal_clb)
            timing_res = matched_hold_timing_permutation_p(
                mkt_daily_clb,
                t_days,
                t_r,
                draws=int(timing_perm_draws),
                seed=int(seed + idx * 53),
                hold_bars=t_holds,
                trade_sides=t_sides,
                alpha=0.05,
            )

            # Build HypothesisCard + EvidenceBundle with EXPLICIT `pbo_returns_matrix` (B4!) & G08 KillCriteria
            kc = build_g08_kill_criteria(is_intraday=not is_swing)
            econ_rat = str(spec.get("economic_rationale") or "").strip()
            counterparty = str(spec.get("counterparty_mechanism") or "").strip()
            invariants = tuple(
                str(x)
                for x in (
                    spec.get("causal_invariants")
                    or ("shift=1_causal_features", "hard_sl_mandatory", "holdout_rows_analysed=0")
                )
            )
            eff_ledger_fam = CAMPAIGN_PRIMARY_FAMILY_ID if s["is_primary"] else CAMPAIGN_EXPLORATORY_FAMILY_ID
            eff_m_trial = m_primary_ledger if s["is_primary"] else m_exploratory_ledger

            card = propose_hypothesis(
                hypothesis_id=sid,
                title=str(spec.get("title") or spec.get("candidate_id") or sid),
                asset_universe=tuple(s["symbols"]),
                timeframe=str(spec.get("timeframe") or ("D1" if is_swing else "M1")),
                counterparty_mechanism=counterparty,
                economic_rationale=econ_rat,
                causal_invariants=invariants,
                n_trials_cumulative=max(1, eff_m_trial),
                kill_criteria=kc,
            )

            pbo_matrix_for_cand = fam_pbo_matrices[fid]
            pool_sh_for_cand = prim_sharpes if (s["is_primary"] and len(prim_sharpes) >= 2) else expl_sharpes
            evidence = EvidenceBundle(
                cluster_a_returns=vec_1x_a,
                cluster_b_returns=s["vec_1x_b"],
                p_value_raw=float(s["p_sign_flip_50k"]),
                family_p_values=(float(s["p_sign_flip_50k"]),),
                candidate_index_in_family=0,
                cost_1x_net=float(s["net_r_1x"]),
                cost_2x_net=float(s["net_r_2x"]),
                n_trades_cluster_b=int(s["n_trades_clb"]),
                incumbent_daily_returns=inc_vec,
                annualization_days=252.0,
                holdout_rows_analysed=0,
                robustness_report=rb_report,
                cluster_b_dates=tuple(cal_clb),
                incumbent_dates=tuple(cal_clb),
                pbo_returns_matrix=pbo_matrix_for_cand,
                pbo_n_slices=eff_pbo_slices,
                trial_sharpes=tuple(pool_sh_for_cand),
                trial_sharpes_are_annualized=True,
            )

            council_verdict = critique_proposal(
                card,
                evidence,
                ledger=ledger,
                family_id=eff_ledger_fam,
                require_incumbent=True,
                require_robustness_gate=True,
                strict_gates=True,
            )

            # Hard B4 fail-closed guarantee: G7_pbo_cscv MUST be present in gates!
            if "G7_pbo_cscv" not in (council_verdict.get("gates") or {}):
                raise RuntimeError(f"B4_INVARIANT_BREACH: G7_pbo_cscv missing from research_council gates for {sid!r}")

            # Post-Cl.B 3-Crisis Stress Windows on combined 2018-2024 Dev daily PnL
            daily_all_dev = {**dmap_1x_a, **s["daily_map_1x_b"]}
            crisis_res = evaluate_crisis_stress_windows(daily_all_dev, risk_frac=float(risk_frac))

            bh_q_prim = round(bh_q_primary_by_sid[sid], 6) if sid in bh_q_primary_by_sid else None
            bh_q_expl = round(bh_q_exploratory_by_sid[sid], 6) if sid in bh_q_exploratory_by_sid else None
            dsr_council = float(council_verdict["gates"]["G2_dsr_and_sharpe"]["dsr_b"])

            audit_rec: dict[str, Any] = {
                "strategy_id": sid,
                "alpha_family_id": fid,
                "candidate_id": s["candidate_id"],
                "pool_tier": s["pool_tier"],
                "is_primary": s["is_primary"],
                "is_swing": is_swing,
                "min_trades_cluster_b": s["min_trades_cluster_b"],
                "symbols": s["symbols"],
                "data_resolution": s["data_resolution"],
                "blindness_tier": s["blindness_tier"],
                "allow_unidirectional": s["allow_unidirectional"],
                "n_trades_clb": s["n_trades_clb"],
                "net_r_1x": round(float(s["net_r_1x"]), 6),
                "net_r_15x": round(float(s["net_r_15x"]), 6),
                "net_r_2x": round(float(s["net_r_2x"]), 6),
                "net_r_zero_pos_swap": round(float(s["net_r_zero_pos_swap"]), 6),
                "fade_net_r_1x": round(float(s["fade_net_r_1x"]), 6),
                "cost_breakeven_mult": round(float(s["cost_breakeven_mult"]), 4),
                "sharpe_clb": round(float(s["sharpe_clb"]), 4),
                "dsr_council": round(dsr_council, 4),
                "dsr_empirical": s["dsr_empirical"],
                "max_dd_r_clb": round(float(s["max_dd_r_clb"]), 4),
                "worst_1d_r_clb": round(float(s["worst_1d_r_clb"]), 4),
                "prop_max_dd_pct_at_risk": s["prop_max_dd_pct_at_risk"],
                "prop_worst_1d_pct_at_risk": s["prop_worst_1d_pct_at_risk"],
                "peak_margin_util_frac": s["peak_margin_util_frac"],
                "margin_breached": s["margin_breached"],
                "sign_flip": s["sign_flip"],
                "p_sign_flip_50k": s["p_sign_flip_50k"],
                "analytical_p": s["analytical_p"],
                "bh_q_primary": bh_q_prim,
                "bh_q_exploratory": bh_q_expl,
                "robustness_gate": rb_report,
                "timing_permutation": timing_res,
                "research_council": council_verdict,
                "crisis_stress_2018_2024": crisis_res,
            }
            audit_rec["classification"] = classify_candidate_tier(audit_rec)
            final_candidates.append(audit_rec)
    finally:
        ledger.close()

    # 8. Aggregate campaign & per-family funnel summaries
    tier_counts = Counter(c["classification"]["tier"] for c in final_candidates)
    t1_tags = Counter(
        c["classification"]["tier1_resolution_tag"]
        for c in final_candidates
        if c["classification"]["tier"] == TIER_1_FTMO_READY
    )
    t1_blind = Counter(
        normalize_blindness_tier(c["blindness_tier"])
        for c in final_candidates
        if c["classification"]["tier"] == TIER_1_FTMO_READY
    )
    eval_blind = dict(
        sorted(Counter(normalize_blindness_tier(c["blindness_tier"]) for c in final_candidates).items())
    )

    family_summaries: dict[str, dict[str, Any]] = {}
    for fid in ckpt_bundle["family_ids"]:
        fc = [c for c in final_candidates if c["alpha_family_id"] == fid]
        if not fc:
            continue
        best_c = max(fc, key=lambda x: float(x["sharpe_clb"]))
        family_summaries[fid] = {
            "total_evaluated": len(fc),
            "primary_evaluated": sum(1 for x in fc if x["is_primary"]),
            "tier1_ftmo_ready": sum(1 for x in fc if x["classification"]["tier"] == TIER_1_FTMO_READY),
            "tier2_personal_vault": sum(1 for x in fc if x["classification"]["tier"] == TIER_2_PERSONAL_VAULT),
            "tier3_dead_no_edge": sum(1 for x in fc if x["classification"]["tier"] == TIER_3_DEAD_NO_EDGE),
            "pbo_cscv": fam_pbo_results.get(fid, {}).get("pbo"),
            "n_eff": n_eff_by_family.get(fid, {}).get("n_eff"),
            "best_sharpe_clb": round(float(best_c["sharpe_clb"]), 3),
            "best_strategy_id": best_c["strategy_id"],
        }

    elapsed_sec = round(time.perf_counter() - t0, 3)
    full_results: dict[str, Any] = {
        "schema_version": "naqex-offensive3-blind-clb-full-v1",
        "generated_utc": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "campaign_run_id": eff_campaign_run_id,
        "git_sha": git_sha,
        "data_sha": data_sha,
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "elapsed_sec": elapsed_sec,
        "cluster_a_years": list(CLUSTER_A_YEARS),
        "cluster_b_years": list(CLUSTER_B_YEARS),
        "statistical_config": {
            "sign_flip_draws": int(sign_flip_draws),
            "timing_perm_draws": int(timing_perm_draws),
            "mc_draws": int(mc_draws),
            "pbo_n_slices": int(eff_pbo_slices),
            "risk_frac": float(risk_frac),
            "g08_max_bh_q": 0.10,
            "g08_min_dsr": 0.50,
            "g08_min_cluster_b_sharpe": 0.40,
            "g08_min_cost_breakeven_mult": 2.0,
            "g08_max_corr_vs_port7e": 0.15,
            "g08_max_tail_corr_vs_port7e": 0.35,
            "g08_max_pbo": 0.50,
            "conditional_retest_rejected": True,
        },
        "duckdb_ledger_summary": {
            "duckdb_path": str(duckdb_path),
            "primary_family_id": CAMPAIGN_PRIMARY_FAMILY_ID,
            "primary_cumulative_m": m_primary_ledger,
            "primary_campaign_count": ckpt_bundle["primary_count"],
            "primary_bh_fdr_pass_count": sum(
                1 for c in final_candidates if c["bh_q_primary"] is not None and float(c["bh_q_primary"]) <= 0.10
            ),
            "exploratory_family_id": CAMPAIGN_EXPLORATORY_FAMILY_ID,
            "exploratory_cumulative_m": m_exploratory_ledger,
            "exploratory_campaign_count": ckpt_bundle["exploratory_total_count"],
            "exploratory_bh_fdr_pass_count": sum(
                1
                for c in final_candidates
                if c["bh_q_exploratory"] is not None and float(c["bh_q_exploratory"]) <= 0.10
            ),
            "integrity_verified": bool(integrity_info["verified"]),
            "total_ledger_experiments": int(integrity_info["experiments_count"]),
        },
        "effective_trials_n_eff": {
            "primary_m200": n_eff_primary,
            "exploratory_m1200": n_eff_exploratory,
            "by_family": n_eff_by_family,
        },
        "campaign_pbo": {
            "primary_m200": camp_pbo_prim,
            "exploratory_m1200": camp_pbo_expl,
            "by_family": fam_pbo_results,
        },
        "evaluated_by_blindness_tier": eval_blind,
        "funnel_counts": {
            "total_evaluated": len(final_candidates),
            "primary_evaluated": ckpt_bundle["primary_count"],
            "exploratory_only_evaluated": ckpt_bundle["exploratory_total_count"] - ckpt_bundle["primary_count"],
            "evaluated_by_blindness_tier": eval_blind,
            "tier1_ftmo_ready": int(tier_counts.get(TIER_1_FTMO_READY, 0)),
            "tier1_m1_native_verified": int(t1_tags.get(TAG_M1_NATIVE_VERIFIED, 0)),
            "tier1_provisional_awaiting_m1": int(t1_tags.get(TAG_PROVISIONAL_AWAITING_M1, 0)),
            "tier1_by_blindness_tier": dict(t1_blind),
            "tier2_personal_vault": int(tier_counts.get(TIER_2_PERSONAL_VAULT, 0)),
            "tier3_dead_no_edge": int(tier_counts.get(TIER_3_DEAD_NO_EDGE, 0)),
            "conditional_retest_rejected_count": sum(
                1 for c in final_candidates if c["classification"]["council_conditional_rejected"]
            ),
            "g7_pbo_executed_count": sum(
                1 for c in final_candidates if "G7_pbo_cscv" in (c["research_council"].get("gates") or {})
            ),
        },
        "family_summaries": family_summaries,
        "candidates": final_candidates,
    }

    output_receipts: dict[str, Any] = {}
    if full_results_path is not None:
        full_p = Path(full_results_path)
        full_bytes = _atomic_write_json(full_p, full_results, compact=False)
        output_receipts["full_results"] = {"path": str(full_p), "bytes": full_bytes}

    if tracked_funnel_path is not None:
        output_receipts["tracked_funnel"] = write_compact_funnel_json(
            full_results,
            tracked_funnel_path,
            max_bytes=MAX_TRACKED_FUNNEL_BYTES,
        )

    full_results["output_receipts"] = output_receipts
    return full_results


# ---------------------------------------------------------------------------
# Fail-Closed CLI (Requires Explicit `--execute-blind-cluster-b` Authorization)
# ---------------------------------------------------------------------------


def _cli_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offensive #3 Stage 3 Blind Cluster B Validation, Dual-Ledger BH-FDR/PBO & 3-Tier Funnel."
    )
    parser.add_argument(
        "--execute-blind-cluster-b",
        action="store_true",
        help="Explicit authorization flag to run ONE SINGLE BLIND PASS on Cluster B (2021-2024).",
    )
    parser.add_argument("--candidates-dir", type=Path, default=DEFAULT_CANDIDATES_DIR)
    parser.add_argument("--duckdb-path", type=Path, default=DEFAULT_DUCKDB_PATH)
    parser.add_argument("--registry-path", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--full-out", type=Path, default=DEFAULT_FULL_RESULTS_PATH)
    parser.add_argument("--funnel-out", type=Path, default=DEFAULT_TRACKED_FUNNEL_PATH)
    parser.add_argument("--sign-flip-draws", type=int, default=SIGN_FLIP_DRAWS)
    parser.add_argument("--timing-draws", type=int, default=TIMING_PERM_DRAWS)
    parser.add_argument("--mc-draws", type=int, default=MC_DRAWS_DEFAULT)
    parser.add_argument("--campaign-run-id", type=str, default=None)
    args = parser.parse_args(argv)

    if not args.execute_blind_cluster_b:
        print(
            json.dumps(
                {
                    "status": "ARMED_WAITING_FOR_COORDINATOR_GO",
                    "order_send_capable": ORDER_SEND_CAPABLE,
                    "holdout_rows_analysed": 0,
                    "message": "Pass --execute-blind-cluster-b ONLY after @coordinator posts GO BLIND CLUSTER B.",
                },
                indent=2,
            )
        )
        return 0

    res = run_stage3_blind_clb(
        candidates_dir=args.candidates_dir,
        duckdb_path=args.duckdb_path,
        registry_path=args.registry_path,
        full_results_path=args.full_out,
        tracked_funnel_path=args.funnel_out,
        campaign_run_id=args.campaign_run_id,
        sign_flip_draws=args.sign_flip_draws,
        timing_perm_draws=args.timing_draws,
        mc_draws=args.mc_draws,
    )
    print(
        json.dumps(
            {
                "campaign_run_id": res["campaign_run_id"],
                "elapsed_sec": res["elapsed_sec"],
                "funnel_counts": res["funnel_counts"],
                "duckdb_ledger_summary": res["duckdb_ledger_summary"],
                "effective_trials_n_eff": {
                    "primary_m200": res["effective_trials_n_eff"]["primary_m200"],
                    "exploratory_m1200": res["effective_trials_n_eff"]["exploratory_m1200"],
                },
                "output_receipts": res["output_receipts"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


__all__ = [
    "CAMPAIGN_EXPLORATORY_FAMILY_ID",
    "CAMPAIGN_PRIMARY_FAMILY_ID",
    "CANONICAL_BLINDNESS_TIERS",
    "CANONICAL_FAMILY_MODULES",
    "DEFAULT_CANDIDATES_DIR",
    "DEFAULT_FULL_RESULTS_PATH",
    "DEFAULT_TRACKED_FUNNEL_PATH",
    "MAX_EXPLORATORY_CANDIDATES",
    "MAX_PRIMARY_CANDIDATES",
    "MAX_TRACKED_FUNNEL_BYTES",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "SIGN_FLIP_DRAWS",
    "TAG_M1_NATIVE_VERIFIED",
    "TAG_PROVISIONAL_AWAITING_M1",
    "TIER_1_FTMO_READY",
    "TIER_2_PERSONAL_VAULT",
    "TIER_3_DEAD_NO_EDGE",
    "TIER_MIXED_12OLD_NEW7",
    "TIER_MIXED_12OLD_NEW9",
    "TIER_MIXED_ALL_3",
    "TIER_MIXED_NEW9_NEW7",
    "TIMING_PERM_DRAWS",
    "build_compact_funnel_payload",
    "build_g08_kill_criteria",
    "classify_candidate_tier",
    "compute_effective_independent_trials",
    "compute_sign_flip_p_50k",
    "compute_student_t_and_newey_west_p",
    "discover_family_modules",
    "load_all_family_checkpoints",
    "load_port7e_incumbent_clb_daily",
    "normalize_blindness_tier",
    "resolve_module_for_family",
    "run_stage3_blind_clb",
    "student_t_one_sided_p",
    "write_compact_funnel_json",
]


if __name__ == "__main__":
    raise SystemExit(_cli_main())
