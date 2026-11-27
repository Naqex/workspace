"""Bounded cushion arithmetic and censored first-passage summaries."""

from decimal import ROUND_FLOOR, Decimal
from math import isfinite
from statistics import mean, median


def state_geometry(return_fraction, target=0.10, static_buffer=0.10):
    s, t, b = map(lambda v: Decimal(str(v)), (return_fraction, target, static_buffer))
    if b <= 0 or s <= -b or s <= -1 or t < 0:
        raise ValueError("state_outside_surviving_static_account")
    gap = max(Decimal(0), t - s)
    return dict(
        account_return_pct=float(s * 100),
        remaining_buffer_pct=float((b + s) * 100),
        remaining_buffer_ROI_required_pct=float(gap / (b + s) * 100),
        current_equity_ROI_to_target_pct=float(gap / (1 + s) * 100),
        current_equity_ROI_to_recover_pct=float(max(Decimal(0), -s) / (1 + s) * 100),
    )


def cushion_risk(phase, equity_milli, balance_milli, gamma, weight=1):
    if phase not in (1, 2, 3) or gamma not in (0.35, 0.5) or not 0.25 <= weight <= 2:
        raise ValueError("unregistered_cushion_policy")
    base = (Decimal(300), Decimal("262.5"), Decimal("187.5"))[phase - 1]
    ratio = min(Decimal(1), max(Decimal(0), Decimal(equity_milli - 45000000) / 5000000))
    bonus = min(Decimal(max(0, balance_milli - 50000000)) / 10000, base) if phase < 3 else Decimal(0)
    value = (base * ratio ** Decimal(str(gamma)) + bonus) * Decimal(str(weight))
    return float(value.quantize(Decimal(".01"), rounding=ROUND_FLOOR))


def first_passage_summary(months, horizon_months, failures=0):
    if horizon_months <= 0 or not months or not 0 <= failures <= len(months):
        raise ValueError("first_passage_sample_contract")
    hits = [float(v) for v in months if v is not None]
    if any(not isfinite(v) or not 0 <= v <= horizon_months for v in hits):
        raise ValueError("first_passage_outside_horizon")
    return dict(
        paths=len(months),
        target_hits=len(hits),
        hit_pct=100 * len(hits) / len(months),
        failures=failures,
        unresolved_or_nonhit=len(months) - len(hits),
        conditional_mean_months=mean(hits) if hits else None,
        conditional_median_months=median(hits) if hits else None,
        restricted_mean_months=mean(v if v is not None else horizon_months for v in months),
        restriction_months=horizon_months,
        unconditional_expected_months=None,
        interpretation="Nonhit/breached paths retain horizon cost; no finite unconditional mean inferred.",
    )


def inverse_volatility_weights(daily_pnl):
    import numpy as np

    x = np.asarray(daily_pnl, dtype=float)
    if x.ndim != 2 or x.shape[1] != 3 or len(x) < 100 or not np.isfinite(x).all():
        raise ValueError("three_sleeve_daily_book_required")
    mu, sigma = x.mean(axis=0), x.std(axis=0, ddof=1)
    cov = np.cov(x, rowvar=False)
    if np.any(sigma <= 0) or mu.sum() <= 0:
        return dict(eligible=False, reason="NONPOSITIVE_MEAN_OR_ZERO_VOL", means=mu.tolist())
    raw = 3 / sigma / (1 / sigma).sum()
    denom = raw @ mu
    if denom <= 0:
        return dict(eligible=False, reason="INVERSE_VOL_NONPOSITIVE_MEAN")
    weights = raw * (mu.sum() / denom)
    return dict(
        eligible=bool(np.all((weights >= 0.25) & (weights <= 2))),
        reason="FIXED_BOUNDS" if np.any((weights < 0.25) | (weights > 2)) else "ELIGIBLE",
        weights=weights.tolist(),
        means=mu.tolist(),
        covariance=cov.tolist(),
        equal_mean=float(mu.sum()),
        weighted_mean=float(weights @ mu),
        equal_variance=float(np.ones(3) @ cov @ np.ones(3)),
        weighted_variance=float(weights @ cov @ weights),
        objective="mean-matched inverse volatility; not claimed to be global covariance optimum",
        unit_book_only=True,
    )


def volatility_drag(daily_fractional_returns, sessions_per_year=252):
    import numpy as np

    x = np.asarray(daily_fractional_returns, dtype=float)
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all():
        raise ValueError("finite_fractional_daily_returns_required")
    variance = float(x.var(ddof=1))
    return dict(
        daily_variance=variance,
        approximate_daily_log_drag=0.5 * variance,
        approximate_annual_log_drag=0.5 * variance * sessions_per_year,
        sessions_per_year=sessions_per_year,
        approximation_not_exact_growth=True,
    )
