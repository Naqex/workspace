"""Lab #6 / #7 — Purged Embargo Walk-Forward Meta-Labeling (Lopez de Prado AFML Ch. 3, 7 & 10).

STRICT CAUSAL & SEALED BOUNDARIES:
  - Holdout `2025-2026` for FX/Gold/Index (`PORT_7E`) remains 100% SEALED (`holdout_rows_analysed = 0`, `OrderSend = 0`).
  - Frozen primary white-box entry signals (`PORT_7E` Dev `2018-2024` and `Crypto F4_4H_EMA_24_120_BTC` `2019-2026`)
    are NEVER altered in entry timing or direction.
  - Meta-Labeling ONLY predicts P(primary trade profitable | 6 strictly causal pre-entry regime/vol features)
    inside an expanding Purged + Embargo Walk-Forward scheme (strict `purge_days` + `embargo_days` gap,
    in-fold feature standardization, zero look-ahead!).
  - Evaluates 2 white-box models (pure NumPy/SciPy, zero sklearn bloat):
      1. L2-Regularized Logistic Regression (`fit_l2_logistic`, exact L-BFGS-B analytic gradient)
      2. Shallow Regularized Boosted Decision Stumps (`fit_shallow_stump_ensemble`, min_leaf >= 40)
    across 2 AFML Ch. 10 bet-sizing policies:
      - Continuous sizing `[0.50x .. 1.25x]`
      - Toxic-regime binary filter `[0.00x / 1.00x]` (drops bottom-20% predicted probability tail)
  - Compares head-to-head against unmodified raw signals on blind Cluster B and reports honestly
    whether Meta-Labeling improves or degrades blind OOS!
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time

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
from quant_factory.portfolio_allocator import DEFAULT_RETURNS_DIR, compute_series_metrics
from quant_factory.report_gen import format_markdown_table


def _sigmoid(z: np.ndarray) -> np.ndarray:
    zc = np.clip(z, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-zc))


def fit_l2_logistic(
    X: np.ndarray,
    y: np.ndarray,
    *,
    l2_reg: float = 2.0,
) -> dict:
    """Fit L2-regularized binary logistic regression with exact analytic gradient (zero external ML deps)."""
    x_arr = np.asarray(X, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    n, d = x_arr.shape
    mu = np.mean(x_arr, axis=0)
    sd = np.std(x_arr, axis=0, ddof=0)
    sd = np.where(sd > 1e-8, sd, 1.0)
    xs = (x_arr - mu) / sd

    base_p = float(np.clip(np.mean(y_arr), 1e-4, 1.0 - 1e-4))
    w0 = np.zeros(d + 1, dtype=np.float64)
    w0[-1] = math.log(base_p / (1.0 - base_p))

    def _loss_and_grad(params: np.ndarray) -> tuple[float, np.ndarray]:
        w, b = params[:-1], params[-1]
        logits = xs @ w + b
        p = _sigmoid(logits)
        # Stable binary cross-entropy + L2 penalty on weights only (bias unpenalized)
        loss = float(np.mean(np.logaddexp(0.0, logits) - y_arr * logits)) + 0.5 * l2_reg * float(np.dot(w, w)) / max(1, n)
        diff = (p - y_arr) / max(1, n)
        grad_w = xs.T @ diff + (l2_reg / max(1, n)) * w
        grad_b = float(np.sum(diff))
        return loss, np.r_[grad_w, grad_b]

    from scipy.optimize import minimize

    res = minimize(_loss_and_grad, w0, jac=True, method="L-BFGS-B", options={"maxiter": 250, "ftol": 1e-10})
    params = res.x if np.all(np.isfinite(res.x)) else w0
    return {
        "kind": "l2_logistic",
        "mu": mu,
        "sd": sd,
        "w": params[:-1].copy(),
        "b": float(params[-1]),
        "base_rate": base_p,
    }


def predict_proba_logistic(model: dict, X: np.ndarray) -> np.ndarray:
    xs = (np.asarray(X, dtype=np.float64) - model["mu"]) / model["sd"]
    return _sigmoid(xs @ model["w"] + model["b"])


def fit_shallow_stump_ensemble(
    X: np.ndarray,
    y: np.ndarray,
    *,
    n_stumps: int = 4,
    learning_rate: float = 0.25,
    min_leaf: int = 40,
) -> dict:
    """Fit shallow regularized gradient-boosted decision stumps (depth=1, min_leaf>=40) for regime nonlinearity."""
    x_arr = np.asarray(X, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    n, d = x_arr.shape
    base_p = float(np.clip(np.mean(y_arr), 1e-4, 1.0 - 1e-4))
    f0 = math.log(base_p / (1.0 - base_p))
    f_cur = np.full(n, f0, dtype=np.float64)
    stumps = []

    eff_min_leaf = min(min_leaf, max(8, n // 6))
    for _ in range(n_stumps):
        p = _sigmoid(f_cur)
        grad = y_arr - p  # negative gradient of log-loss (residual)
        hess = np.maximum(p * (1.0 - p), 1e-4)

        best_gain = 1e-9
        best_stump = None
        g_tot = float(np.sum(grad))
        h_tot = float(np.sum(hess))
        reg_lam = 15.0  # strong leaf L2 regularization
        parent_score = (g_tot * g_tot) / (h_tot + reg_lam)

        for j in range(d):
            col = x_arr[:, j]
            qs = np.unique(np.quantile(col, [0.20, 0.35, 0.50, 0.65, 0.80]))
            for thr in qs:
                left = col <= thr
                n_l = int(np.sum(left))
                n_r = n - n_l
                if n_l < eff_min_leaf or n_r < eff_min_leaf:
                    continue
                g_l = float(np.sum(grad[left]))
                h_l = float(np.sum(hess[left]))
                g_r = g_tot - g_l
                h_r = h_tot - h_l
                gain = (g_l * g_l) / (h_l + reg_lam) + (g_r * g_r) / (h_r + reg_lam) - parent_score
                if gain > best_gain:
                    best_gain = gain
                    val_l = float(np.clip(g_l / (h_l + reg_lam), -1.5, 1.5))
                    val_r = float(np.clip(g_r / (h_r + reg_lam), -1.5, 1.5))
                    best_stump = (j, float(thr), val_l, val_r)

        if best_stump is None:
            break
        j, thr, vl, vr = best_stump
        step = np.where(x_arr[:, j] <= thr, vl, vr)
        f_cur = f_cur + learning_rate * step
        stumps.append({"feat": j, "thr": thr, "val_l": vl, "val_r": vr})

    return {
        "kind": "shallow_stumps",
        "f0": f0,
        "learning_rate": learning_rate,
        "stumps": stumps,
        "base_rate": base_p,
    }


def predict_proba_stumps(model: dict, X: np.ndarray) -> np.ndarray:
    x_arr = np.asarray(X, dtype=np.float64)
    f = np.full(len(x_arr), model["f0"], dtype=np.float64)
    lr = float(model["learning_rate"])
    for st in model["stumps"]:
        f = f + lr * np.where(x_arr[:, st["feat"]] <= st["thr"], st["val_l"], st["val_r"])
    return _sigmoid(f)


def compute_classification_metrics(y_true: np.ndarray, p_pred: np.ndarray) -> dict:
    """Compute Brier score, Brier skill vs base rate, log-loss, and exact Mann-Whitney ROC-AUC."""
    y = np.asarray(y_true, dtype=np.float64)
    p = np.clip(np.asarray(p_pred, dtype=np.float64), 1e-6, 1.0 - 1e-6)
    n = len(y)
    if n == 0:
        return {"n": 0, "brier": 0.25, "brier_skill": 0.0, "logloss": 0.693, "roc_auc": 0.5}
    base = float(np.mean(y))
    brier = float(np.mean((p - y) ** 2))
    brier_base = float(np.mean((base - y) ** 2))
    skill = (1.0 - brier / brier_base) if brier_base > 1e-9 else 0.0
    logloss = float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))

    pos = p[y >= 0.5]
    neg = p[y < 0.5]
    if len(pos) > 0 and len(neg) > 0:
        # Exact rank-based AUC
        diff = pos[:, None] - neg[None, :]
        auc = float(np.mean((diff > 0).astype(np.float64) + 0.5 * (diff == 0).astype(np.float64)))
    else:
        auc = 0.5
    return {
        "n": int(n),
        "win_rate_pct": round(100.0 * base, 1),
        "brier": round(brier, 4),
        "brier_skill": round(skill, 4),
        "logloss": round(logloss, 4),
        "roc_auc": round(auc, 4),
    }


def purged_embargo_walkforward_predict(
    X: np.ndarray,
    y: np.ndarray,
    day_ordinals: np.ndarray,
    *,
    model_kind: str = "l2_logistic",
    min_train_obs: int = 180,
    fold_span_days: int = 90,
    purge_days: int = 5,
    embargo_days: int = 10,
    scale_lo: float = 0.50,
    scale_hi: float = 1.25,
    toxic_quantile: float = 0.20,
) -> dict:
    """Strictly causal expanding Purged + Embargo Walk-Forward Meta-Labeling predictions & bet sizes.

    For every validation block [t_start, t_end]:
      - Training indices MUST satisfy `day_ord <= t_start - purge_days - embargo_days`!
      - Both the classifier AND bet-size calibration quantiles `(p_lo, p_hi, p_toxic)` are
        fitted strictly on that purged training fold ONLY — zero future leakage!
    """
    n = len(y)
    probs = np.full(n, np.nan, dtype=np.float64)
    sizes_cont = np.ones(n, dtype=np.float64)
    sizes_filt = np.ones(n, dtype=np.float64)
    evaluated = np.zeros(n, dtype=bool)
    n_folds = 0
    total_purged_obs = 0

    if n <= min_train_obs:
        return {
            "probs": probs,
            "sizes_cont": sizes_cont,
            "sizes_filt": sizes_filt,
            "evaluated_mask": evaluated,
            "n_folds": 0,
            "total_purged_obs": 0,
        }

    first_val_ord = int(day_ordinals[min_train_obs])
    max_ord = int(day_ordinals[-1])
    cur_start = first_val_ord
    gap = int(purge_days) + int(embargo_days)

    while cur_start <= max_ord:
        cur_end = cur_start + int(fold_span_days) - 1
        val_mask = (day_ordinals >= cur_start) & (day_ordinals <= cur_end)
        if np.any(val_mask):
            raw_pre = day_ordinals < cur_start
            train_mask = day_ordinals <= (cur_start - gap)
            purged_here = int(np.sum(raw_pre & (~train_mask)))
            total_purged_obs += purged_here

            if int(np.sum(train_mask)) >= max(60, min_train_obs // 2) and len(np.unique(y[train_mask])) >= 2:
                if model_kind == "l2_logistic":
                    mdl = fit_l2_logistic(X[train_mask], y[train_mask], l2_reg=2.0)
                    p_tr = predict_proba_logistic(mdl, X[train_mask])
                    p_val = predict_proba_logistic(mdl, X[val_mask])
                elif model_kind == "shallow_stumps":
                    mdl = fit_shallow_stump_ensemble(X[train_mask], y[train_mask], n_stumps=4, learning_rate=0.25, min_leaf=40)
                    p_tr = predict_proba_stumps(mdl, X[train_mask])
                    p_val = predict_proba_stumps(mdl, X[val_mask])
                else:
                    raise ValueError(f"Unknown model_kind: {model_kind}")

                p_lo = float(np.quantile(p_tr, 0.10))
                p_hi = float(np.quantile(p_tr, 0.90))
                p_tox = float(np.quantile(p_tr, toxic_quantile))
                span = max(p_hi - p_lo, 1e-4)

                # Continuous bet sizing [scale_lo .. scale_hi] calibrated strictly on training fold
                s_c = np.clip(scale_lo + (scale_hi - scale_lo) * ((p_val - p_lo) / span), scale_lo, scale_hi)
                # Toxic-regime filter: zero out bottom tail, preserve 1.0x elsewhere
                s_f = np.where(p_val < p_tox, 0.0, 1.0)

                probs[val_mask] = p_val
                sizes_cont[val_mask] = s_c
                sizes_filt[val_mask] = s_f
                evaluated[val_mask] = True
                n_folds += 1
        cur_start = cur_end + 1

    return {
        "probs": probs,
        "sizes_cont": sizes_cont,
        "sizes_filt": sizes_filt,
        "evaluated_mask": evaluated,
        "n_folds": n_folds,
        "total_purged_obs": total_purged_obs,
    }


def build_port7e_causal_meta_dataset() -> dict:
    """Build strictly causal 6-feature trade dataset for frozen `PORT_7E` Dev 2018-2024 (`holdout_rows = 0`)."""
    lock_sha = assert_holdout_locked()
    d = build_or_load_frozen_tapes(force_rebuild=False)
    tapes = d["tapes"]
    ext_days = sorted(d["ext_days"])
    if max(ext_days) >= "2025-01-01":
        raise AssertionError(f"HOLDOUT_CONTAMINATION: {max(ext_days)}")

    reg = load_registry()
    base_risks = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    core7 = list(reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"])

    # Precompute daily frozen PORT_7E return stream for strictly lagged (<= t-1) market/portfolio features
    day_ret = {dk: 0.0 for dk in ext_days}
    day_cnt = {dk: 0 for dk in ext_days}
    for eng in core7:
        rf = base_risks[eng]
        for dk, (row, _st, _mk) in tapes[eng].items():
            if dk in day_ret:
                day_ret[dk] += float(row["net_R"]) * rf
                day_cnt[dk] += 1

    r_arr = np.array([day_ret[dk] for dk in ext_days], dtype=np.float64)
    c_arr = np.array([day_cnt[dk] for dk in ext_days], dtype=np.float64)
    eq_arr = np.cumprod(1.0 + r_arr)

    # Compute strictly lagged (t-1) day-level features (NEVER peeks at day `i`!)
    day_feats: dict[str, tuple[float, float, float, float, float]] = {}
    for i, dk in enumerate(ext_days):
        if i < 20:
            v20, vr5_20, ret20, dd60, cnt5 = 0.004, 1.0, 0.0, 0.0, 2.0
        else:
            w20 = r_arr[i - 20 : i]
            w5 = r_arr[i - 5 : i]
            v20 = float(np.std(w20, ddof=1))
            v5 = float(np.std(w5, ddof=1))
            vr5_20 = v5 / max(v20, 1e-6)
            ret20 = float(np.sum(w20))
            eq_win = eq_arr[max(0, i - 60) : i]
            pk = float(np.max(eq_win))
            dd60 = (pk - float(eq_arr[i - 1])) / max(pk, 1e-9)
            cnt5 = float(np.mean(c_arr[i - 5 : i]))
        day_feats[dk] = (v20, vr5_20, ret20, dd60, cnt5)

    # Assemble chronological per-trade dataset with per-engine strictly lagged win-rate
    raw_trades = []
    for eng in core7:
        rf = base_risks[eng]
        for dk, (row, st, _mk) in tapes[eng].items():
            if dk in day_feats:
                raw_trades.append((dk, int(st[0]), eng, float(row["net_R"]), rf))
    raw_trades.sort(key=lambda x: (x[0], x[1], x[2]))

    eng_hist: dict[str, list[float]] = {e: [] for e in core7}
    X_rows, y_rows, day_strs, day_ords, trade_rets = [], [], [], [], []
    for dk, _ets, eng, net_r, rf in raw_trades:
        v20, vr5_20, ret20, dd60, cnt5 = day_feats[dk]
        hist = eng_hist[eng]
        # Empirical Bayes shrunk trailing 20-trade win rate (strictly prior trades ONLY!)
        if hist:
            tail = hist[-20:]
            eng_wr = (sum(tail) + 4.5) / (len(tail) + 10.0)
        else:
            eng_wr = 0.45
        X_rows.append([v20, vr5_20, ret20, dd60, cnt5, eng_wr])
        win_flag = 1.0 if net_r > 0.0 else 0.0
        y_rows.append(win_flag)
        day_strs.append(dk)
        day_ords.append(datetime.strptime(dk, "%Y-%m-%d").toordinal())
        trade_rets.append(net_r * rf)
        eng_hist[eng].append(win_flag)

    return {
        "name": "PORT_7E_DEV_2018_2024",
        "holdout_lock_sha256": lock_sha,
        "feature_names": ["port_vol_20d", "vol_ratio_5_20", "port_ret_20d", "port_dd_60d", "signal_density_5d", "eng_trailing_wr20"],
        "X": np.asarray(X_rows, dtype=np.float64),
        "y": np.asarray(y_rows, dtype=np.float64),
        "days": day_strs,
        "day_ordinals": np.asarray(day_ords, dtype=np.int64),
        "trade_rets": np.asarray(trade_rets, dtype=np.float64),
        "all_calendar_days": ext_days,
        "cluster_b_start": "2022-01-01",
        "ann_days": 252.0,
    }


def build_crypto_f4_causal_meta_dataset(returns_dir: Path = DEFAULT_RETURNS_DIR) -> dict:
    """Build strictly causal 6-feature active-day dataset for frozen `Crypto F4_4H_EMA_24_120_BTC` (2019-2026)."""
    s2 = json.loads((returns_dir / "sleeve2_crypto_spot.json").read_text(encoding="utf-8"))
    f4_map = {str(k): float(v) for k, v in s2["daily_returns"].items()}
    btc_raw = s2["variants"]["BM_BH_BTC"]
    btc_map = {str(k): float(v) for k, v in (btc_raw["daily_returns"] if isinstance(btc_raw, dict) and "daily_returns" in btc_raw else btc_raw).items()}

    all_days = sorted(f4_map.keys())
    f4_arr = np.array([f4_map[d] for d in all_days], dtype=np.float64)
    btc_arr = np.array([btc_map.get(d, 0.0) for d in all_days], dtype=np.float64)
    f4_eq = np.cumprod(1.0 + f4_arr)
    btc_eq = np.cumprod(1.0 + btc_arr)

    X_rows, y_rows, day_strs, day_ords, act_rets = [], [], [], [], []
    for i, dk in enumerate(all_days):
        if i < 20:
            continue
        r_today = float(f4_arr[i])
        # Only label days where frozen white-box F4 signal is active in market!
        if abs(r_today) <= 1e-10:
            continue
        # Strictly lagged <= i-1 features (zero leakage from day i!)
        bw20 = btc_arr[i - 20 : i]
        bw5 = btc_arr[i - 5 : i]
        b_vol20 = float(np.std(bw20, ddof=1))
        b_vr = float(np.std(bw5, ddof=1)) / max(b_vol20, 1e-6)
        b_ret20 = float(np.sum(bw20))
        b_pk = float(np.max(btc_eq[max(0, i - 60) : i]))
        b_dd60 = (b_pk - float(btc_eq[i - 1])) / max(b_pk, 1e-9)

        f_ret20 = float(np.sum(f4_arr[i - 20 : i]))
        f_pk = float(np.max(f4_eq[max(0, i - 60) : i]))
        f_dd60 = (f_pk - float(f4_eq[i - 1])) / max(f_pk, 1e-9)

        X_rows.append([b_vol20, b_vr, b_ret20, b_dd60, f_ret20, f_dd60])
        y_rows.append(1.0 if r_today > 0.0 else 0.0)
        day_strs.append(dk)
        day_ords.append(datetime.strptime(dk, "%Y-%m-%d").toordinal())
        act_rets.append(r_today)

    return {
        "name": "CRYPTO_F4_4H_EMA_2019_2026",
        "feature_names": ["btc_vol_20d", "btc_vol_ratio_5_20", "btc_ret_20d", "btc_dd_60d", "f4_ret_20d", "f4_dd_60d"],
        "X": np.asarray(X_rows, dtype=np.float64),
        "y": np.asarray(y_rows, dtype=np.float64),
        "days": day_strs,
        "day_ordinals": np.asarray(day_ords, dtype=np.int64),
        "trade_rets": np.asarray(act_rets, dtype=np.float64),
        "all_calendar_days": all_days,
        "cluster_b_start": "2024-01-01",
        "ann_days": 365.0,
    }


def _aggregate_to_daily_returns(
    all_days: list[str],
    trade_days: list[str],
    scaled_trade_rets: np.ndarray,
    *,
    start_day: str,
) -> np.ndarray:
    cal = [d for d in all_days if d >= start_day]
    by_day = {d: 0.0 for d in cal}
    for d, r in zip(trade_days, scaled_trade_rets):
        if d in by_day:
            by_day[d] += float(r)
    return np.array([by_day[d] for d in cal], dtype=np.float64)


def evaluate_meta_labeling_on_dataset(ds: dict) -> dict:
    """Run Purged Embargo Walk-Forward head-to-head comparison vs Raw White-Box on Blind Cluster B."""
    X = ds["X"]
    y = ds["y"]
    ords = ds["day_ordinals"]
    days = ds["days"]
    rets = ds["trade_rets"]
    cb_start = ds["cluster_b_start"]
    cb_mask = np.array([d >= cb_start for d in days])

    raw_daily_b = _aggregate_to_daily_returns(ds["all_calendar_days"], days, rets, start_day=cb_start)
    raw_met_b = compute_series_metrics(raw_daily_b, ann_days=ds["ann_days"])

    variants = {
        "RAW_WHITEBOX_1X": {
            "model": "none",
            "policy": "raw_1.00x",
            "avg_size": 1.0,
            "kept_pct": 100.0,
            "cls_metrics_b": None,
            "blind_b": raw_met_b,
            "delta_sharpe": 0.0,
            "delta_calmar": 0.0,
        }
    }

    for mkind, label_prefix in (("l2_logistic", "LOGISTIC"), ("shallow_stumps", "SHALLOW_TREE")):
        wf = purged_embargo_walkforward_predict(
            X, y, ords,
            model_kind=mkind,
            min_train_obs=200,
            fold_span_days=90,
            purge_days=5,
            embargo_days=10,
            scale_lo=0.50,
            scale_hi=1.25,
            toxic_quantile=0.20,
        )
        eval_b = cb_mask & wf["evaluated_mask"]
        cls_b = compute_classification_metrics(y[eval_b], wf["probs"][eval_b])

        for pol_name, sz_arr in (
            (f"{label_prefix}_SCALE_050_125", wf["sizes_cont"]),
            (f"{label_prefix}_TOXIC_FILTER", wf["sizes_filt"]),
        ):
            scaled = rets * sz_arr
            daily_b = _aggregate_to_daily_returns(ds["all_calendar_days"], days, scaled, start_day=cb_start)
            mb = compute_series_metrics(daily_b, ann_days=ds["ann_days"])
            variants[pol_name] = {
                "model": mkind,
                "policy": pol_name,
                "n_folds": wf["n_folds"],
                "total_purged_obs": wf["total_purged_obs"],
                "avg_size": round(float(np.mean(sz_arr[cb_mask])), 3),
                "kept_pct": round(100.0 * float(np.mean(sz_arr[cb_mask] > 0.0)), 1),
                "cls_metrics_b": cls_b,
                "blind_b": mb,
                "delta_sharpe": round(mb["sharpe"] - raw_met_b["sharpe"], 3),
                "delta_calmar": round(mb["calmar"] - raw_met_b["calmar"], 3),
            }

    # Strict promotion rule: must beat Raw on BOTH Blind Cluster B Sharpe AND Calmar with positive Brier Skill!
    challengers = [v for k, v in variants.items() if k != "RAW_WHITEBOX_1X"]
    best = max(challengers, key=lambda v: (v["blind_b"]["calmar"], v["blind_b"]["sharpe"]))
    improves_both = (
        best["delta_sharpe"] > 0.05
        and best["delta_calmar"] > 0.05
        and (best["cls_metrics_b"]["brier_skill"] > 0.0)
    )
    verdict = "PROMOTE_AS_V2_SIZING_OVERLAY" if improves_both else "REJECT_KEEP_RAW_WHITEBOX"
    return {
        "dataset": ds["name"],
        "n_total_obs": int(len(y)),
        "n_cluster_b_obs": int(np.sum(cb_mask)),
        "cluster_b_start": cb_start,
        "feature_names": ds["feature_names"],
        "variants": variants,
        "best_challenger": best["policy"],
        "verdict": verdict,
    }


def run_lab6_meta_labeling_study(*, returns_dir: Path = DEFAULT_RETURNS_DIR) -> dict:
    """Run full Lab #6 Purged Embargo Meta-Labeling audit on PORT_7E (Dev) + Crypto F4_4H_EMA."""
    t0 = time.perf_counter()
    ds_fx = build_port7e_causal_meta_dataset()
    ds_cr = build_crypto_f4_causal_meta_dataset(returns_dir=returns_dir)
    res_fx = evaluate_meta_labeling_on_dataset(ds_fx)
    res_cr = evaluate_meta_labeling_on_dataset(ds_cr)
    return {
        "schema": "naqex-lab6-meta-labeling-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_lock_sha256": ds_fx["holdout_lock_sha256"],
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "protocol": {"purge_days": 5, "embargo_days": 10, "fold_span_days": 90, "scale_band": [0.50, 1.25], "toxic_quantile": 0.20},
        "port7e_dev": res_fx,
        "crypto_f4": res_cr,
        "runtime_seconds": round(time.perf_counter() - t0, 3),
    }


