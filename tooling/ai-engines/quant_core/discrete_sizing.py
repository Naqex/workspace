"""Certify a bounded sizing grid without assuming drawdown is monotone."""
import hashlib
import numpy as np


def quantity_grid(ticks, denominators, risk_milli):
    ticks = np.asarray(ticks, dtype=np.int64)
    denominators = np.asarray(denominators, dtype=np.int64)
    risk_milli = np.asarray(risk_milli, dtype=np.int64)
    if (np.any(ticks <= 0) or np.any(denominators <= 0) or
            denominators.shape != risk_milli.shape or np.any(risk_milli <= 0)):
        raise ValueError("INVALID_QUANTITY_GRID")
    # c=tick/1e6; flooring risk to milli-USD then lot units gives this same quotient.
    return (ticks[:, None] * risk_milli) // (1_000_000 * denominators)


def largest_feasible(ticks, quantities, measure, accepts):
    """Bisection probes plus every distinct lot-vector plateau, including re-entry."""
    ticks = np.asarray(ticks)
    if len(ticks) != len(quantities) or len(ticks) == 0 or np.any(np.diff(ticks) != 1):
        raise ValueError("CONTIGUOUS_REGISTERED_GRID_REQUIRED")
    cache, probes = {}, []

    def evaluate(index):
        vector = quantities[index]
        key = vector.tobytes()
        if key not in cache:
            metrics = measure(int(ticks[index]), vector)
            cache[key] = dict(measured_tick=int(ticks[index]),
                              quantity_sha256=hashlib.sha256(key).hexdigest(),
                              metrics=metrics, feasible=bool(accepts(metrics)))
        return cache[key]

    low, high = 0, len(ticks)-1
    while high-low > 1:
        middle = (low+high)//2
        row = evaluate(middle)
        probes.append(dict(tick=int(ticks[middle]), feasible=row["feasible"]))
        if row["feasible"]:
            low = middle
        else:
            high = middle
    # Feasibility can return after an infeasible lot jump. Inspect every plateau.
    last = {row.tobytes(): i for i, row in enumerate(quantities)}
    feasible = [i for i in last.values() if evaluate(i)["feasible"]]
    chosen = max(feasible) if feasible else None
    return dict(tick=int(ticks[chosen]) if chosen is not None else None,
                selected=evaluate(chosen) if chosen is not None else None,
                grid_points=len(ticks), unique_vectors=len(last),
                bisection_probes=probes, evaluations=list(cache.values()),
                all_grid_plateaus_checked=True, monotonicity_assumed=False)
