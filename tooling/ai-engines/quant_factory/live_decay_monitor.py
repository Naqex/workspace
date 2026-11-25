"""Live Alpha Decay & Concept Drift Monitor (reuses projects/quant-trading CUSUM + Wald SPRT + MC Confidence Cones).

Distinguishes objectively between normal expected drawdown noise (e.g., 2019/2021 flat periods)
and genuine structural strategy decay during forward demo / live trading.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
QT_SRC = ROOT / "projects/quant-trading/src"
if QT_SRC.exists() and str(QT_SRC) not in sys.path:
    sys.path.insert(0, str(QT_SRC))

from quant_trading.change_detection import CUSUMConfig, run_cusum  # noqa: E402
from quant_trading.state_primitives import CausalObservation  # noqa: E402


def calibrate_baseline(dev_series: np.ndarray) -> dict:
    """Freeze baseline mean, std, and empirical array strictly from sealed Development returns."""
    arr = np.asarray(dev_series, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    if len(arr) < 30:
        raise ValueError("Baseline series requires at least 30 observations")
    mu = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1))
    return {"n_dev": int(len(arr)), "mu": mu, "sd": max(sd, 1e-9)}


def evaluate_live_decay(
    dev_series: np.ndarray,
    live_series: np.ndarray,
    *,
    cusum_k_sigma: float = 0.25,
    cusum_h_sigma: float = 4.5,
    sprt_alpha: float = 0.05,
    sprt_beta: float = 0.10,
    n_cone_draws: int = 2000,
    seed: int = 20261123,
) -> dict:
    """Audit live/forward return stream against frozen Development baseline using 3 independent lenses:

      1. Two-sided causal Page CUSUM (via `projects/quant-trading/src/quant_trading/change_detection.py`).
      2. Wald Sequential Probability Ratio Test (SPRT: H0 mu=mu_dev vs H1 mu<=0).
      3. Non-parametric bootstrap Confidence Cone (5th / 10th / 50th / 90th percentiles) for exact horizon N.
    """
    base = calibrate_baseline(dev_series)
    dev_arr = np.asarray(dev_series, dtype=np.float64)
    dev_arr = dev_arr[np.isfinite(dev_arr)]
    live_arr = np.asarray(live_series, dtype=np.float64)
    live_arr = live_arr[np.isfinite(live_arr)]
    n_live = len(live_arr)
    if n_live == 0:
        return {"schema": "naqex-live-decay-v1", "n_live": 0, "verdict": "NO_LIVE_DATA"}

    mu0, sd0 = base["mu"], base["sd"]
    z_live = (live_arr - mu0) / sd0

    # 1. Causal Page CUSUM reusing projects/quant-trading verified primitive
    obs = [
        CausalObservation(event_time=i + 1, known_at=i + 1, sequence=i, value=float(z))
        for i, z in enumerate(z_live)
    ]
    cusum_cfg = CUSUMConfig(baseline=0.0, threshold=float(cusum_h_sigma), drift=float(cusum_k_sigma), reset_on_detection=False)
    cusum_res = run_cusum(obs, config=cusum_cfg)
    min_neg_stat = min((s.negative_stat for s in cusum_res.steps), default=0.0)
    cur_neg_stat = cusum_res.steps[-1].negative_stat if cusum_res.steps else 0.0
    neg_triggers = [s.sequence for s in cusum_res.detections if s.direction in ("negative", "both")]
    active_cusum_breach = (-cur_neg_stat) >= float(cusum_h_sigma)

    # 2. Wald SPRT (Gaussian log-likelihood ratio testing H1: mu=0 vs H0: mu=mu0)
    # Positive LLR favors H1 (edge decayed to zero); negative LLR favors H0 (edge intact)
    llr = 0.0
    max_llr = -1e9
    if mu0 > 0.0:
        for x in live_arr:
            llr += ((x - mu0) ** 2 - (x - 0.0) ** 2) / (2.0 * sd0 * sd0)
            if llr > max_llr:
                max_llr = llr
    else:
        max_llr = 0.0
    upper_bound = math.log((1.0 - sprt_beta) / sprt_alpha)  # reject H0 (edge decayed)
    lower_bound = math.log(sprt_beta / (1.0 - sprt_alpha))  # accept H0 (edge confirmed)
    if llr >= upper_bound:
        sprt_state = "REJECT_EDGE_DECAYED"
    elif llr <= lower_bound:
        sprt_state = "CONFIRM_EDGE_INTACT"
    else:
        sprt_state = "INCONCLUSIVE_CONTINUE"

    # 3. Empirical Bootstrap Confidence Cone on cumulative live PnL / R
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(dev_arr), size=(n_cone_draws, n_live))
    sim_cum = dev_arr[idx].sum(axis=1)
    obs_cum = float(live_arr.sum())
    p05, p10, p50, p90 = [float(np.percentile(sim_cum, q)) for q in (5, 10, 50, 90)]
    emp_pct_rank = round(100.0 * float(np.mean(sim_cum <= obs_cum)), 1)

    # Combined objective verdict (uses CURRENT active CUSUM breach so already-recovered drawdowns clear cleanly)
    reasons = []
    if active_cusum_breach and (sprt_state == "REJECT_EDGE_DECAYED" or obs_cum < p05):
        verdict = "RED_HALT_ALPHA_DECAY"
        reasons.append(f"Active negative CUSUM {cur_neg_stat:.2f}σ <= -{cusum_h_sigma}σ AND confirmed by SPRT/p05 cone")
    elif active_cusum_breach or obs_cum < p05 or sprt_state == "REJECT_EDGE_DECAYED":
        verdict = "AMBER_WATCH_REDUCE_SIZE"
        if active_cusum_breach:
            reasons.append(f"Active negative CUSUM breach ({cur_neg_stat:.2f}σ <= -{cusum_h_sigma}σ)")
        if obs_cum < p05:
            reasons.append(f"Cumulative live sum {obs_cum:.3f} below 5th-percentile Dev cone ({p05:.3f})")
        if sprt_state == "REJECT_EDGE_DECAYED":
            reasons.append(f"Wald SPRT LLR={llr:.2f} >= {upper_bound:.2f}")
    else:
        verdict = "GREEN_WITHIN_EXPECTATION"
        reasons.append(f"Live cumulative {obs_cum:.3f} at {emp_pct_rank}th pct of Dev cone (p05={p05:.3f}, p50={p50:.3f}); current CUSUM={cur_neg_stat:.2f}σ")

    return {
        "schema": "naqex-live-decay-v1",
        "baseline": base,
        "n_live": n_live,
        "live_mean": round(float(np.mean(live_arr)), 5),
        "live_cum": round(obs_cum, 4),
        "cusum": {
            "schema": cusum_res.schema,
            "current_negative_sigma": round(cur_neg_stat, 3),
            "min_negative_sigma": round(min_neg_stat, 3),
            "threshold_sigma": cusum_h_sigma,
            "active_breach": active_cusum_breach,
            "historical_trigger_count": len(neg_triggers),
            "first_negative_step": neg_triggers[0] if neg_triggers else None,
            "result_sha256": cusum_res.canonical_sha256()[:16],
        },
        "sprt": {
            "llr": round(llr, 3),
            "upper_reject_edge": round(upper_bound, 3),
            "lower_confirm_edge": round(lower_bound, 3),
            "state": sprt_state,
        },
        "confidence_cone": {
            "p05": round(p05, 4),
            "p10": round(p10, 4),
            "p50": round(p50, 4),
            "p90": round(p90, 4),
            "observed_percentile": emp_pct_rank,
        },
        "verdict": verdict,
        "reasons": reasons,
    }