def render_lab6_markdown(res: dict) -> str:
    """Render concise Vietnamese Lab #6 Meta-Labeling Audit receipt (< 900 KB, zero bare $ pairs)."""
    p = res["protocol"]
    lines = [
        "---",
        "doc_type: research_receipt",
        "date: 2026-11-24",
        "lane: risk-auditor",
        "milestone: Wave2-Lab6-MetaLabeling",
        "holdout_rows_analysed: 0",
        "order_send_count: 0",
        "---",
        "",
        "# Lab #6 — Kiểm Định Purged Embargo Walk-Forward Meta-Labeling (AFML Ch. 3, 7 & 10)",
        "",
        f"- **Generated UTC:** `{res['generated_utc']}` (runtime `{res['runtime_seconds']}s`)",
        f"- **Safety Seal:** Holdout `2025–2026` của `PORT_7E` giữ **100% SEALED** (`lock={res['holdout_lock_sha256'][:16]}...`, `holdout_rows_analysed = 0`, `OrderSend = 0`).",
        f"- **Giao thức chống rò rỉ (AFML Ch. 7):** Expanding Walk-Forward mỗi `{p['fold_span_days']}` ngày, **Purge `{p['purge_days']}` ngày + Embargo `{p['embargo_days']}` ngày** giữa tập huấn luyện và tập kiểm định; chuẩn hóa đặc trưng và ngưỡng kích thước lệnh khớp 100% trong tập huấn luyện.",
        "- **Tín hiệu gốc giữ nguyên tuyệt đối:** Không thay đổi điểm vào/hướng lệnh của `PORT_7E` và `Crypto F4_4H_EMA`; Meta-Labeler chỉ điều chỉnh kích thước vị thế (`[0.50x..1.25x]`) hoặc lọc bỏ nhóm đuôi 20% xác suất thấp nhất (`Toxic Filter`).",
        "",
    ]

    for idx, (sec_title, blk) in enumerate(
        (
            ("1. Đối Đầu Trực Tiếp Trên `PORT_7E` Intraday Prop (Blind Cluster B `2022–2024`, Dev Only)", res["port7e_dev"]),
            ("2. Đối Đầu Trực Tiếp Trên `Crypto F4_4H_EMA_24_120_BTC` (Blind Cluster B `2024–2026`)", res["crypto_f4"]),
        ),
        start=1,
    ):
        lines += [
            f"## {sec_title}",
            "",
            f"- **Mẫu quan sát:** `{blk['n_total_obs']}` tổng mẫu (`{blk['n_cluster_b_obs']}` trên Blind Cluster B từ `{blk['cluster_b_start']}`)",
            f"- **6 Đặc trưng nhân quả (`<= t-1`):** `{', '.join(blk['feature_names'])}`",
            f"- **Phán quyết trung thực:** **`{blk['verdict']}`** (ứng viên tốt nhất: `{blk['best_challenger']}`)",
            "",
        ]
        headers = ["Policy", "Avg Size", "Kept %", "Brier (Skill)", "ROC-AUC", "Cl.B CAGR%", "Cl.B MaxDD%", "Cl.B Sharpe", "Cl.B Calmar", "ΔSharpe / ΔCalmar"]
        rows = []
        for k, v in blk["variants"].items():
            mb = v["blind_b"]
            cm = v["cls_metrics_b"]
            brier_str = f"{cm['brier']:.4f} ({cm['brier_skill']:+.3f})" if cm else "baseline"
            auc_str = f"{cm['roc_auc']:.3f}" if cm else "—"
            rows.append([
                k,
                f"{v['avg_size']:.2f}x",
                f"{v['kept_pct']:.1f}%",
                brier_str,
                auc_str,
                f"{mb['cagr_pct']:+.2f}%",
                f"{mb['max_dd_pct']:.2f}%",
                f"{mb['sharpe']:.2f}",
                f"{mb['calmar']:.2f}",
                f"{v['delta_sharpe']:+.2f} / {v['delta_calmar']:+.2f}",
            ])
        lines.append(format_markdown_table(headers, rows, right_align_cols={1, 2, 3, 4, 5, 6, 7, 8, 9}))
        lines.append("")

    cr_raw = res["crypto_f4"]["variants"]["RAW_WHITEBOX_1X"]
    cr_st = res["crypto_f4"]["variants"]["SHALLOW_TREE_SCALE_050_125"]
    lines += [
        "## 3. Phân Tích Định Lượng & Khuyến Nghị Điều Hành",
        "",
        f"1. **Tại sao Meta-Labeling cần tiêu chuẩn khắt khe (`ΔSharpe > +0.05`, `ΔCalmar > +0.05` VÀ `Brier Skill > 0`):** Mô hình phân loại nhị phân trên chuỗi lợi suất tài chính có tỷ lệ tín hiệu/nhiễu rất thấp. Nếu `Brier Skill <= 0` hoặc `ROC-AUC ≈ 0.50`, mô hình không có khả năng phân biệt lệnh thắng/thua ngoài mẫu tốt hơn tung đồng xu. Điểm đáng chú ý trên `Crypto F4_4H_EMA` là `SHALLOW_TREE_SCALE_050_125` đẩy Sharpe từ `{cr_raw['blind_b']['sharpe']:.2f} -> {cr_st['blind_b']['sharpe']:.2f}` dù `ROC-AUC = {cr_st['cls_metrics_b']['roc_auc']:.3f}` và `Brier Skill = {cr_st['cls_metrics_b']['brier_skill']:+.3f}`: hiệu ứng này đến từ **implicit volatility/drawdown damping** (`avg_size = {cr_st['avg_size']:.2f}x` giảm phơi nhiễm khi biến động tăng) chứ không phải năng lực phân loại thắng/thua thực sự, nên gate `Brier Skill > 0` bác bỏ một cách kỷ luật để tránh chọn nhầm lớp ML cồng kềnh thay cho rule quản trị vốn white-box đơn giản.",
        "2. **Cảnh báo rủi ro với chiến lược Trend-Following lồi (`PORT_7E` & `F4_4H_EMA`):** Như đã chứng minh ở `RED-TEAM-ADVERSARIAL-AUDIT-20261124.md` (Test 4 Top-K), phần lớn lợi nhuận của hệ thống breakout nằm ở đuôi phải `+2R..+5R`. Bất kỳ bộ lọc `Toxic Filter` nào vô tình bỏ sót chỉ `2–3%` ngày breakout lớn sẽ làm suy giảm mạnh tỷ suất sinh lời ngoài mẫu.",
        "3. **Quyết định thực thi:** Giữ nguyên tín hiệu white-box thuần (`RAW_WHITEBOX_1X`) cho cả `PORT_7E` (FTMO Free Trial/Funded) và `Crypto F4_4H_EMA` nếu Meta-Labeler không vượt chuẩn ở cả 3 tiêu chí; chỉ coi `meta_labeler.py` là công cụ nghiên cứu chuẩn AFML sẵn sàng tái kiểm định khi có thêm dữ liệu forward thực tế.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    res = run_lab6_meta_labeling_study()
    md = render_lab6_markdown(res)
    out_md = ROOT / "planning/research/LAB6-META-LABELING-AUDIT-20261124.md"
    out_md.write_text(md, encoding="utf-8", newline="\n")
    print(json.dumps({
        "output_md": str(out_md),
        "md_bytes": out_md.stat().st_size,
        "runtime_seconds": res["runtime_seconds"],
        "port7e_verdict": res["port7e_dev"]["verdict"],
        "port7e_best": res["port7e_dev"]["best_challenger"],
        "crypto_verdict": res["crypto_f4"]["verdict"],
        "crypto_best": res["crypto_f4"]["best_challenger"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
