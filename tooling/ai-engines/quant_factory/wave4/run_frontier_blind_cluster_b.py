"""Wave 2A Single, One-Shot Blind Cluster B Evaluation for 3 Frozen Frontier Non-CFD Sleeves (`W4-G09`).

Executes the pre-registered, zero-retuning, one-shot blind Cluster B evaluation (`<= 2024-12-31`,
`holdout_rows_analysed == 0`) on the EXACT 3 Cluster A winners frozen by `w4-m2b-frontier` in
`.runtime/offensive4/frontier/frontier_cluster_a_frozen.json`:
  1. `FRONTIER_01_SJM_NCO_REGIME_RISK_PARITY` -> `F01_T8_HRP_LAM100_W_DB10`
  2. `FRONTIER_02_VRP_VIX_TERM_VOL_MANAGED_MULTIFACTOR` -> `F02_T3_INVVAR_TIGHT_GLD15`
  3. `FRONTIER_03_CRYPTO_PERP_FUNDING_CARRY_XSEC_MOM` -> `F03_T6_SLOW_W14_BUF25`

Hard scientific integrity & fail-closed invariants (ZERO bare `assert`s; active under `python -O`):
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `SPEND_VND = 0`.
  - Holdout `2025+` SEALED (`HOLDOUT_CUTOFF_DATE = "2024-12-31"`, `holdout_rows_analysed == 0`).
  - Verifies `frontier_cluster_a_frozen.json` `manifest_sha256`, every sleeve's `params_sha256` &
    `candidate_sha256`, and parity with `tooling/automation/configs/frontier_alpha_candidates.json`
    BEFORE calling `evaluate_sleeve(..., split="cluster_b_blind", cutoff_utc="2024-12-31")` ONCE.
  - Zero parameter re-tuning, zero lowering standards, zero rescuing failed sleeves:
    failing ANY pre-registered kill rule marks the sleeve `KILLED_ON_BLIND_CLUSTER_B`.
  - Logs the 3 blind evaluations into `.runtime/offensive4/frontier/wave4_frontier_m36.duckdb`
    (`24 + 3 = 27 <= 36` total trials; `DUPLICATE_TRIAL_ID` blocks accidental re-runs).
  - Applies canonical `quant_core.metrics` statistical gates (`compute_pbo_cscv`,
    `deflated_sharpe_ratio_empirical`, `combinatorial_purged_cv`, `hansen_spa_test`) and
    `benjamini_hochberg` BH-FDR across ALL `m_total = 27` trials.
  - Top-level imports use stdlib + NumPy + lightweight `quant_core`/`frontier_sleeves` only
    (lazy SciPy/Arrow/DuckDB/Numba).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[2]
REPO_ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quant_core.holdout_guard import (  # noqa: E402
    HOLDOUT_CUTOFF_DAY,
    HoldoutLockError,
    enforce_holdout_zero_rows,
    enforce_pre_holdout_dates,
)
from quant_core.io_utils import (  # noqa: E402
    atomic_write_json,
    sha256_file,
    sha256_json_canonical,
)
from quant_core.metrics import (  # noqa: E402
    combinatorial_purged_cv,
    compute_pbo_cscv,
    deflated_sharpe_ratio_empirical,
    hansen_spa_test,
)

from quant_factory.eval_pipeline import benjamini_hochberg  # noqa: E402
from quant_factory.wave4 import frontier_sleeves as fs  # noqa: E402

# ---------------------------------------------------------------------------
# Hard Safety Constants & Canonical Paths
# ---------------------------------------------------------------------------

BLIND_VERDICT_SCHEMA_VERSION: str = "naqex-wave4-frontier-cluster-b-blind-verdict-v1"
RECEIPT_SCHEMA_VERSION: str = "naqex-wave4-worker-receipt-v1"

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
SPEND_VND: int = 0

HOLDOUT_CUTOFF_DATE: str = fs.HOLDOUT_CUTOFF_DATE  # "2024-12-31"
HOLDOUT_START_DATE: str = HOLDOUT_CUTOFF_DAY  # "2025-01-01"

VERDICT_PASS: str = "PASS_BLIND_CLUSTER_B"
VERDICT_KILLED: str = "KILLED_ON_BLIND_CLUSTER_B"

S3B_S4_2022_INCUMBENT_DD_LIMIT_PCT: float = 13.59
F02_2022_DD_LIMIT_PCT: float = 10.0
S3B_CLUSTER_B_INCUMBENT_SHARPE_FALLBACK: float = 1.063
S3B_CLUSTER_B_INCUMBENT_CALMAR_FALLBACK: float = 0.975

DEFAULT_VERDICT_JSON_PATH: Path = fs.FRONTIER_OUT_DIR / "frontier_cluster_b_blind_verdict.json"
DEFAULT_BLIND_RECEIPT_PATH: Path = REPO_ROOT / ".runtime" / "offensive4" / "audits" / "w4_m2b_blind_receipt.json"
DEFAULT_BLIND_DROPBOX_PATH: Path = REPO_ROOT / ".tmp" / "swarm_dropbox" / "w4-m2b-blind.json"

_STD_NORM = NormalDist(0.0, 1.0)
_EPS: float = 1e-12
_HANSEN_SPA_SEED: int = 20261127
_HANSEN_SPA_BOOTS: int = 2000
_HANSEN_SPA_BLOCK_LEN: int = 5


# ---------------------------------------------------------------------------
# Strict Input & Date Validators (ZERO bare `assert`s; `-O` safe)
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_non_empty_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string, got {value!r}")
    return value.strip()


def _require_finite_float(
    value: Any,
    name: str,
    *,
    lo: float | None = None,
    hi: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        raise ValueError(f"{name} must be a finite numeric value (not bool), got {value!r}")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite, got {value!r}")
    if lo is not None and out < lo:
        raise ValueError(f"{name}={out} must be >= {lo}")
    if hi is not None and out > hi:
        raise ValueError(f"{name}={out} must be <= {hi}")
    return out


def _require_int(
    value: Any,
    name: str,
    *,
    lo: int | None = None,
    hi: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer (not bool), got {value!r}")
    out = int(value)
    if lo is not None and out < lo:
        raise ValueError(f"{name}={out} must be >= {lo}")
    if hi is not None and out > hi:
        raise ValueError(f"{name}={out} must be <= {hi}")
    return out


def _validate_cutoff_strict(cutoff_utc: Any, *, context: str) -> str:
    txt = _require_non_empty_str(cutoff_utc, f"{context}.cutoff_utc")
    if len(txt) != 10:
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: invalid cutoff_utc={cutoff_utc!r}")
    try:
        parsed = date.fromisoformat(txt).isoformat()
    except ValueError as exc:
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: malformed cutoff_utc={cutoff_utc!r}") from exc
    enforce_pre_holdout_dates(parsed, context=f"{context}.cutoff_utc", cutoff_day=HOLDOUT_START_DATE)
    if parsed > HOLDOUT_CUTOFF_DATE:
        raise HoldoutLockError(
            f"HOLDOUT_LOCK_VIOLATION [{context}]: cutoff_utc={parsed!r} exceeds sealed {HOLDOUT_CUTOFF_DATE!r}"
        )
    return parsed


def _select_even_pbo_slices(n_obs: int, preferred: int = 16) -> int:
    if n_obs < 8:
        raise ValueError(f"Insufficient observations ({n_obs}) for CSCV PBO (need >= 8)")
    target = int(preferred)
    if target < 4 or target % 2 != 0:
        target = 16
    while target >= 4:
        if n_obs >= target and (target // 2) * (n_obs // target) >= 2:
            return target
        target -= 2
    return 4


# ---------------------------------------------------------------------------
# 1. Fail-Closed Frozen Artifact & Gate Verification (Pre-Blind Guard)
# ---------------------------------------------------------------------------


def verify_frozen_bundle_for_blind_eval(
    frozen_json_path: str | Path = fs.DEFAULT_FROZEN_JSON_PATH,
    *,
    config_path: str | Path = fs.CONFIG_PATH,
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
) -> dict[str, Any]:
    """Fail-closed verification of frozen Cluster A artifact, all 3 `candidate_sha256`s, and canonical gates."""
    cut = _validate_cutoff_strict(cutoff_utc, context="verify_frozen_bundle_for_blind_eval")
    cfg = fs.load_frontier_config(config_path)

    # First run upstream canonical verifier from frontier_sleeves
    upstream_ver = fs.verify_frozen_artifact(frozen_json_path)
    p = Path(frozen_json_path)
    doc = json.loads(p.read_text(encoding="utf-8"))

    if doc.get("family_budget_id") != fs.WAVE4_FRONTIER_FAMILY_ID:
        raise ValueError(
            f"FAMILY_BUDGET_ID_MISMATCH: {doc.get('family_budget_id')!r} != {fs.WAVE4_FRONTIER_FAMILY_ID!r}"
        )
    if doc.get("dev_cutoff_utc") != HOLDOUT_CUTOFF_DATE:
        raise HoldoutLockError(f"FROZEN_CUTOFF_MISMATCH: {doc.get('dev_cutoff_utc')!r} != {HOLDOUT_CUTOFF_DATE!r}")

    fc = doc.get("frozen_candidates", {})
    all_a = doc.get("all_cluster_a_trials", {})
    verified_candidates: dict[str, dict[str, Any]] = {}

    for sid in fs.FRONTIER_SLEEVE_IDS:
        if sid not in fc:
            raise ValueError(f"MISSING_FROZEN_CANDIDATE: {sid}")
        cand = fc[sid]
        spec = fs.get_sleeve_spec(sid, config=cfg)

        enforce_holdout_zero_rows(cand.get("holdout_rows_analysed", -1), context=f"frozen.{sid}")
        if cand.get("cluster_b_touched") is not False:
            raise ValueError(f"CLUSTER_B_LEAKAGE_VIOLATION: frozen {sid} already touched Cluster B")

        params = cand.get("params")
        if not isinstance(params, Mapping):
            raise ValueError(f"MALFORMED_PARAMS: {sid} params must be a mapping")
        params_clean = dict(sorted((str(k), v) for k, v in params.items()))
        recomputed_params_sha = sha256_json_canonical(params_clean)
        if cand.get("params_sha256") != recomputed_params_sha:
            raise ValueError(
                f"PARAMS_SHA256_MISMATCH for {sid}: stored={cand.get('params_sha256')} != {recomputed_params_sha}"
            )

        freeze_payload = {
            "sleeve_id": cand["sleeve_id"],
            "frozen_trial_id": cand["frozen_trial_id"],
            "params": params_clean,
            "params_sha256": recomputed_params_sha,
            "dev_cluster_a": cand["dev_cluster_a"],
            "dev_cluster_b_blind_pending": cand["dev_cluster_b_blind_pending"],
            "dev_cutoff_utc": cand["dev_cutoff_utc"],
        }
        recomputed_cand_sha = sha256_json_canonical(freeze_payload)
        if cand.get("candidate_sha256") != recomputed_cand_sha:
            raise ValueError(
                f"CANDIDATE_SHA256_MISMATCH for {sid}: stored={cand.get('candidate_sha256')} != {recomputed_cand_sha}"
            )

        # Cross-check frozen trial against Cluster A trial log if present in frozen JSON
        if isinstance(all_a, Mapping) and sid in all_a and isinstance(all_a[sid], list):
            matching = [row for row in all_a[sid] if row.get("trial_id") == cand["frozen_trial_id"]]
            if not matching:
                raise ValueError(
                    f"FROZEN_TRIAL_NOT_IN_CLUSTER_A_LOG: {cand['frozen_trial_id']!r} missing from {sid}"
                )
            if matching[0].get("params_sha256") != recomputed_params_sha:
                raise ValueError(f"FROZEN_TRIAL_PARAMS_DRIFT: {cand['frozen_trial_id']!r} params_sha256 mismatch")

        # Verify pre-registered falsification gate was not weakened relative to frontier_alpha_candidates.json
        frozen_gate = cand.get("pre_registered_falsification_gate")
        canonical_gate = spec["gate"]
        if isinstance(frozen_gate, Mapping):
            for key, canon_val in canonical_gate.items():
                if key == "immediate_kill_rules":
                    continue
                if frozen_gate.get(key) != canon_val:
                    raise ValueError(
                        f"GATE_TAMPER_MISMATCH [{sid}.{key}]: "
                        f"frozen={frozen_gate.get(key)!r} != canonical={canon_val!r}"
                    )

        verified_candidates[sid] = {
            "sleeve_id": sid,
            "frozen_trial_id": str(cand["frozen_trial_id"]),
            "blind_trial_id": f"{cand['frozen_trial_id']}__BLIND_B",
            "params": params_clean,
            "params_sha256": recomputed_params_sha,
            "candidate_sha256": recomputed_cand_sha,
            "dev_cluster_a": str(cand["dev_cluster_a"]),
            "dev_cluster_b_blind": str(canonical_gate["dev_cluster_b_blind"]),
            "cluster_a_metrics": dict(cand.get("cluster_a_metrics", {})),
            "canonical_gate": dict(canonical_gate),
        }

    return {
        "verified": True,
        "cutoff_utc": cut,
        "frozen_json_path": str(p),
        "frozen_file_sha256": upstream_ver["file_sha256"],
        "frozen_manifest_sha256": upstream_ver["manifest_sha256"],
        "cluster_a_trials_total": int(doc["cluster_a_trials_total"]),
        "budget_cap": int(doc["budget_cap"]),
        "config": cfg,
        "frozen_doc": doc,
        "candidates": verified_candidates,
    }


# ---------------------------------------------------------------------------
# 2. Pure Statistical Helpers (Newey-West, 2022 DD, Baselines, CPCV, Starved Months)
# ---------------------------------------------------------------------------


def compute_newey_west_one_sided_p(
    returns: Sequence[float] | np.ndarray,
    *,
    max_lag: int | None = None,
) -> dict[str, float | int]:
    """Compute IID and Newey-West Bartlett HAC one-sided p-values (`H0: mean <= 0`)."""
    r = np.asarray(returns, dtype=np.float64)
    if r.ndim != 1 or not bool(np.all(np.isfinite(r))):
        raise ValueError("returns must be a finite 1D array")
    n = int(r.size)
    if n < 5:
        return {
            "n_obs": n,
            "t_iid": 0.0,
            "p_iid": 1.0,
            "t_newey_west": 0.0,
            "p_newey_west": 1.0,
            "p_conservative": 1.0,
            "nw_lag": 0,
        }

    mu = float(np.mean(r))
    centered = r - mu
    sd = float(np.std(r, ddof=1))
    if sd <= 1e-15:
        t_iid = 0.0
        p_iid = 1.0 if mu <= 0.0 else 0.0
    else:
        t_iid = mu / (sd / math.sqrt(float(n)))
        p_iid = float(0.5 * math.erfc(t_iid / math.sqrt(2.0)))

    lag = int(max_lag) if max_lag is not None else max(1, int(math.floor(4.0 * ((float(n) / 100.0) ** (2.0 / 9.0)))))
    lag = min(max(1, lag), max(1, n - 2))
    gamma0 = float(np.dot(centered, centered)) / float(n)
    lrv = gamma0
    for ell in range(1, lag + 1):
        weight = 1.0 - float(ell) / float(lag + 1)
        gamma_l = float(np.dot(centered[ell:], centered[:-ell])) / float(n)
        lrv += 2.0 * weight * gamma_l

    lrv_adj = max(lrv * (float(n) / float(max(1, n - 1))), 0.0)
    if lrv_adj <= 1e-24:
        t_nw = t_iid
        p_nw = p_iid
    else:
        se_nw = math.sqrt(lrv_adj / float(n))
        t_nw = mu / se_nw
        p_nw = float(0.5 * math.erfc(t_nw / math.sqrt(2.0)))

    p_iid_c = float(np.clip(p_iid, 0.0, 1.0))
    p_nw_c = float(np.clip(p_nw, 0.0, 1.0))
    p_cons = max(p_iid_c, p_nw_c)
    return {
        "n_obs": n,
        "t_iid": round(float(t_iid), 4),
        "p_iid": round(p_iid_c, 6),
        "t_newey_west": round(float(t_nw), 4),
        "p_newey_west": round(p_nw_c, 6),
        "p_conservative": round(p_cons, 6),
        "nw_lag": int(lag),
    }


def compute_calendar_year_drawdown(
    daily_returns_map: Mapping[str, float],
    *,
    year: int = 2022,
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
) -> dict[str, Any]:
    """Compute exact peak-to-trough max drawdown strictly inside calendar year `year` (`<= cutoff_utc`)."""
    cut = _validate_cutoff_strict(cutoff_utc, context="compute_calendar_year_drawdown")
    if daily_returns_map:
        all_days = sorted(str(k) for k in daily_returns_map)
        enforce_pre_holdout_dates(all_days, context="calendar_year_dd.dates", cutoff_day=HOLDOUT_START_DATE)
        if all_days[-1] > cut:
            raise HoldoutLockError(f"CUTOFF_BREACH [calendar_year_dd]: {all_days[-1]!r} > {cut!r}")

    prefix = f"{int(year):04d}-"
    yr_days = sorted(str(d) for d in daily_returns_map if str(d).startswith(prefix))
    if not yr_days:
        return {
            "year": int(year),
            "applicable": False,
            "n_days": 0,
            "max_dd_pct": None,
            "total_return_pct": None,
        }

    r = np.array([_require_finite_float(daily_returns_map[d], f"ret[{d}]") for d in yr_days], dtype=np.float64)
    eq = np.cumprod(1.0 + r)
    peaks = np.maximum.accumulate(np.r_[1.0, eq])
    dd = (peaks[1:] - eq) / np.maximum(peaks[1:], _EPS)
    return {
        "year": int(year),
        "applicable": True,
        "n_days": int(len(r)),
        "start_date": yr_days[0],
        "end_date": yr_days[-1],
        "max_dd_pct": round(float(np.max(dd)) * 100.0, 4),
        "total_return_pct": round(float(eq[-1] - 1.0) * 100.0, 4),
    }


def compute_cpcv_oos_summary(
    returns: Sequence[float] | np.ndarray,
    *,
    ann_days: float = 252.0,
    n_groups: int = 6,
    k_test_groups: int = 2,
    purge_bars: int = 5,
    embargo_bars: int = 5,
) -> dict[str, Any]:
    """Run Lopez de Prado CPCV with strict purging & embargoing on blind returns."""
    r = np.asarray(returns, dtype=np.float64)
    if r.ndim != 1 or not bool(np.all(np.isfinite(r))):
        raise ValueError("returns must be a finite 1D array")
    n_obs = int(r.size)
    if n_obs < n_groups * 4:
        raise ValueError(f"Insufficient observations ({n_obs}) for CPCV with n_groups={n_groups}")

    splits = combinatorial_purged_cv(
        n_obs,
        n_groups=n_groups,
        k_test_groups=k_test_groups,
        purge_bars=purge_bars,
        embargo_bars=embargo_bars,
    )
    oos_sharpes: list[float] = []
    total_purged = 0
    total_embargoed = 0
    for sp in splits:
        if set(sp.train_indices) & set(sp.test_indices):
            raise ValueError(f"CPCV_OVERLAP_VIOLATION on split {sp.split_id}")
        total_purged += len(sp.purged_indices)
        total_embargoed += len(sp.embargoed_indices)
        test_r = r[list(sp.test_indices)]
        sd = float(np.std(test_r, ddof=1)) if test_r.size >= 2 else 0.0
        sr = (float(np.mean(test_r)) / sd * math.sqrt(float(ann_days))) if sd > _EPS else 0.0
        oos_sharpes.append(sr)

    arr = np.asarray(oos_sharpes, dtype=np.float64)
    return {
        "cpcv_purge_embargo_verified": bool(len(splits) > 0 and total_purged > 0 and total_embargoed > 0),
        "n_groups": int(n_groups),
        "k_test_groups": int(k_test_groups),
        "n_paths": int(len(splits)),
        "purge_bars": int(purge_bars),
        "embargo_bars": int(embargo_bars),
        "total_purged_bars": int(total_purged),
        "total_embargoed_bars": int(total_embargoed),
        "median_oos_sharpe": round(float(np.median(arr)), 4),
        "mean_oos_sharpe": round(float(np.mean(arr)), 4),
        "min_oos_sharpe": round(float(np.min(arr)), 4),
        "max_oos_sharpe": round(float(np.max(arr)), 4),
        "pct_paths_positive_sharpe": round(100.0 * float(np.mean(arr > 0.0)), 2),
    }


def compute_spy_vol_target_baseline(
    panel: Mapping[str, Any],
    *,
    target_vol: float,
    vol_lookback: int,
    safe_harbor: str = "bil_shy",
    cost_bps_oneway: float = 5.0,
    eval_start: str,
    eval_end: str,
) -> dict[str, Any]:
    """Build strictly causal plain SPY volatility-targeting baseline (pre-registered F02 SPA benchmark)."""
    dates = list(panel["dates"])
    enforce_pre_holdout_dates(dates, context="spy_vol_target_baseline.dates", cutoff_day=HOLDOUT_START_DATE)
    syms = [fs._canonical_symbol(s) for s in panel["symbols"]]
    px = np.asarray(panel["adjclose"], dtype=np.float64)
    n_t, n_k = px.shape
    sym_idx = {s: i for i, s in enumerate(syms)}
    if "SPY" not in sym_idx:
        raise ValueError("SPY missing from ETF panel for plain SPY volatility-targeting baseline")
    spy_j = sym_idx["SPY"]
    bil_j = sym_idx.get("BIL")
    shy_j = sym_idx.get("SHY")

    rets = fs._compute_etf_daily_returns(px)
    target_w = np.zeros((n_t, n_k), dtype=np.float64)
    min_warmup = max(int(vol_lookback), 21) + 1
    for t in range(min_warmup, n_t):
        if not (math.isfinite(px[t, spy_j]) and px[t, spy_j] > 0.0):
            continue
        rw = rets[t - int(vol_lookback) + 1 : t + 1, spy_j]
        valid = rw[np.isfinite(rw)]
        if len(valid) < max(8, int(0.85 * int(vol_lookback))):
            continue
        sd = float(np.std(valid, ddof=1)) * math.sqrt(252.0)
        spy_w = float(np.clip(float(target_vol) / max(sd, 0.04), 0.0, 1.0))
        target_w[t, spy_j] = spy_w
        rem = max(0.0, 1.0 - spy_w)
        if safe_harbor == "bil_shy" and rem > 1e-6:
            if bil_j is not None and math.isfinite(px[t, bil_j]) and px[t, bil_j] > 0.0:
                target_w[t, bil_j] = rem
            elif shy_j is not None and math.isfinite(px[t, shy_j]) and px[t, shy_j] > 0.0:
                target_w[t, shy_j] = rem

    sim = fs._simulate_etf_causal(px, target_w, syms, cost_bps_oneway=float(cost_bps_oneway))
    eval_mask = np.array([(d >= eval_start) and (d <= eval_end) for d in dates], dtype=bool)
    r_eval = sim["net_returns"][eval_mask]
    eval_dates = [d for d, flag in zip(dates, eval_mask, strict=True) if flag]
    metrics = fs.compute_series_metrics(r_eval, ann_days=252.0)
    return {
        "benchmark_name": "PLAIN_SPY_VOL_TARGET_BASELINE",
        "dates": eval_dates,
        "daily_returns": r_eval,
        "metrics": metrics,
    }


def compute_bil_cash_baseline(
    panel: Mapping[str, Any],
    *,
    eval_start: str,
    eval_end: str,
) -> dict[str, Any]:
    """Compute strictly causal BIL T-bill benchmark daily returns on `[eval_start, eval_end]`."""
    dates = list(panel["dates"])
    enforce_pre_holdout_dates(dates, context="bil_baseline.dates", cutoff_day=HOLDOUT_START_DATE)
    syms = [fs._canonical_symbol(s) for s in panel["symbols"]]
    px = np.asarray(panel["adjclose"], dtype=np.float64)
    n_t, n_k = px.shape
    sym_idx = {s: i for i, s in enumerate(syms)}
    bil_j = sym_idx.get("BIL")
    target_w = np.zeros((n_t, n_k), dtype=np.float64)
    if bil_j is not None:
        ok = np.isfinite(px[:, bil_j]) & (px[:, bil_j] > 0.0)
        target_w[ok, bil_j] = 1.0
    sim = fs._simulate_etf_causal(px, target_w, syms, cost_bps_oneway=0.0)
    eval_mask = np.array([(d >= eval_start) and (d <= eval_end) for d in dates], dtype=bool)
    r_eval = sim["net_returns"][eval_mask]
    eval_dates = [d for d, flag in zip(dates, eval_mask, strict=True) if flag]
    return {
        "benchmark_name": "BIL_CASH_BASELINE",
        "dates": eval_dates,
        "daily_returns": r_eval,
        "metrics": fs.compute_series_metrics(r_eval, ann_days=252.0),
    }


def compute_sleeve_cluster_a_pbo(
    sleeve_id: str,
    *,
    panel_a: Mapping[str, Any],
    grid: Sequence[tuple[str, dict[str, Any]]],
    config: Mapping[str, Any],
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
    n_slices: int = 16,
) -> dict[str, Any]:
    """Compute exact Bailey et al. CSCV PBO over the `M = 8` Cluster A trials strictly `<= cluster_a_end`.

    Never loads or touches any Cluster B date (`cluster_b_touched == False` for all 8 grid replays).
    """
    cut = _validate_cutoff_strict(cutoff_utc, context=f"cluster_a_pbo.{sleeve_id}")
    if len(grid) < 2:
        raise ValueError(f"CSCV PBO requires >= 2 grid trials for {sleeve_id}, got {len(grid)}")

    fs.enforce_split_bounds(
        panel_a["dates"],
        sleeve_id=sleeve_id,
        split="cluster_a",
        cutoff_utc=cut,
        config=config,
    )

    series_cols: list[np.ndarray] = []
    ref_dates: list[str] | None = None
    trial_ids: list[str] = []
    for trial_id, params in grid:
        res = fs.evaluate_sleeve(
            sleeve_id,
            params,
            split="cluster_a",
            cutoff_utc=cut,
            panel=panel_a,
            config=config,
        )
        if res["cluster_b_touched"] is not False:
            raise ValueError(f"CLUSTER_B_LEAKAGE_VIOLATION in Cluster A PBO replay for {trial_id}")
        enforce_holdout_zero_rows(res["holdout_rows_analysed"], context=f"pbo.{trial_id}")
        d_keys = sorted(res["daily_returns"].keys())
        if ref_dates is None:
            ref_dates = d_keys
        elif d_keys != ref_dates:
            raise ValueError(f"Date alignment mismatch inside Cluster A PBO grid for {sleeve_id}")
        series_cols.append(np.array([float(res["daily_returns"][d]) for d in ref_dates], dtype=np.float64))
        trial_ids.append(trial_id)

    mat = np.column_stack(series_cols)
    eff_slices = _select_even_pbo_slices(int(mat.shape[0]), preferred=n_slices)
    pbo_res = compute_pbo_cscv(mat, n_slices=eff_slices)
    return {
        "pbo_cscv": round(float(pbo_res.pbo), 4),
        "is_overfit": bool(pbo_res.is_overfit),
        "n_slices": int(pbo_res.n_slices),
        "n_combinations": int(pbo_res.n_combinations),
        "n_trials_in_matrix": int(pbo_res.n_trials),
        "n_obs_cluster_a": int(mat.shape[0]),
        "prob_oos_nonpositive_sr": round(float(pbo_res.prob_oos_nonpositive_sr), 4),
        "cluster_b_touched": False,
        "trial_ids": trial_ids,
    }


# ---------------------------------------------------------------------------
# 3. Pure Pre-Registered Falsification Gate Evaluator (Fail-Closed, `-O` Safe)
# ---------------------------------------------------------------------------


def evaluate_sleeve_falsification_gates(
    sleeve_id: str,
    blind_metrics: Mapping[str, Any],
    gate: Mapping[str, Any],
    *,
    incumbent_s3b_sharpe: float = S3B_CLUSTER_B_INCUMBENT_SHARPE_FALLBACK,
    incumbent_s3b_calmar: float = S3B_CLUSTER_B_INCUMBENT_CALMAR_FALLBACK,
) -> dict[str, Any]:
    """Apply EVERY pre-registered falsification gate honestly; any failure yields `KILLED_ON_BLIND_CLUSTER_B`.

    Zero lowering standards, zero silent defaults, zero bare `assert`s (`python -O` safe).
    """
    sid = _require_non_empty_str(sleeve_id, "sleeve_id")
    if sid not in fs.FRONTIER_SLEEVE_IDS:
        raise ValueError(f"Unsupported sleeve_id={sid!r}")

    # Hard Holdout & safety checks first (raise on Holdout breach!)
    enforce_holdout_zero_rows(blind_metrics.get("holdout_rows_analysed", -1), context=f"gate.{sid}")
    eval_end = _validate_cutoff_strict(blind_metrics.get("eval_end_date"), context=f"gate.{sid}.eval_end")
    max_loaded = _validate_cutoff_strict(blind_metrics.get("max_loaded_date"), context=f"gate.{sid}.max_loaded")
    order_send = _require_int(blind_metrics.get("order_send_count", -1), f"{sid}.order_send_count", lo=0)
    if order_send != 0:
        raise ValueError(f"ORDER_SEND_VIOLATION [{sid}]: order_send_count={order_send} != 0")

    sharpe = _require_finite_float(blind_metrics.get("sharpe"), f"{sid}.sharpe")
    calmar = _require_finite_float(blind_metrics.get("calmar"), f"{sid}.calmar")
    pbo_cscv = _require_finite_float(blind_metrics.get("pbo_cscv"), f"{sid}.pbo_cscv", lo=0.0, hi=1.0)
    dsr_emp = _require_finite_float(blind_metrics.get("dsr_empirical"), f"{sid}.dsr_empirical", lo=0.0, hi=1.0)
    bh_fdr_q = _require_finite_float(blind_metrics.get("bh_fdr_q"), f"{sid}.bh_fdr_q", lo=0.0, hi=1.0)
    spa_p = _require_finite_float(blind_metrics.get("hansen_spa_p"), f"{sid}.hansen_spa_p", lo=0.0, hi=1.0)
    cost_2x_net = _require_finite_float(blind_metrics.get("cost_2x_net_pct"), f"{sid}.cost_2x_net_pct")
    be_mult = _require_finite_float(blind_metrics.get("cost_breakeven_mult"), f"{sid}.cost_breakeven_mult", lo=0.0)
    turnover = _require_finite_float(blind_metrics.get("annual_turnover"), f"{sid}.annual_turnover", lo=0.0)
    pre_list_v = _require_int(blind_metrics.get("pre_listing_weight_violations", 0), f"{sid}.pre_listing_viol", lo=0)
    sig_only_w = _require_finite_float(
        blind_metrics.get("signal_only_max_abs_weight", 0.0),
        f"{sid}.signal_only_max_abs_weight",
        lo=0.0,
    )

    corr_7e_raw = blind_metrics.get("corr_vs_7e")
    corr_7e = None if corr_7e_raw is None else _require_finite_float(corr_7e_raw, f"{sid}.corr_vs_7e", lo=-1.0, hi=1.0)
    tail_7e_raw = blind_metrics.get("tail_corr_vs_7e")
    tail_7e = (
        None
        if tail_7e_raw is None
        else _require_finite_float(tail_7e_raw, f"{sid}.tail_corr_vs_7e", lo=-1.0, hi=1.0)
    )
    corr_s4_raw = blind_metrics.get("corr_vs_s4_etf")
    corr_s4 = (
        None
        if corr_s4_raw is None
        else _require_finite_float(corr_s4_raw, f"{sid}.corr_vs_s4_etf", lo=-1.0, hi=1.0)
    )

    min_sharpe = _require_finite_float(gate["min_cluster_b_sharpe"], "gate.min_cluster_b_sharpe")
    max_pbo = _require_finite_float(gate["max_pbo_cscv"], "gate.max_pbo_cscv", lo=0.0, hi=1.0)
    min_dsr = _require_finite_float(gate["min_dsr_empirical"], "gate.min_dsr_empirical", lo=0.0, hi=1.0)
    max_bh_q = _require_finite_float(gate["max_bh_fdr_q"], "gate.max_bh_fdr_q", lo=0.0, hi=1.0)
    max_spa_p = _require_finite_float(gate["max_hansen_spa_p"], "gate.max_hansen_spa_p", lo=0.0, hi=1.0)
    min_be = _require_finite_float(gate["min_cost_breakeven_mult"], "gate.min_cost_breakeven_mult", lo=0.0)
    max_turn = _require_finite_float(gate["max_annual_turnover"], "gate.max_annual_turnover", lo=0.0)
    max_corr_7e = _require_finite_float(gate["max_abs_corr_vs_7e"], "gate.max_abs_corr_vs_7e", lo=0.0, hi=1.0)
    max_tail_7e = _require_finite_float(
        gate["max_worst5pct_tail_corr_vs_7e"], "gate.max_worst5pct_tail_corr_vs_7e", lo=0.0, hi=1.0
    )

    checks: dict[str, bool] = {}
    details: dict[str, dict[str, Any]] = {}

    def _rec(name: str, passed: bool, observed: Any, threshold: str) -> None:
        checks[name] = bool(passed)
        details[name] = {"passed": bool(passed), "observed": observed, "threshold": threshold}

    _rec(
        "holdout_cutoff_sealed",
        eval_end <= HOLDOUT_CUTOFF_DATE and max_loaded <= HOLDOUT_CUTOFF_DATE,
        {"eval_end_date": eval_end, "max_loaded_date": max_loaded, "holdout_rows_analysed": 0},
        f"<= {HOLDOUT_CUTOFF_DATE} & holdout_rows_analysed == 0",
    )
    _rec("min_cluster_b_sharpe", sharpe >= min_sharpe, sharpe, f">= {min_sharpe}")
    _rec("max_pbo_cscv", pbo_cscv <= max_pbo, pbo_cscv, f"<= {max_pbo}")
    _rec("min_dsr_empirical", dsr_emp >= min_dsr, dsr_emp, f">= {min_dsr}")
    _rec("max_bh_fdr_q", bh_fdr_q <= max_bh_q, bh_fdr_q, f"<= {max_bh_q} (all m_total trials)")
    _rec("max_hansen_spa_p", spa_p <= max_spa_p, spa_p, f"<= {max_spa_p}")

    if bool(gate.get("cost_stress_2x_net_positive_required", True)):
        _rec("cost_stress_2x_net_positive", cost_2x_net > 0.0, cost_2x_net, "> 0.0%")
    _rec("min_cost_breakeven_mult", be_mult >= min_be, be_mult, f">= {min_be}x")
    _rec("max_annual_turnover", turnover <= max_turn, turnover, f"<= {max_turn}x/yr")

    # Kill rule states: "Kill if |r(PORT_7E)| >= 0.15" (strict `<`)
    abs_corr_7e = None if corr_7e is None else round(abs(corr_7e), 4)
    _rec(
        "max_abs_corr_vs_7e",
        corr_7e is not None and abs(corr_7e) < max_corr_7e,
        {"corr_vs_7e": corr_7e, "abs_corr_vs_7e": abs_corr_7e},
        f"< {max_corr_7e}",
    )
    _rec(
        "max_worst5pct_tail_corr_vs_7e",
        tail_7e is not None and tail_7e <= max_tail_7e,
        tail_7e,
        f"<= {max_tail_7e}",
    )
    _rec("zero_pre_listing_violations", pre_list_v == 0, pre_list_v, "== 0")
    _rec("zero_signal_only_weights", sig_only_w == 0.0, sig_only_w, "== 0.0")

    if bool(gate.get("cpcv_purge_embargo_required", True)):
        cpcv_ok = bool(blind_metrics.get("cpcv_purge_embargo_verified", False))
        _rec("cpcv_purge_embargo_required", cpcv_ok, cpcv_ok, "== True")

    # Sleeve-specific pre-registered kill rules
    if sid == fs.FRONTIER_01_ID:
        max_s4 = _require_finite_float(gate["max_corr_vs_existing_s4_etf"], "gate.max_corr_vs_existing_s4_etf")
        _rec(
            "max_corr_vs_existing_s4_etf",
            corr_s4 is not None and abs(corr_s4) <= max_s4,
            corr_s4,
            f"|r| <= {max_s4}",
        )
        dd22_raw = blind_metrics.get("max_dd_2022_pct")
        dd22 = None if dd22_raw is None else _require_finite_float(dd22_raw, f"{sid}.max_dd_2022_pct", lo=0.0)
        dominates = (sharpe > float(incumbent_s3b_sharpe)) and (calmar > float(incumbent_s3b_calmar))
        dd22_ok = dd22 is not None and (dd22 <= S3B_S4_2022_INCUMBENT_DD_LIMIT_PCT or dominates)
        _rec(
            "inflation_2022_dd_check",
            dd22_ok,
            {"max_dd_2022_pct": dd22, "dominates_incumbent_sharpe_calmar": dominates},
            (
                f"<= {S3B_S4_2022_INCUMBENT_DD_LIMIT_PCT}% "
                f"(or Sharpe>{incumbent_s3b_sharpe} & Calmar>{incumbent_s3b_calmar})"
            ),
        )

    elif sid == fs.FRONTIER_02_ID:
        dd22_raw = blind_metrics.get("max_dd_2022_pct")
        dd22 = None if dd22_raw is None else _require_finite_float(dd22_raw, f"{sid}.max_dd_2022_pct", lo=0.0)
        _rec(
            "inflation_2022_dd_check",
            dd22 is not None and dd22 <= F02_2022_DD_LIMIT_PCT,
            dd22,
            f"<= {F02_2022_DD_LIMIT_PCT}%",
        )
        spa_spy_raw = blind_metrics.get("hansen_spa_vs_spy_vt_p")
        spa_spy = (
            None
            if spa_spy_raw is None
            else _require_finite_float(spa_spy_raw, f"{sid}.hansen_spa_vs_spy_vt_p", lo=0.0, hi=1.0)
        )
        _rec(
            "hansen_spa_vs_spy_voltarget",
            spa_spy is not None and spa_spy <= max_spa_p,
            spa_spy,
            f"<= {max_spa_p} vs plain SPY vol-targeting baseline",
        )

    elif sid == fs.FRONTIER_03_ID:
        cross_liq = _require_int(blind_metrics.get("cross_liq_events", -1), f"{sid}.cross_liq_events", lo=0)
        iso_liq = _require_int(blind_metrics.get("isolated_liq_events", -1), f"{sid}.isolated_liq_events", lo=0)
        _rec("zero_cross_margin_liquidations", cross_liq == 0, cross_liq, "== 0")
        _rec("zero_isolated_liquidations", iso_liq == 0, iso_liq, "== 0")

    failed_gates = [name for name, ok in checks.items() if not ok]
    verdict = VERDICT_PASS if not failed_gates else VERDICT_KILLED
    return {
        "sleeve_id": sid,
        "verdict": verdict,
        "all_gates_passed": len(failed_gates) == 0,
        "failed_gates": failed_gates,
        "checks": checks,
        "gate_details": details,
    }


# ---------------------------------------------------------------------------
# 4. Pod-Level Blend Impact & Starved-Month Reduction (Dev Cluster B <= 2024)
# ---------------------------------------------------------------------------


def compute_starved_month_metrics(
    dates: Sequence[str],
    daily_returns: Sequence[float] | np.ndarray,
    *,
    low_return_threshold: float = 0.005,
) -> dict[str, Any]:
    """Compute monthly compounded returns & exact starved-month (`<= 0%` and `< +0.5%`) rates & streaks."""
    r = np.asarray(daily_returns, dtype=np.float64)
    if len(dates) != len(r):
        raise ValueError(f"dates length {len(dates)} != daily_returns length {len(r)}")
    if len(dates) == 0:
        return {
            "n_months": 0,
            "positive_months": 0,
            "starved_months_le_0": 0,
            "starved_month_rate_le_0_pct": 0.0,
            "starved_months_lt_0p5pct": 0,
            "starved_month_rate_lt_0p5_pct": 0.0,
            "max_consec_starved_le_0": 0,
            "max_consec_starved_lt_0p5": 0,
            "monthly_median_pct": 0.0,
            "monthly_worst_pct": 0.0,
            "monthly_best_pct": 0.0,
        }
    enforce_pre_holdout_dates(dates, context="starved_month_metrics.dates", cutoff_day=HOLDOUT_START_DATE)

    by_month: dict[str, float] = {}
    for dk, rv in zip(dates, r, strict=True):
        ym = str(dk)[:7]
        by_month[ym] = (1.0 + by_month.get(ym, 0.0)) * (1.0 + float(rv)) - 1.0

    vals = [by_month[ym] for ym in sorted(by_month)]
    n_m = len(vals)
    s0_cnt = 0
    s05_cnt = 0
    cur0 = 0
    max0 = 0
    cur05 = 0
    max05 = 0
    for mv in vals:
        if mv <= 0.0:
            s0_cnt += 1
            cur0 += 1
            max0 = max(max0, cur0)
        else:
            cur0 = 0
        if mv < float(low_return_threshold):
            s05_cnt += 1
            cur05 += 1
            max05 = max(max05, cur05)
        else:
            cur05 = 0

    arr = np.asarray(vals, dtype=np.float64)
    return {
        "n_months": int(n_m),
        "positive_months": int(n_m - s0_cnt),
        "starved_months_le_0": int(s0_cnt),
        "starved_month_rate_le_0_pct": round(100.0 * s0_cnt / float(n_m), 2),
        "starved_months_lt_0p5pct": int(s05_cnt),
        "starved_month_rate_lt_0p5_pct": round(100.0 * s05_cnt / float(n_m), 2),
        "max_consec_starved_le_0": int(max0),
        "max_consec_starved_lt_0p5": int(max05),
        "monthly_median_pct": round(float(np.median(arr)) * 100.0, 3),
        "monthly_worst_pct": round(float(np.min(arr)) * 100.0, 3),
        "monthly_best_pct": round(float(np.max(arr)) * 100.0, 3),
    }


def _align_business_days_multi(
    sleeve_maps: Mapping[str, Mapping[str, float]],
    *,
    start_day: str,
    end_day: str,
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
) -> tuple[list[str], np.ndarray, list[str]]:
    """Align multiple daily return maps onto Mon-Fri business days compounding weekends into Monday."""
    cut = _validate_cutoff_strict(cutoff_utc, context="align_business_days_multi")
    hi_eff = min(end_day, cut)
    enforce_pre_holdout_dates([start_day, hi_eff], context="align_multi.bounds", cutoff_day=HOLDOUT_START_DATE)
    names = list(sleeve_maps.keys())
    if not names:
        raise ValueError("sleeve_maps cannot be empty")
    for nm, smap in sleeve_maps.items():
        if smap:
            enforce_pre_holdout_dates(sorted(smap.keys()), context=f"align_multi.{nm}", cutoff_day=HOLDOUT_START_DATE)

    d0 = date.fromisoformat(start_day)
    d1 = date.fromisoformat(hi_eff)
    if d1 < d0:
        raise ValueError(f"Empty overlap window: {start_day}..{hi_eff}")

    biz_days: list[str] = []
    rows: list[list[float]] = []
    carry = {nm: 1.0 for nm in names}
    cur = d0
    while cur <= d1:
        iso = cur.isoformat()
        if cur.weekday() >= 5:
            for nm in names:
                carry[nm] *= 1.0 + float(sleeve_maps[nm].get(iso, 0.0))
        else:
            row = []
            for nm in names:
                r = float(sleeve_maps[nm].get(iso, 0.0))
                eff_r = carry[nm] * (1.0 + r) - 1.0
                carry[nm] = 1.0
                row.append(eff_r)
            biz_days.append(iso)
            rows.append(row)
        cur += timedelta(days=1)

    enforce_pre_holdout_dates(biz_days, context="align_multi.output", cutoff_day=HOLDOUT_START_DATE)
    return biz_days, np.asarray(rows, dtype=np.float64), names


def _summarize_blend(dates: Sequence[str], r_vec: np.ndarray) -> dict[str, Any]:
    m = fs.compute_series_metrics(r_vec, ann_days=252.0)
    st = compute_starved_month_metrics(dates, r_vec)
    return {
        "n_days": int(m["n_days"]),
        "sharpe": float(m["sharpe"]),
        "calmar": float(m["calmar"]),
        "max_dd_pct": float(m["max_dd_pct"]),
        "cagr_pct": float(m["cagr_pct"]),
        "ann_vol_pct": float(m["ann_vol_pct"]),
        "starved_months": st,
    }


def evaluate_pod_blend_impact(
    port7e_daily: Mapping[str, float] | None,
    sleeve_blind_daily: Mapping[str, Mapping[str, float]],
    surviving_sleeve_ids: Sequence[str],
    *,
    cluster_a_vols: Mapping[str, float] | None = None,
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
) -> dict[str, Any]:
    """Evaluate Pod-level `PORT_7E + surviving Frontier sleeve(s)` impact strictly on Dev Cluster B `<= 2024-12-31`.

    Uses ONLY causal/fixed allocation schemes (Equal Weight, 50/50 Core-Satellite, Causal Cluster A
    Inverse-Volatility) — zero in-sample weight fitting on Cluster B!
    """
    cut = _validate_cutoff_strict(cutoff_utc, context="evaluate_pod_blend_impact")
    if not port7e_daily:
        return {
            "status": "PORT_7E_UNAVAILABLE",
            "surviving_sleeves": list(surviving_sleeve_ids),
            "holdout_rows_analysed": 0,
            "blends": {},
        }

    p7e_sliced = {
        str(d): float(v)
        for d, v in port7e_daily.items()
        if str(d) <= cut and str(d) < HOLDOUT_START_DATE and math.isfinite(float(v))
    }
    enforce_pre_holdout_dates(sorted(p7e_sliced.keys()), context="pod_blend.port7e", cutoff_day=HOLDOUT_START_DATE)

    # Always report PORT_7E baseline on both 2019..2024 and 2023..2024 Dev Cluster B windows
    baselines: dict[str, Any] = {}
    for label, win_start in (("cluster_b_2019_2024", "2019-01-03"), ("cluster_b_2023_2024", "2023-01-01")):
        p7e_min = min(p7e_sliced.keys())
        p7e_max = min(max(p7e_sliced.keys()), cut)
        eff_lo = max(win_start, p7e_min)
        if eff_lo <= p7e_max:
            bdays, mat, _ = _align_business_days_multi(
                {"PORT_7E": p7e_sliced}, start_day=eff_lo, end_day=p7e_max, cutoff_utc=cut
            )
            baselines[label] = {
                "window": f"{bdays[0]}..{bdays[-1]}",
                **_summarize_blend(bdays, mat[:, 0]),
            }

    survivors = [sid for sid in surviving_sleeve_ids if sid in sleeve_blind_daily and sleeve_blind_daily[sid]]
    if not survivors:
        return {
            "status": "NO_SURVIVING_FRONTIER_SLEEVES",
            "surviving_sleeves": [],
            "holdout_rows_analysed": 0,
            "port_7e_baselines": baselines,
            "combined_blends": {},
            "pairwise_50_50_blends": {},
        }

    # Align PORT_7E + all surviving sleeves on their exact common Dev Cluster B overlap window <= 2024-12-31
    all_maps: dict[str, Mapping[str, float]] = {"PORT_7E": p7e_sliced}
    for sid in survivors:
        all_maps[sid] = sleeve_blind_daily[sid]

    ov_start = max(min(m.keys()) for m in all_maps.values())
    ov_end = min(cut, *(max(m.keys()) for m in all_maps.values()))
    biz_days, mat, cols = _align_business_days_multi(all_maps, start_day=ov_start, end_day=ov_end, cutoff_utc=cut)

    base_r = mat[:, 0]
    base_sum = _summarize_blend(biz_days, base_r)
    k_surv = len(survivors)

    def _with_delta(w_vec: np.ndarray, scheme: str) -> dict[str, Any]:
        blend_r = mat @ w_vec
        s = _summarize_blend(biz_days, blend_r)
        return {
            "scheme": scheme,
            "window": f"{biz_days[0]}..{biz_days[-1]}",
            "weights": {cols[i]: round(float(w_vec[i]), 4) for i in range(len(cols))},
            **s,
            "delta_vs_port7e": {
                "sharpe_delta": round(s["sharpe"] - base_sum["sharpe"], 4),
                "calmar_delta": round(s["calmar"] - base_sum["calmar"], 4),
                "max_dd_delta_pct": round(s["max_dd_pct"] - base_sum["max_dd_pct"], 4),
                "starved_le_0_reduction_pp": round(
                    base_sum["starved_months"]["starved_month_rate_le_0_pct"]
                    - s["starved_months"]["starved_month_rate_le_0_pct"],
                    2,
                ),
                "starved_lt_0p5_reduction_pp": round(
                    base_sum["starved_months"]["starved_month_rate_lt_0p5_pct"]
                    - s["starved_months"]["starved_month_rate_lt_0p5_pct"],
                    2,
                ),
                "max_consec_starved_le_0_delta": int(
                    s["starved_months"]["max_consec_starved_le_0"]
                    - base_sum["starved_months"]["max_consec_starved_le_0"]
                ),
            },
        }

    w_eq = np.full(1 + k_surv, 1.0 / float(1 + k_surv), dtype=np.float64)
    w_50_50 = np.array([0.50, *([0.50 / float(k_surv)] * k_surv)], dtype=np.float64)

    combined: dict[str, Any] = {
        "PORT_7E_ONLY": {
            "scheme": "PORT_7E_ONLY",
            "window": f"{biz_days[0]}..{biz_days[-1]}",
            "weights": {"PORT_7E": 1.0},
            **base_sum,
        },
        "EQUAL_WEIGHT": _with_delta(w_eq, "EQUAL_WEIGHT"),
        "CORE_50_FRONTIER_50": _with_delta(w_50_50, "CORE_50_FRONTIER_50"),
    }

    # Causal Cluster-A Inverse-Vol blend (strictly zero Cluster B weight fitting!)
    if cluster_a_vols and all(
        (nm in cluster_a_vols and math.isfinite(float(cluster_a_vols[nm])) and float(cluster_a_vols[nm]) > 1e-6)
        for nm in cols
    ):
        inv_v = np.array([1.0 / max(0.005, float(cluster_a_vols[nm])) for nm in cols], dtype=np.float64)
        w_inv = inv_v / float(np.sum(inv_v))
        combined["CAUSAL_CLUSTER_A_INV_VOL"] = _with_delta(w_inv, "CAUSAL_CLUSTER_A_INV_VOL")

    # Pairwise 50/50 PORT_7E + each surviving sleeve on that sleeve's full Cluster B overlap
    pairwise: dict[str, Any] = {}
    for sid in survivors:
        s_map = sleeve_blind_daily[sid]
        p_lo = max(min(p7e_sliced.keys()), min(s_map.keys()))
        p_hi = min(cut, max(p7e_sliced.keys()), max(s_map.keys()))
        p_days, p_mat, _ = _align_business_days_multi(
            {"PORT_7E": p7e_sliced, sid: s_map}, start_day=p_lo, end_day=p_hi, cutoff_utc=cut
        )
        p_base = _summarize_blend(p_days, p_mat[:, 0])
        p_50 = _summarize_blend(p_days, 0.50 * p_mat[:, 0] + 0.50 * p_mat[:, 1])
        pairwise[sid] = {
            "window": f"{p_days[0]}..{p_days[-1]}",
            "port_7e_only": p_base,
            "blend_50_50": p_50,
            "delta_vs_port7e": {
                "sharpe_delta": round(p_50["sharpe"] - p_base["sharpe"], 4),
                "calmar_delta": round(p_50["calmar"] - p_base["calmar"], 4),
                "max_dd_delta_pct": round(p_50["max_dd_pct"] - p_base["max_dd_pct"], 4),
                "starved_le_0_reduction_pp": round(
                    p_base["starved_months"]["starved_month_rate_le_0_pct"]
                    - p_50["starved_months"]["starved_month_rate_le_0_pct"],
                    2,
                ),
                "starved_lt_0p5_reduction_pp": round(
                    p_base["starved_months"]["starved_month_rate_lt_0p5_pct"]
                    - p_50["starved_months"]["starved_month_rate_lt_0p5_pct"],
                    2,
                ),
            },
        }

    return {
        "status": "SURVIVING_FRONTIER_SLEEVES_BLENDED",
        "surviving_sleeves": survivors,
        "common_overlap_window": f"{biz_days[0]}..{biz_days[-1]}",
        "holdout_rows_analysed": 0,
        "port_7e_baselines": baselines,
        "combined_blends": combined,
        "pairwise_50_50_blends": pairwise,
    }


# ---------------------------------------------------------------------------
# 5. Incumbent S3B Loader & Cluster A Vol Estimator (Strictly <= cutoff_utc)
# ---------------------------------------------------------------------------


def _load_s3b_incumbent_benchmarks(returns_dir: Path = fs.RETURNS_DIR) -> tuple[float, float]:
    """Read S3B Cluster B Sharpe & Calmar from `.runtime/quant-pod-returns/sleeve3b_macro_etf.json`."""
    p = returns_dir / "sleeve3b_macro_etf.json"
    if not p.is_file():
        return S3B_CLUSTER_B_INCUMBENT_SHARPE_FALLBACK, S3B_CLUSTER_B_INCUMBENT_CALMAR_FALLBACK
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        cb = raw.get("metrics_cluster_b", {})
        sh = float(cb.get("sharpe", S3B_CLUSTER_B_INCUMBENT_SHARPE_FALLBACK))
        cal = float(cb.get("calmar", S3B_CLUSTER_B_INCUMBENT_CALMAR_FALLBACK))
        if math.isfinite(sh) and math.isfinite(cal):
            return sh, cal
    except Exception:
        pass
    return S3B_CLUSTER_B_INCUMBENT_SHARPE_FALLBACK, S3B_CLUSTER_B_INCUMBENT_CALMAR_FALLBACK


# ---------------------------------------------------------------------------
# 6. Main One-Shot Blind Cluster B Orchestrator (`W4-G09`)
# ---------------------------------------------------------------------------


def run_blind_cluster_b_evaluation(
    *,
    frozen_json_path: str | Path = fs.DEFAULT_FROZEN_JSON_PATH,
    config_path: str | Path = fs.CONFIG_PATH,
    etf_cache_dir: str | Path = fs.ETF40_CACHE_DIR,
    crypto_cache_dir: str | Path = fs.CRYPTO_CACHE_DIR,
    duckdb_path: str | Path = fs.DEFAULT_DUCKDB_PATH,
    registry_path: str | Path | None = fs.DEFAULT_REGISTRY_PATH,
    verdict_json_path: str | Path = DEFAULT_VERDICT_JSON_PATH,
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
    s1_dev_returns: Mapping[str, float] | None = None,
    s4_dev_returns: Mapping[str, float] | None = None,
    panels_by_sleeve: Mapping[str, Mapping[str, Any]] | None = None,
    cluster_a_panels_by_sleeve: Mapping[str, Mapping[str, Any]] | None = None,
    grids: Mapping[str, Sequence[tuple[str, dict[str, Any]]]] | None = None,
    spa_n_boot: int = _HANSEN_SPA_BOOTS,
    spa_block_len: int = _HANSEN_SPA_BLOCK_LEN,
    spa_seed: int = _HANSEN_SPA_SEED,
    pbo_n_slices: int = 16,
) -> dict[str, Any]:
    """Execute SINGLE, ONE-SHOT blind Cluster B evaluation (`<= 2024-12-31`, `holdout_rows == 0`)."""
    cut = _validate_cutoff_strict(cutoff_utc, context="run_blind_cluster_b_evaluation")

    # Step 1: Fail-closed verification of frozen Cluster A bundle & all 3 candidate SHA-256s BEFORE touching Cluster B!
    bundle = verify_frozen_bundle_for_blind_eval(
        frozen_json_path=frozen_json_path,
        config_path=config_path,
        cutoff_utc=cut,
    )
    cfg = bundle["config"]
    candidates = bundle["candidates"]
    active_grids = grids if grids is not None else fs.PRE_REGISTERED_CLUSTER_A_GRIDS

    # Step 2: Load incumbent PORT_7E & S4 daily returns strictly <= cutoff_utc (< 2025-01-01)
    if s1_dev_returns is None and s4_dev_returns is None:
        s1_ref, s4_ref = fs._load_incumbent_returns_strict(max_date=cut, cutoff_utc=cut)
    else:
        s1_ref = (
            {str(d): float(v) for d, v in s1_dev_returns.items() if str(d) <= cut and str(d) < HOLDOUT_START_DATE}
            if s1_dev_returns is not None
            else None
        )
        s4_ref = (
            {str(d): float(v) for d, v in s4_dev_returns.items() if str(d) <= cut and str(d) < HOLDOUT_START_DATE}
            if s4_dev_returns is not None
            else None
        )
        if s1_ref:
            enforce_pre_holdout_dates(
                sorted(s1_ref.keys()), context="blind.s1_dev_returns", cutoff_day=HOLDOUT_START_DATE
            )
        if s4_ref:
            enforce_pre_holdout_dates(
                sorted(s4_ref.keys()), context="blind.s4_dev_returns", cutoff_day=HOLDOUT_START_DATE
            )

    s3b_sh_inc, s3b_cal_inc = _load_s3b_incumbent_benchmarks()

    # Step 3: Verify DuckDB budget headroom & one-shot non-duplication BEFORE running blind evaluations
    db_p = Path(duckdb_path)
    reg_p = Path(registry_path) if registry_path is not None else db_p.with_name(f"{db_p.stem}_registry.sqlite3")
    with fs.FrontierExperimentLedger(duckdb_path=db_p, registry_path=reg_p) as ledger:
        pre_integrity = ledger.verify_integrity()
        pre_total = ledger.get_total_trial_count()
        existing_ids = {row["trial_id"] for row in ledger.list_trials()}
        for sid in fs.FRONTIER_SLEEVE_IDS:
            btid = candidates[sid]["blind_trial_id"]
            if btid in existing_ids:
                raise ValueError(
                    f"DUPLICATE_BLIND_EVAL_BLOCKED: {btid!r} already recorded in {db_p}; "
                    "Cluster B is strictly one-shot!"
                )
        if pre_total + len(fs.FRONTIER_SLEEVE_IDS) > fs.WAVE4_FRONTIER_BUDGET_CAP:
            raise ValueError(
                f"WAVE4_FRONTIER_BUDGET_EXCEEDED: pre_total={pre_total} + {len(fs.FRONTIER_SLEEVE_IDS)} "
                f"> cap={fs.WAVE4_FRONTIER_BUDGET_CAP}"
            )

    # Step 4: Execute SINGLE blind Cluster B evaluation ONCE per sleeve (+ Cluster A PBO strictly <= cluster_a_end)
    evaluated_sleeves: set[str] = set()
    staged: dict[str, dict[str, Any]] = {}
    cluster_a_vols: dict[str, float] = {}
    if s1_ref:
        s1_a = [v for d, v in sorted(s1_ref.items()) if d <= "2018-12-31"]
        if len(s1_a) >= 20:
            cluster_a_vols["PORT_7E"] = float(np.std(np.asarray(s1_a, dtype=np.float64), ddof=1)) * math.sqrt(252.0)

    git_sha = fs._git_head_sha()

    for sid in fs.FRONTIER_SLEEVE_IDS:
        if sid in evaluated_sleeves:
            raise RuntimeError(f"DOUBLE_BLIND_EVAL_BLOCKED: {sid}")
        evaluated_sleeves.add(sid)

        cand = candidates[sid]
        spec = fs.get_sleeve_spec(sid, config=cfg)
        is_crypto = sid == fs.FRONTIER_03_ID
        a_end = spec["cluster_a_end"]
        b_end = min(spec["cluster_b_end"], cut)

        # 4a. Strictly Cluster A CSCV PBO over the M=8 pre-registered Cluster A grid (ZERO Cluster B dates!)
        if cluster_a_panels_by_sleeve is not None and sid in cluster_a_panels_by_sleeve:
            panel_a = cluster_a_panels_by_sleeve[sid]
        elif is_crypto:
            panel_a = fs.load_crypto_panel_strict(
                spec["required_dev_symbols"],
                max_date=a_end,
                cache_dir=crypto_cache_dir,
                cutoff_utc=cut,
                include_4h=True,
            )
        else:
            panel_a = fs.load_etf_panel_strict(
                spec["required_dev_symbols"],
                max_date=a_end,
                cache_dir=etf_cache_dir,
                cutoff_utc=cut,
            )

        pbo_info = compute_sleeve_cluster_a_pbo(
            sid,
            panel_a=panel_a,
            grid=active_grids[sid],
            config=cfg,
            cutoff_utc=cut,
            n_slices=pbo_n_slices,
        )

        # Also extract causal Cluster A volatility of frozen winner for causal Pod inverse-vol blend
        a_win_eval = fs.evaluate_sleeve(
            sid,
            cand["params"],
            split="cluster_a",
            cutoff_utc=cut,
            panel=panel_a,
            config=cfg,
        )
        a_vol_pct = float(a_win_eval["metrics_1x"]["ann_vol_pct"])
        if a_vol_pct > 1e-6:
            cluster_a_vols[sid] = a_vol_pct / 100.0

        # 4b. Load strictly bounded Dev panel <= b_end <= 2024-12-31 for ONE-SHOT blind Cluster B call
        if panels_by_sleeve is not None and sid in panels_by_sleeve:
            panel_b = panels_by_sleeve[sid]
        elif is_crypto:
            panel_b = fs.load_crypto_panel_strict(
                spec["required_dev_symbols"],
                max_date=b_end,
                cache_dir=crypto_cache_dir,
                cutoff_utc=cut,
                include_4h=True,
            )
        else:
            panel_b = fs.load_etf_panel_strict(
                spec["required_dev_symbols"],
                max_date=b_end,
                cache_dir=etf_cache_dir,
                cutoff_utc=cut,
            )

        # SINGLE, ONE-SHOT BLIND CLUSTER B CALL with exact frozen params!
        blind_res = fs.evaluate_sleeve(
            sid,
            cand["params"],
            split="cluster_b_blind",
            cutoff_utc=cut,
            panel=panel_b,
            s1_dev_returns=s1_ref,
            s4_dev_returns=s4_ref,
            config=cfg,
        )

        # Belt-and-suspenders anti-leakage & immutability assertions (no bare `assert`!)
        enforce_holdout_zero_rows(blind_res["holdout_rows_analysed"], context=f"blind_res.{sid}")
        if blind_res["max_loaded_date"] > cut or blind_res["eval_end_date"] > cut:
            raise HoldoutLockError(
                f"HOLDOUT_BREACH [{sid}]: "
                f"max_loaded={blind_res['max_loaded_date']}, eval_end={blind_res['eval_end_date']}"
            )
        if blind_res["params_sha256"] != cand["params_sha256"]:
            raise ValueError(f"PARAMS_SHA256_DRIFT [{sid}]: {blind_res['params_sha256']} != {cand['params_sha256']}")
        if blind_res["cluster_b_touched"] is not True:
            raise ValueError(f"BLIND_SPLIT_FLAG_INVALID [{sid}]: expected cluster_b_touched=True")
        if blind_res["order_send_count"] != 0:
            raise ValueError(f"ORDER_SEND_VIOLATION [{sid}]: order_send_count={blind_res['order_send_count']}")

        eval_dates = sorted(blind_res["daily_returns"].keys())
        enforce_pre_holdout_dates(eval_dates, context=f"blind_daily_returns.{sid}", cutoff_day=HOLDOUT_START_DATE)
        r_clb = np.array([float(blind_res["daily_returns"][d]) for d in eval_dates], dtype=np.float64)
        ann_days = float(blind_res["annualization_days"])

        # Newey-West HAC & IID p-values
        nw_stats = compute_newey_west_one_sided_p(r_clb)

        # CPCV with strict purging & embargoing on blind Cluster B returns
        cpcv_stats = compute_cpcv_oos_summary(
            r_clb,
            ann_days=ann_days,
            n_groups=6,
            k_test_groups=2,
            purge_bars=5,
            embargo_bars=5,
        )

        # Calendar-year 2022 inflation drawdown audit
        dd_2022 = compute_calendar_year_drawdown(blind_res["daily_returns"], year=2022, cutoff_utc=cut)

        # Hansen SPA (2005) studentized stationary bootstrap tests
        spa_zero = hansen_spa_test(r_clb, n_boot=spa_n_boot, block_len=spa_block_len, seed=spa_seed)
        spa_diagnostics: dict[str, Any] = {
            "vs_zero_cash": {
                "t_stat": round(float(spa_zero.t_stat), 4),
                "spa_p_consistent": round(float(spa_zero.spa_p_consistent), 6),
                "spa_p_lower": round(float(spa_zero.spa_p_lower), 6),
                "spa_p_upper": round(float(spa_zero.spa_p_upper), 6),
                "n_boot": int(spa_zero.n_boot),
                "block_len": int(spa_zero.block_len),
            }
        }
        primary_spa_p = float(spa_zero.spa_p_consistent)
        spa_vs_spy_vt_p: float | None = None

        if sid == fs.FRONTIER_01_ID:
            bil_base = compute_bil_cash_baseline(
                panel_b,
                eval_start=blind_res["eval_start_date"],
                eval_end=blind_res["eval_end_date"],
            )
            if len(bil_base["daily_returns"]) == len(r_clb):
                spa_bil = hansen_spa_test(
                    r_clb - bil_base["daily_returns"],
                    n_boot=spa_n_boot,
                    block_len=spa_block_len,
                    seed=spa_seed + 1,
                )
                spa_diagnostics["vs_bil_cash"] = {
                    "t_stat": round(float(spa_bil.t_stat), 4),
                    "spa_p_consistent": round(float(spa_bil.spa_p_consistent), 6),
                    "bil_sharpe": float(bil_base["metrics"]["sharpe"]),
                    "bil_cagr_pct": float(bil_base["metrics"]["cagr_pct"]),
                }

        elif sid == fs.FRONTIER_02_ID:
            spy_vt = compute_spy_vol_target_baseline(
                panel_b,
                target_vol=float(cand["params"]["target_vol"]),
                vol_lookback=int(cand["params"]["vol_lookback"]),
                safe_harbor=str(cand["params"]["safe_harbor"]),
                cost_bps_oneway=float(cand["canonical_gate"]["cost_model_1x_bps_one_way"]),
                eval_start=blind_res["eval_start_date"],
                eval_end=blind_res["eval_end_date"],
            )
            if len(spy_vt["daily_returns"]) != len(r_clb):
                raise ValueError(
                    f"SPY_VT_ALIGNMENT_MISMATCH [{sid}]: {len(spy_vt['daily_returns'])} != {len(r_clb)}"
                )
            spa_spy = hansen_spa_test(
                r_clb - spy_vt["daily_returns"],
                n_boot=spa_n_boot,
                block_len=spa_block_len,
                seed=spa_seed + 2,
            )
            spa_vs_spy_vt_p = float(spa_spy.spa_p_consistent)
            # Pre-registered F02 rule requires beating BOTH 0% cash AND plain SPY vol-targeting baseline
            primary_spa_p = max(float(spa_zero.spa_p_consistent), spa_vs_spy_vt_p)
            spa_diagnostics["vs_plain_spy_vol_target"] = {
                "t_stat": round(float(spa_spy.t_stat), 4),
                "spa_p_consistent": round(float(spa_spy.spa_p_consistent), 6),
                "spa_p_lower": round(float(spa_spy.spa_p_lower), 6),
                "spa_p_upper": round(float(spa_spy.spa_p_upper), 6),
                "spy_vt_sharpe": float(spy_vt["metrics"]["sharpe"]),
                "spy_vt_cagr_pct": float(spy_vt["metrics"]["cagr_pct"]),
                "spy_vt_max_dd_pct": float(spy_vt["metrics"]["max_dd_pct"]),
            }

        staged[sid] = {
            "candidate": cand,
            "blind_res": blind_res,
            "r_clb": r_clb,
            "ann_days": ann_days,
            "pbo_info": pbo_info,
            "nw_stats": nw_stats,
            "cpcv_stats": cpcv_stats,
            "dd_2022": dd_2022,
            "primary_spa_p": round(primary_spa_p, 6),
            "spa_vs_spy_vt_p": None if spa_vs_spy_vt_p is None else round(spa_vs_spy_vt_p, 6),
            "spa_diagnostics": spa_diagnostics,
        }

    # Step 5: Log the EXACT 3 blind rows into DuckDB `wave4_frontier_m36.duckdb` (`24 + 3 = 27 <= 36`)
    logged_blind_records: dict[str, dict[str, Any]] = {}
    with fs.FrontierExperimentLedger(duckdb_path=db_p, registry_path=reg_p) as ledger:
        for sid in fs.FRONTIER_SLEEVE_IDS:
            st = staged[sid]
            cand = st["candidate"]
            res = st["blind_res"]
            p_eff = float(st["nw_stats"]["p_conservative"])
            rec = ledger.record_trial(
                trial_id=cand["blind_trial_id"],
                sleeve_id=sid,
                split="cluster_b_blind",
                params=cand["params"],
                cluster_a_sharpe=float(res["sharpe"]),
                cluster_a_calmar=float(res["calmar"]),
                cluster_a_dd=float(res["max_dd_pct"]),
                cluster_a_cagr=float(res["cagr_pct"]),
                cluster_a_turnover=float(res["annual_turnover"]),
                corr_vs_7e=res["corr_vs_7e"],
                tail_corr_vs_7e=res["tail_corr_vs_7e"],
                cost_2x_net=float(res["cost_2x_net"]),
                cost_breakeven_mult=float(res["cost_breakeven_mult"]),
                holdout_rows_analysed=0,
                cluster_b_touched=True,
                p_value=p_eff,
                git_sha=git_sha,
                data_sha=res["data_sha256"],
            )
            logged_blind_records[sid] = rec

        all_trials_db = ledger.list_trials()
        post_integrity = ledger.verify_integrity()
        total_trials_logged = ledger.get_total_trial_count()

    # Step 6: Compute BH-FDR `q` across ALL `m_total` (= 27) DuckDB trials & Empirical DSR over `m_total`
    m_total = len(all_trials_db)
    if m_total != total_trials_logged or m_total > fs.WAVE4_FRONTIER_BUDGET_CAP:
        raise ValueError(f"LEDGER_COUNT_MISMATCH: m_total={m_total}, total={total_trials_logged}")

    all_p_vals = [float(row["p_value"]) for row in all_trials_db]
    all_q_vals = benjamini_hochberg(all_p_vals)
    q_by_trial_id = {
        str(row["trial_id"]): round(float(q), 6) for row, q in zip(all_trials_db, all_q_vals, strict=True)
    }

    # Build per-period trial Sharpes across ALL m_total trials (converting ETF /sqrt(252) vs Crypto /sqrt(365))
    all_per_period_sharpes: list[float] = []
    sleeve_ann_sharpes: dict[str, list[float]] = {sid: [] for sid in fs.FRONTIER_SLEEVE_IDS}
    for row in all_trials_db:
        r_sid = str(row["sleeve_id"])
        r_sh = row.get("cluster_a_sharpe")
        if r_sh is not None and math.isfinite(float(r_sh)):
            sh_val = float(r_sh)
            ann_d = 365.0 if r_sid == fs.FRONTIER_03_ID else 252.0
            all_per_period_sharpes.append(sh_val / math.sqrt(ann_d))
            if r_sid in sleeve_ann_sharpes:
                sleeve_ann_sharpes[r_sid].append(sh_val)

    # Step 7: Evaluate EVERY pre-registered falsification gate honestly for each of the 3 sleeves
    sleeve_verdicts: dict[str, dict[str, Any]] = {}
    surviving_sleeves: list[str] = []
    killed_sleeves: list[str] = []

    for sid in fs.FRONTIER_SLEEVE_IDS:
        st = staged[sid]
        cand = st["candidate"]
        res = st["blind_res"]
        r_clb = st["r_clb"]
        ann_days_int = int(round(float(st["ann_days"])))
        btid = cand["blind_trial_id"]
        bh_q = float(q_by_trial_id[btid])

        # Empirical DSR (Bailey & Lopez de Prado 2014):
        # Primary: within-sleeve empirical Sharpe variance (avoids ETF vs Crypto Carry scale distortion)
        #          with FULL conservative `n_trials = m_total (27)` multiple-testing penalty!
        # Diagnostics also report `dsr_empirical_within_sleeve_m9` and `dsr_empirical_pooled_all27`.
        s_sh = sleeve_ann_sharpes[sid]
        if len(s_sh) < 2 or float(np.std(r_clb, ddof=1)) <= 1e-15:
            dsr_m_total_val = 0.0
            dsr_m_total_meta: dict[str, Any] = {"dsr": 0.0, "mode": "degenerate_zero_var"}
            dsr_m_sleeve_val = 0.0
            dsr_pooled_val = 0.0
        else:
            dsr_m_total = deflated_sharpe_ratio_empirical(
                r_clb,
                trial_sharpes=s_sh,
                n_trials=m_total,
                annualization_days=ann_days_int,
                sharpes_are_annualized=True,
            )
            dsr_m_sleeve = deflated_sharpe_ratio_empirical(
                r_clb,
                trial_sharpes=s_sh,
                n_trials=len(s_sh),
                annualization_days=ann_days_int,
                sharpes_are_annualized=True,
            )
            dsr_pooled = deflated_sharpe_ratio_empirical(
                r_clb,
                trial_sharpes=all_per_period_sharpes,
                n_trials=m_total,
                annualization_days=ann_days_int,
                sharpes_are_annualized=False,
            )
            dsr_m_total_val = round(float(dsr_m_total.dsr), 4)
            dsr_m_sleeve_val = round(float(dsr_m_sleeve.dsr), 4)
            dsr_pooled_val = round(float(dsr_pooled.dsr), 4)
            dsr_m_total_meta = {
                "dsr": dsr_m_total_val,
                "z_stat": round(float(dsr_m_total.z_stat), 4),
                "observed_sr_annualized": round(float(dsr_m_total.observed_sr_annualized), 4),
                "expected_max_sr_annualized": round(
                    float(dsr_m_total.expected_max_sr) * math.sqrt(float(ann_days_int)), 4
                ),
                "sr_trials_var_per_period": round(float(dsr_m_total.sr_trials_var), 8),
                "n_trials_penalty": int(dsr_m_total.n_trials),
                "n_sleeve_trials_for_var": int(len(s_sh)),
                "skewness": round(float(dsr_m_total.skewness), 4),
                "kurtosis": round(float(dsr_m_total.kurtosis), 4),
                "dsr_within_sleeve_m9": dsr_m_sleeve_val,
                "dsr_pooled_all27_cross_asset_diagnostic": dsr_pooled_val,
            }

        diag = res["diagnostics"]
        gate_input: dict[str, Any] = {
            "holdout_rows_analysed": int(res["holdout_rows_analysed"]),
            "eval_end_date": str(res["eval_end_date"]),
            "max_loaded_date": str(res["max_loaded_date"]),
            "order_send_count": int(res["order_send_count"]),
            "sharpe": float(res["sharpe"]),
            "calmar": float(res["calmar"]),
            "max_dd_pct": float(res["max_dd_pct"]),
            "cagr_pct": float(res["cagr_pct"]),
            "pbo_cscv": float(st["pbo_info"]["pbo_cscv"]),
            "dsr_empirical": float(dsr_m_total_val),
            "bh_fdr_q": float(bh_q),
            "hansen_spa_p": float(st["primary_spa_p"]),
            "hansen_spa_vs_spy_vt_p": st["spa_vs_spy_vt_p"],
            "cost_2x_net_pct": float(res["cost_2x_net"]),
            "cost_breakeven_mult": float(res["cost_breakeven_mult"]),
            "annual_turnover": float(res["annual_turnover"]),
            "corr_vs_7e": res["corr_vs_7e"],
            "tail_corr_vs_7e": res["tail_corr_vs_7e"],
            "corr_vs_s4_etf": res["corr_vs_s4_etf"],
            "pre_listing_weight_violations": int(diag["pre_listing_weight_violations"]),
            "signal_only_max_abs_weight": float(diag["signal_only_max_abs_weight"]),
            "cpcv_purge_embargo_verified": bool(st["cpcv_stats"]["cpcv_purge_embargo_verified"]),
            "max_dd_2022_pct": st["dd_2022"]["max_dd_pct"],
        }
        if sid == fs.FRONTIER_03_ID:
            gate_input["cross_liq_events"] = int(diag.get("cross_liq_events", 0))
            gate_input["isolated_liq_events"] = int(diag.get("isolated_liq_events", 0))

        gate_eval = evaluate_sleeve_falsification_gates(
            sid,
            gate_input,
            cand["canonical_gate"],
            incumbent_s3b_sharpe=s3b_sh_inc,
            incumbent_s3b_calmar=s3b_cal_inc,
        )

        if gate_eval["verdict"] == VERDICT_PASS:
            surviving_sleeves.append(sid)
        else:
            killed_sleeves.append(sid)

        sleeve_verdicts[sid] = {
            "sleeve_id": sid,
            "frozen_trial_id": cand["frozen_trial_id"],
            "blind_trial_id": btid,
            "candidate_sha256": cand["candidate_sha256"],
            "params_sha256": cand["params_sha256"],
            "params": cand["params"],
            "verdict": gate_eval["verdict"],
            "all_gates_passed": gate_eval["all_gates_passed"],
            "failed_gates": gate_eval["failed_gates"],
            "gate_checks": gate_eval["checks"],
            "gate_details": gate_eval["gate_details"],
            "eval_window": f"{res['eval_start_date']}..{res['eval_end_date']}",
            "eval_start_date": res["eval_start_date"],
            "eval_end_date": res["eval_end_date"],
            "max_loaded_date": res["max_loaded_date"],
            "n_eval_days": int(res["n_eval_days"]),
            "annualization_days": float(res["annualization_days"]),
            "blind_metrics": {
                "sharpe": float(res["sharpe"]),
                "calmar": float(res["calmar"]),
                "max_dd_pct": float(res["max_dd_pct"]),
                "cagr_pct": float(res["cagr_pct"]),
                "ann_vol_pct": float(res["metrics_1x"]["ann_vol_pct"]),
                "total_net_return_pct": float(res["metrics_1x"]["total_net_return_pct"]),
                "cost_2x_net_pct": float(res["cost_2x_net"]),
                "cost_2x_cagr_pct": float(res["cost_2x_cagr_pct"]),
                "cost_2x_sharpe": float(res["cost_2x_sharpe"]),
                "cost_breakeven_mult": float(res["cost_breakeven_mult"]),
                "annual_turnover": float(res["annual_turnover"]),
                "corr_vs_7e": res["corr_vs_7e"],
                "tail_corr_vs_7e": res["tail_corr_vs_7e"],
                "corr_vs_s4_etf": res["corr_vs_s4_etf"],
                "p_iid": float(st["nw_stats"]["p_iid"]),
                "p_newey_west": float(st["nw_stats"]["p_newey_west"]),
                "p_value_logged": float(st["nw_stats"]["p_conservative"]),
                "bh_fdr_q": float(bh_q),
                "bh_fdr_m_total": int(m_total),
                "pbo_cscv": float(st["pbo_info"]["pbo_cscv"]),
                "dsr_empirical": float(dsr_m_total_val),
                "hansen_spa_p": float(st["primary_spa_p"]),
                "hansen_spa_vs_spy_vt_p": st["spa_vs_spy_vt_p"],
                "max_dd_2022_pct": st["dd_2022"]["max_dd_pct"],
            },
            "statistical_audits": {
                "pbo_cscv_cluster_a_grid": st["pbo_info"],
                "dsr_empirical_detail": dsr_m_total_meta,
                "newey_west_detail": st["nw_stats"],
                "cpcv_purge_embargo_detail": st["cpcv_stats"],
                "hansen_spa_detail": st["spa_diagnostics"],
                "inflation_2022_detail": st["dd_2022"],
            },
            "diagnostics": diag,
            "cluster_a_reference": cand["cluster_a_metrics"],
            "pre_registered_falsification_gate": cand["canonical_gate"],
            "registry_event_hash": logged_blind_records[sid]["registry_event_hash"],
            "data_sha256": res["data_sha256"],
            "holdout_rows_analysed": 0,
            "cluster_b_touched": True,
            "order_send_count": 0,
        }

    # Step 8: Pod-level blend impact (`PORT_7E + surviving Frontier sleeve(s)`) strictly on Dev Cluster B <= 2024-12-31
    blind_daily_by_sleeve = {sid: staged[sid]["blind_res"]["daily_returns"] for sid in fs.FRONTIER_SLEEVE_IDS}
    pod_blend = evaluate_pod_blend_impact(
        s1_ref,
        blind_daily_by_sleeve,
        surviving_sleeves,
        cluster_a_vols=cluster_a_vols,
        cutoff_utc=cut,
    )

    verdict_doc: dict[str, Any] = {
        "schema_version": BLIND_VERDICT_SCHEMA_VERSION,
        "generated_utc": _utc_now_iso(),
        "worker": "w4-m2b-blind",
        "gate_id": "W4-G09",
        "wave": "Wave 2A (Total Offensive #4 v4.8.1 FINAL)",
        "family_budget_id": fs.WAVE4_FRONTIER_FAMILY_ID,
        "budget_cap": fs.WAVE4_FRONTIER_BUDGET_CAP,
        "pre_blind_trials_total": int(pre_total),
        "blind_trials_logged": len(fs.FRONTIER_SLEEVE_IDS),
        "total_trials_logged": int(total_trials_logged),
        "budget_headroom_remaining": int(fs.WAVE4_FRONTIER_BUDGET_CAP - total_trials_logged),
        "dev_cutoff_utc": cut,
        "holdout_rows_analysed": 0,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "spend_vnd": SPEND_VND,
        "zero_retuning_verified": True,
        "zero_lowering_standards_verified": True,
        "git_sha": git_sha,
        "frozen_cluster_a_source": {
            "path": (
                str(Path(frozen_json_path).resolve().relative_to(REPO_ROOT).as_posix())
                if Path(frozen_json_path).resolve().is_relative_to(REPO_ROOT)
                else str(frozen_json_path)
            ),
            "file_sha256": bundle["frozen_file_sha256"],
            "manifest_sha256": bundle["frozen_manifest_sha256"],
        },
        "duckdb_path": (
            str(db_p.resolve().relative_to(REPO_ROOT).as_posix())
            if db_p.resolve().is_relative_to(REPO_ROOT)
            else str(db_p)
        ),
        "registry_path": (
            str(reg_p.resolve().relative_to(REPO_ROOT).as_posix())
            if reg_p.resolve().is_relative_to(REPO_ROOT)
            else str(reg_p)
        ),
        "pre_blind_ledger_integrity": pre_integrity,
        "post_blind_ledger_integrity": post_integrity,
        "summary": {
            "evaluated_count": len(fs.FRONTIER_SLEEVE_IDS),
            "surviving_count": len(surviving_sleeves),
            "killed_count": len(killed_sleeves),
            "surviving_sleeves": surviving_sleeves,
            "killed_sleeves": killed_sleeves,
            "verdicts_by_sleeve": {sid: sleeve_verdicts[sid]["verdict"] for sid in fs.FRONTIER_SLEEVE_IDS},
        },
        "sleeves": sleeve_verdicts,
        "pod_blend_impact": pod_blend,
        "bh_fdr_all_trials_m_total": int(m_total),
        "bh_fdr_blind_q_by_trial_id": {
            candidates[sid]["blind_trial_id"]: q_by_trial_id[candidates[sid]["blind_trial_id"]]
            for sid in fs.FRONTIER_SLEEVE_IDS
        },
    }
    verdict_doc["report_sha256"] = sha256_json_canonical(
        {k: v for k, v in verdict_doc.items() if k != "report_sha256"}
    )
    atomic_write_json(verdict_json_path, verdict_doc, indent=2)
    return verdict_doc


# ---------------------------------------------------------------------------
# 7. Fail-Closed Blind Verdict Verifier
# ---------------------------------------------------------------------------


def verify_blind_verdict_artifact(
    verdict_json_path: str | Path = DEFAULT_VERDICT_JSON_PATH,
    *,
    duckdb_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Fail-closed verifier for `frontier_cluster_b_blind_verdict.json` and optional DuckDB parity."""
    p = Path(verdict_json_path)
    if not p.is_file():
        raise FileNotFoundError(f"Blind Cluster B verdict artifact not found: {p}")
    doc = json.loads(p.read_text(encoding="utf-8"))

    if doc.get("schema_version") != BLIND_VERDICT_SCHEMA_VERSION:
        raise ValueError(f"Unexpected schema_version={doc.get('schema_version')!r}")
    enforce_holdout_zero_rows(doc.get("holdout_rows_analysed", -1), context="verify_blind_verdict")
    _validate_cutoff_strict(doc.get("dev_cutoff_utc"), context="verify_blind_verdict")
    if doc.get("order_send_count") != 0 or doc.get("order_send_capable") is not False:
        raise ValueError("ORDER_SEND_SAFETY_VIOLATION in blind verdict artifact")

    total = _require_int(doc.get("total_trials_logged"), "total_trials_logged", lo=1, hi=fs.WAVE4_FRONTIER_BUDGET_CAP)
    cap = _require_int(doc.get("budget_cap"), "budget_cap", lo=total, hi=fs.WAVE4_FRONTIER_BUDGET_CAP)
    if cap != fs.WAVE4_FRONTIER_BUDGET_CAP:
        raise ValueError(f"Unexpected budget_cap={cap} != {fs.WAVE4_FRONTIER_BUDGET_CAP}")

    expected_sha = sha256_json_canonical({k: v for k, v in doc.items() if k != "report_sha256"})
    if doc.get("report_sha256") != expected_sha:
        raise ValueError(f"VERDICT_REPORT_SHA256_MISMATCH: {doc.get('report_sha256')} != {expected_sha}")

    sleeves = doc.get("sleeves", {})
    s3b_sh_inc, s3b_cal_inc = _load_s3b_incumbent_benchmarks()
    for sid in fs.FRONTIER_SLEEVE_IDS:
        if sid not in sleeves:
            raise ValueError(f"Missing sleeve verdict for {sid}")
        sv = sleeves[sid]
        enforce_holdout_zero_rows(sv.get("holdout_rows_analysed", -1), context=f"verify_blind.{sid}")
        _validate_cutoff_strict(sv.get("eval_end_date"), context=f"verify_blind.{sid}.eval_end")
        _validate_cutoff_strict(sv.get("max_loaded_date"), context=f"verify_blind.{sid}.max_loaded")
        bm = sv["blind_metrics"]
        diag = sv["diagnostics"]
        recheck_input = {
            "holdout_rows_analysed": int(sv["holdout_rows_analysed"]),
            "eval_end_date": str(sv["eval_end_date"]),
            "max_loaded_date": str(sv["max_loaded_date"]),
            "order_send_count": int(sv["order_send_count"]),
            "sharpe": bm["sharpe"],
            "calmar": bm["calmar"],
            "pbo_cscv": bm["pbo_cscv"],
            "dsr_empirical": bm["dsr_empirical"],
            "bh_fdr_q": bm["bh_fdr_q"],
            "hansen_spa_p": bm["hansen_spa_p"],
            "hansen_spa_vs_spy_vt_p": bm.get("hansen_spa_vs_spy_vt_p"),
            "cost_2x_net_pct": bm["cost_2x_net_pct"],
            "cost_breakeven_mult": bm["cost_breakeven_mult"],
            "annual_turnover": bm["annual_turnover"],
            "corr_vs_7e": bm["corr_vs_7e"],
            "tail_corr_vs_7e": bm["tail_corr_vs_7e"],
            "corr_vs_s4_etf": bm.get("corr_vs_s4_etf"),
            "pre_listing_weight_violations": diag["pre_listing_weight_violations"],
            "signal_only_max_abs_weight": diag["signal_only_max_abs_weight"],
            "cpcv_purge_embargo_verified": sv["statistical_audits"]["cpcv_purge_embargo_detail"][
                "cpcv_purge_embargo_verified"
            ],
            "max_dd_2022_pct": bm.get("max_dd_2022_pct"),
        }
        if sid == fs.FRONTIER_03_ID:
            recheck_input["cross_liq_events"] = diag["cross_liq_events"]
            recheck_input["isolated_liq_events"] = diag["isolated_liq_events"]
        recheck = evaluate_sleeve_falsification_gates(
            sid,
            recheck_input,
            sv["pre_registered_falsification_gate"],
            incumbent_s3b_sharpe=s3b_sh_inc,
            incumbent_s3b_calmar=s3b_cal_inc,
        )
        if sv.get("verdict") != recheck["verdict"] or sv.get("failed_gates") != recheck["failed_gates"]:
            raise ValueError(
                f"VERDICT_RECOMPUTATION_MISMATCH [{sid}]: stored={sv.get('verdict')}/{sv.get('failed_gates')} "
                f"!= recomputed={recheck['verdict']}/{recheck['failed_gates']}"
            )

    db_ver: dict[str, Any] | None = None
    if duckdb_path is not None:
        with fs.FrontierExperimentLedger(duckdb_path=duckdb_path, registry_path=registry_path) as ledger:
            db_ver = ledger.verify_integrity()
            if db_ver["wave4_frontier_trials_count"] != total:
                raise ValueError(
                    f"DUCKDB_TRIAL_COUNT_MISMATCH: db={db_ver['wave4_frontier_trials_count']} != verdict={total}"
                )

    return {
        "verified": True,
        "path": str(p),
        "file_sha256": sha256_file(p),
        "report_sha256": expected_sha,
        "total_trials_logged": total,
        "budget_cap": cap,
        "holdout_rows_analysed": 0,
        "verdicts_by_sleeve": doc["summary"]["verdicts_by_sleeve"],
        "duckdb_integrity": db_ver,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wave 2A One-Shot Blind Cluster B Evaluation for 3 Frozen Frontier Sleeves (OrderSend=0)."
    )
    parser.add_argument(
        "--run-blind",
        action="store_true",
        help="Execute the single, one-shot blind Cluster B evaluation and log 3 rows into DuckDB.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify existing blind Cluster B verdict artifact & DuckDB integrity without running evaluations.",
    )
    parser.add_argument("--frozen-path", type=Path, default=fs.DEFAULT_FROZEN_JSON_PATH)
    parser.add_argument("--duckdb-path", type=Path, default=fs.DEFAULT_DUCKDB_PATH)
    parser.add_argument("--registry-path", type=Path, default=fs.DEFAULT_REGISTRY_PATH)
    parser.add_argument("--verdict-path", type=Path, default=DEFAULT_VERDICT_JSON_PATH)
    args = parser.parse_args(argv)

    if args.run_blind:
        doc = run_blind_cluster_b_evaluation(
            frozen_json_path=args.frozen_path,
            duckdb_path=args.duckdb_path,
            registry_path=args.registry_path,
            verdict_json_path=args.verdict_path,
        )
        out = {
            "status": "COMPLETED",
            "total_trials_logged": doc["total_trials_logged"],
            "budget_cap": doc["budget_cap"],
            "holdout_rows_analysed": doc["holdout_rows_analysed"],
            "report_sha256": doc["report_sha256"],
            "summary": doc["summary"],
            "sleeves": {
                sid: {
                    "trial_id": sv["blind_trial_id"],
                    "verdict": sv["verdict"],
                    "failed_gates": sv["failed_gates"],
                    "sharpe": sv["blind_metrics"]["sharpe"],
                    "calmar": sv["blind_metrics"]["calmar"],
                    "max_dd_pct": sv["blind_metrics"]["max_dd_pct"],
                    "pbo_cscv": sv["blind_metrics"]["pbo_cscv"],
                    "dsr_empirical": sv["blind_metrics"]["dsr_empirical"],
                    "bh_fdr_q": sv["blind_metrics"]["bh_fdr_q"],
                    "hansen_spa_p": sv["blind_metrics"]["hansen_spa_p"],
                    "corr_vs_7e": sv["blind_metrics"]["corr_vs_7e"],
                    "tail_corr_vs_7e": sv["blind_metrics"]["tail_corr_vs_7e"],
                    "cost_2x_net_pct": sv["blind_metrics"]["cost_2x_net_pct"],
                    "max_dd_2022_pct": sv["blind_metrics"]["max_dd_2022_pct"],
                }
                for sid, sv in doc["sleeves"].items()
            },
        }
        print(json.dumps(out, indent=2))
        return 0

    if args.verify_only:
        ver = verify_blind_verdict_artifact(
            args.verdict_path,
            duckdb_path=args.duckdb_path,
            registry_path=args.registry_path,
        )
        print(json.dumps(ver, indent=2))
        return 0

    parser.print_help()
    return 0


__all__ = [
    "BLIND_VERDICT_SCHEMA_VERSION",
    "DEFAULT_BLIND_DROPBOX_PATH",
    "DEFAULT_BLIND_RECEIPT_PATH",
    "DEFAULT_VERDICT_JSON_PATH",
    "F02_2022_DD_LIMIT_PCT",
    "HOLDOUT_CUTOFF_DATE",
    "HOLDOUT_START_DATE",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "RECEIPT_SCHEMA_VERSION",
    "S3B_S4_2022_INCUMBENT_DD_LIMIT_PCT",
    "VERDICT_KILLED",
    "VERDICT_PASS",
    "compute_bil_cash_baseline",
    "compute_calendar_year_drawdown",
    "compute_cpcv_oos_summary",
    "compute_newey_west_one_sided_p",
    "compute_sleeve_cluster_a_pbo",
    "compute_spy_vol_target_baseline",
    "compute_starved_month_metrics",
    "evaluate_pod_blend_impact",
    "evaluate_sleeve_falsification_gates",
    "run_blind_cluster_b_evaluation",
    "verify_blind_verdict_artifact",
    "verify_frozen_bundle_for_blind_eval",
]

if __name__ == "__main__":
    raise SystemExit(main())
