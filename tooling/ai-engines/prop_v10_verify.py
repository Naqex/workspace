"""Audit persisted V10 endpoints with rational arithmetic; benchmark signal parity."""
import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from math import erfc, sqrt
from pathlib import Path
from statistics import median
import subprocess
import time
import numpy as np

from prop_v10_source import JOB, FIRST, END, sources, sha
from prop_v10_signals import recipes
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.vectorized_stage0_scanner import measure, summaries

BASE = "5d8cd61a054c5d8584f05bef1ef6d7d2ce347906"
DAY, HOUR = 86400000, 3600000


def save(name, value):
    target = JOB / name
    if target.exists():
        raise ValueError("preserve_verification_attempt:" + name)
    target.write_text(json.dumps(value, indent=2), encoding="utf-8")


def snapshot():
    registration = json.loads((JOB / "discovery-registration.json").read_text())
    target = JOB / "original-source"
    target.mkdir(exist_ok=True)
    evidence = {}
    for path, digest in registration["pins"].items():
        rel = Path(path)
        if rel.is_absolute():
            rel = rel.relative_to(Path.cwd())
        raw = subprocess.check_output(["git", "show", f"{BASE}:{rel.as_posix()}"])
        choices = [raw, raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")]
        original = next((b for b in choices if hashlib.sha256(b).hexdigest() == digest), None)
        if original is None:
            raise ValueError("original_source_pin_unrecoverable:" + str(rel))
        out = target / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists() and out.read_bytes() != original:
            raise ValueError("snapshot_changed")
        out.write_bytes(original)
        evidence[str(rel)] = dict(path=str(out), sha256=digest)
    return evidence


def oracle():
    """No producer endpoint/cost/funding/statistical helpers in the scalar oracle."""
    start = time.perf_counter()
    pins = snapshot()
    original = json.loads((JOB / "discovery.json").read_text())
    store, source = np.load(JOB / "raw-matrix-reviewed.npz"), sources()
    source_times = {asset: bars["t"].tolist() for asset, bars in source.items()}
    calendar = gold_calendar(FIRST, END)
    # Schedule is an admitted input, not an independently certified broker calendar.
    flats = sorted(set(calendar.times))
    rollover = []
    for day in range(FIRST // DAY - 1, END // DAY + 1):
        weekday = (day + 3) % 7
        if weekday < 5:
            rollover.append((day * DAY + 22 * HOUR, 3 if weekday == 2 else 1))
    weekdays = [d for d in range(FIRST // DAY, END // DAY) if (d+3) % 7 < 5]
    event_times = [t for t, _ in rollover]
    accrued = [0]
    for _, weight in rollover:
        accrued.append(accrued[-1] + weight)
    day_index = {d: i for i, d in enumerate(weekdays)}
    measurements, daily_check, financial_rows = [], [], 0
    max_error = 0.
    for j, saved in enumerate(original["rows"]):
        get = lambda field: store[f"{j}:{field}"]
        m = {k: get(k) for k in ("at", "entry_at", "exit_at", "deadline", "side",
             "entry_price", "exit_price", "stop", "natural", "friction", "ratio",
             "ok", "admitted", "years")}
        m.update({k: saved[k] for k in ("asset", "recipe", "family", "horizon")})
        m["model"] = {mname: {f: get(f"{mname}:{f}") for f in
                       ("gross", "commission", "funding", "funding_multipliers", "net", "net_R")}
                      for mname in ("SYM", "ASYM")}
        bars = source[m["asset"]]
        times = source_times[m["asset"]]
        scale = 1000 if m["asset"] == "XAUUSD" else 100000
        daily = [0.] * len(weekdays)
        for i, decision in enumerate(m["at"]):
            entry_i = bisect_left(times, int(decision))
            entry = int(times[min(entry_i, len(times)-1)])
            horizon = m["horizon"]
            flat = flats[bisect_right(flats, entry)]
            wanted = (entry // DAY * DAY + 20*HOUR + HOUR//2 if horizon == "DAY"
                      else entry + int(horizon[:-1])*HOUR if horizon != "FRIDAY" else flat)
            deadline = min(flat, wanted)
            exit_i = bisect_left(times, deadline)
            exit_i_safe = min(exit_i, len(times)-1)
            exit_at = times[exit_i_safe]
            side = int(m["side"][i])
            p0 = int(bars["ao" if side == 1 else "bo"][min(entry_i, len(times)-1)])
            px = int(bars["bo" if side == 1 else "ao"][exit_i_safe])
            natural = F(side * (p0 - int(m["stop"][i])), scale)
            ok = (entry_i < len(times) and entry-decision <= 60000 and
                  exit_i < len(times) and 0 <= exit_at-deadline <= 60000 and
                  deadline < END and FIRST <= decision < END and natural > 0 and
                  deadline >= entry and exit_at >= entry and
                  not ((entry//DAY+3)%7 == 4 and entry%DAY >= 20*HOUR+HOUR//2))
            assert bool(m["ok"][i]) == ok
            assert (entry, exit_at, p0, px, deadline) == tuple(
                int(m[k][i]) for k in ("entry_at", "exit_at", "entry_price", "exit_price", "deadline"))
            if not ok:
                continue
            multipliers = accrued[bisect_right(event_times, exit_at)] - accrued[bisect_right(event_times, entry)]
            gross = F(side * (px-p0), scale)
            if scale == 1000:
                # cents at 100oz reference lot; explicit rational half-up.
                def leg(price):
                    cents = F(price, scale) * 100 * F(7, 1000000) * 100
                    rounded = (2*cents.numerator + cents.denominator) // (2*cents.denominator)
                    return F(rounded, 10000)
                fee, other = leg(p0) + leg(px), F(2, 5)
            else:
                fee, other = F(0), F(9, 100000)
            for model in ("SYM", "ASYM"):
                rate = (F(-2, 5) if model == "SYM" else
                        F(-45 if side == 1 else -5, 100)) if scale == 1000 else F(-4, 10000)
                funding = rate * multipliers
                net = gross-fee-other+funding
                expected = dict(gross=gross, commission=fee, funding=funding,
                                funding_multipliers=multipliers, net=net, net_R=net/natural)
                for field, value in expected.items():
                    error = abs(float(value) - float(m["model"][model][field][i]))
                    max_error = max(max_error, error)
                    if error > 1e-9:
                        raise AssertionError((j, i, model, field, error))
                if model == "SYM":
                    daily[day_index[int(decision)//DAY]] += float(net/natural)
            financial_rows += 1
        measurements.append(m)
        daily_check.append(daily)
    revised, daily = summaries(measurements, FIRST, END, 544)
    np.testing.assert_allclose(daily, daily_check, rtol=1e-10, atol=1e-9)
    p_values = []
    for i, x in enumerate(daily_check):
        n = len(x)
        mu = sum(x)/n
        c = [v-mu for v in x]
        v0 = sum(v*v for v in c)/n
        variance = v0 + sum(2*(1-lag/6)*sum(c[k]*c[k-lag] for k in range(lag,n))/n
                            for lag in range(1,6))
        variance = max(variance, v0*1e-6)
        t = mu/sqrt(variance/n) if variance > 0 else 0.
        p = .5*erfc(t/sqrt(2))
        assert abs(t-revised[i]["statistics"]["t_stat"]) < 1e-9
        p_values.append(p)
    running = 0.
    for rank, i in enumerate(sorted(range(544), key=lambda k: p_values[k])):
        running = min(1., max(running, p_values[i]*(544-rank)))
        assert abs(running-revised[i]["statistics"]["p_holm"]) < 1e-9
    # Independently reconcile the clustered economic gate from the persisted raw arrays.
    for m, row in zip(measurements, revised):
        reasons = []
        for cluster in row["clusters"]:
            years = cluster["years"]
            raw = np.isin(m["years"], years)
            ok, admitted = raw & m["ok"], raw & m["admitted"]
            scale_ratio = median(m["friction"][ok])/median(m["natural"][ok]) if ok.any() else None
            assert scale_ratio == cluster["scale_ratio"]
            if not raw.any() or sum(admitted)/sum(raw) < .6:
                reasons.append(f"{years[0]}:RETENTION")
            if sum(admitted) < 60:
                reasons.append(f"{years[0]}:CADENCE")
            if sum(ok) != sum(raw):
                reasons.append(f"{years[0]}:ENDPOINT")
            if scale_ratio is None or scale_ratio > .15:
                reasons.append(f"{years[0]}:SCALE")
            for model in ("SYM", "ASYM"):
                values = m["model"][model]["net_R"]
                if min(sum(values[ok]), sum(values[admitted])) <= 0:
                    reasons.append(f"{years[0]}:{model}:CLUSTER_ECONOMIC")
        for model in ("SYM", "ASYM"):
            values = m["model"][model]["net_R"]
            if sum(sum(values[(m["years"] == y) & m["ok"]]) > 0 for y in range(2018,2024)) < 4:
                reasons.append(model + ":FEWER_THAN_4_POSITIVE_YEARS")
        assert sorted(reasons) == sorted(r for r in row["reasons"] if r not in
                ("HOLM_MULTIPLE_TESTING", "DEFLATED_SHARPE_PROXY"))
    ranked = sorted(revised, key=lambda r: (r["score"], sum(c["net"]["SYM"]["raw"] for c in r["clusters"])),
                    reverse=True)
    changes = [dict(index=i, before=a["reasons"], after=b["reasons"])
               for i, (a,b) in enumerate(zip(original["rows"], revised)) if a["reasons"] != b["reasons"]]
    save("discovery-reviewed.json", dict(original, rows=revised, top15=ranked[:15],
        eligible=[r for r in revised if r["eligible"]], economics_pass=sum(r["economic_gate"] for r in revised),
        technical_delta="Cluster pooled medians; reject backward DAY exit and post-Friday-flat entry; original retained.",
        original_sha256=sha(JOB/"discovery.json")))
    receipt = dict(passed=True, configurations=544, rational_priced_rows=financial_rows,
        financial_cost_views=financial_rows*2, max_abs_error=max_error, seconds=time.perf_counter()-start,
        original_source=pins, changed_gate_rows=changes,
        original_discovery_sha256=sha(JOB/"discovery.json"),
        reviewed_matrix_sha256=sha(JOB/"raw-matrix-reviewed.npz"),
        revised_discovery_sha256=sha(JOB/"discovery-reviewed.json"),
        rank_top15_unchanged=[(r["asset"],r["recipe"],r["horizon"]) for r in ranked[:15]] ==
                            [(r["asset"],r["recipe"],r["horizon"]) for r in original["top15"]],
        eligible=sum(r["eligible"] for r in revised), economic_gate=sum(r["economic_gate"] for r in revised),
        coverage="All priced endpoints/quotes/Fraction fees/funding/netR; daily HAC/Holm; annual sums and gates.",
        limitations=["same implementer, different arithmetic; no independent person review",
                     "calendar is shared admitted input; no broker verification",
                     "DSR proxy formula source-reviewed, not independently certified DSR"])
    save("oracle.json", receipt)
    save("postpersist-failure.json", dict(
        original_numeric_artifacts_preserved=True, original_run_exit_success=False,
        failure="TypeError duplicate stage keyword only in final stdout after persistence",
        corrected_terminal_event_regression=True, financial_rescan=False))
    print({k:v for k,v in receipt.items() if k not in ("original_source","changed_gate_rows")}, flush=True)


def remeasure():
    snapshot()
    save("technical-correction-registration.json", dict(
        original_commit=BASE, original_matrix_sha256=sha(JOB/"raw-matrix.npz"),
        scanner_sha256=sha(Path(__file__).with_name("quant_core")/"vectorized_stage0_scanner.py"),
        trials=544, signals="exact persisted raw-signals.json; no new signal recipes or thresholds",
        changes=["Reject DAY exits before entry", "Reject entries at/after Friday20:30",
                 "Pooled cluster scale medians, not worst annual median"],
        discovered_by="Fraction oracle funding discrepancy on j96/i60; negative holding period",
        validation_prices_opened=False))
    raw = json.loads((JOB/"raw-signals.json").read_text())
    data, cal, packed, j = sources(), gold_calendar(FIRST,END), {}, 0
    for asset, recipes_ in raw.items():
        for r in recipes_:
            for key in ("at","side","stop"):
                r[key] = np.array(r[key], dtype="int64")
            for m in measure(asset,r,data[asset],cal,FIRST,END):
                for field in ("at","entry_at","exit_at","deadline","side","entry_price","exit_price",
                              "stop","natural","friction","ratio","ok","admitted","years"):
                    packed[f"{j}:{field}"] = m[field]
                for model in ("SYM","ASYM"):
                    for field in ("gross","commission","funding","funding_multipliers","net","net_R"):
                        packed[f"{j}:{model}:{field}"] = m["model"][model][field]
                j += 1
    assert j == 544
    old = np.load(JOB/"raw-matrix.npz")
    differences = []
    for i in range(544):
        for field in ("at","side","stop","entry_price","exit_price","deadline"):
            np.testing.assert_array_equal(old[f"{i}:{field}"],packed[f"{i}:{field}"])
        before, after = old[f"{i}:ok"], packed[f"{i}:ok"]
        assert not np.any(after & ~before)
        if np.any(before != after):
            differences.append(dict(index=i,invalidated=int(np.sum(before & ~after))))
    np.savez_compressed(JOB/"raw-matrix-reviewed.npz",**packed)
    save("technical-correction-receipt.json",dict(passed=True,trials=544,
        changed_cells=differences,invalidated=sum(r["invalidated"] for r in differences),
        signal_and_quote_fields_identical=True,original_preserved=True,
        matrix_sha256=sha(JOB/"raw-matrix-reviewed.npz")))


def benchmark():
    pins = snapshot()
    path = JOB/"original-source/tooling/ai-engines/prop_v10_signals.py"
    spec = importlib.util.spec_from_file_location("original_v10_signals", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data, calendar = sources(), gold_calendar(FIRST, END)
    samples = []
    for pair in range(16):
        timings, outputs = {}, {}
        for label in (("original","cached") if pair%2 == 0 else ("cached","original")):
            function = module.recipes if label == "original" else recipes
            start = time.perf_counter()
            outputs[label] = {asset:function(bars,asset,FIRST,END,calendar) for asset,bars in data.items()}
            timings[label] = time.perf_counter()-start
        for asset in data:
            for a,b in zip(outputs["original"][asset],outputs["cached"][asset]):
                assert a["config"] == b["config"] and a["id"] == b["id"]
                for field in ("at","side","stop"):
                    np.testing.assert_array_equal(a[field],b[field])
        samples.append(timings)
        print(dict(pair=pair+1,parity=True,**timings),flush=True)
    medians = {k:median(s[k] for s in samples) for k in ("original","cached")}
    save("signal-benchmark.json", dict(passed=True,alternating_pairs=16,samples=samples,
        medians=medians,speedup=medians["original"]/medians["cached"],
        original_source=pins,cached_source_sha256=sha(Path(__file__).with_name("prop_v10_signals.py")),
        scope="Same 136 recipes, all at/side/stop/config fields exact; signal generation only; warm memory.",
        price_inputs="Development 2018–2023 plus prior warmup only"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("oracle","benchmark","remeasure"))
    args = parser.parse_args()
    {"oracle":oracle,"benchmark":benchmark,"remeasure":remeasure}[args.mode]()
