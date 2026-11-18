"""One registered ISO scaling trial on the unchanged V24 Development trade tape."""
from fractions import Fraction
import subprocess
import math
from prop_v25_common import *
from prop_v24_pareto import prepare, measure, WEIGHTS
from prop_v15_evidence import bars_for
from prop_v14_paths import M1ScenarioQuotes
from quant_core.research_fast_fail import content_hash

FREEZE = PROTOCOL.with_name("CORPUS-ISOLATION-V25-FREEZE-20261118.json")


def iso_weights(previous):
    base, candidate = previous["baseline"], previous["candidate"]
    c = min(Fraction(str(base["equity_R_DD"])) / Fraction(str(candidate["equity_R_DD"])),
            Fraction(str(base["max_open_risk_USD"])) / Fraction(str(candidate["max_open_risk_USD"])))
    if not 0 < c <= 1:
        raise ValueError("invalid_iso_scale")
    return c, {k: float(c * Fraction(str(v))) for k, v in WEIGHTS.items()}


def decide(candidate, baseline):
    reasons = []
    for row in (candidate, baseline):
        for name in ("net_R", "equity_R_DD", "static_R_loss", "worst_daily_R", "max_open_risk_USD"):
            value = row.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                reasons.append("INVALID_METRIC_" + name)
            elif name != "net_R" and value < 0:
                reasons.append("NEGATIVE_METRIC_" + name)
        clusters = row.get("cluster_R", [])
        if len(clusters) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                                    not math.isfinite(v) for v in clusters):
            reasons.append("INVALID_CLUSTERS")
    if reasons:
        return dict(passed=False, reasons=reasons, candidate=candidate, baseline=baseline)
    if candidate["net_R"] <= baseline["net_R"] + 1e-8:
        reasons.append("NET_NOT_HIGHER")
    for name in ("equity_R_DD", "static_R_loss", "worst_daily_R", "max_open_risk_USD"):
        if candidate[name] > baseline[name] + 1e-8:
            reasons.append(name.upper() + "_INCREASED")
    if min(candidate["cluster_R"]) <= 0:
        reasons.append("DUAL_CLUSTER_FAIL")
    return dict(passed=not reasons, reasons=reasons, candidate=candidate, baseline=baseline)


def development():
    previous = read(V24 / "P80-Development-decision.json")
    c, weights = iso_weights(previous["cases"][0]["decision"])
    sources = [PROTOCOL, Path(__file__), Path("tooling/ai-engines/prop_v25_campaign.py"),
               Path("tooling/ai-engines/prop_v25_common.py"), Path("tooling/ai-engines/prop_v24_pareto.py"),
               Path("tooling/ai-engines/prop_v15_accounts.py"),
               Path("tooling/ai-engines/prop_v14_accounts.py")]
    registration = dict(commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        sources={str(p): sha(p) for p in sources}, c_iso=str(c), c_iso_float=float(c),
        weights=weights, parent_sha256=sha(V24 / "P80-Development-decision.json"),
        development=[FIRST, DEV_END], trials=1, prices_2024_2026_read=False)
    save("ISO-registration.json", registration)
    bars = {a: bars_for(a, True) for a in ("XAUUSD", "EURUSD")}
    cases = []
    for tag, order in (("OLHC", "OPEN_LOW_HIGH_CLOSE"), ("OHLC", "OPEN_HIGH_LOW_CLOSE")):
        trades = read(V19 / f"Dev-{tag}-PRIMARY-trades.json")
        assert all(FIRST <= t["entry_msc"] <= t["exit_msc"] < DEV_END for t in trades)
        readers = {a: M1ScenarioQuotes(b, order, FIRST, DEV_END) for a, b in bars.items()}
        points = prepare(trades, readers)
        base, candidate = measure(trades, points, {}), measure(trades, points, weights)
        prior = next(r["decision"]["baseline"] for r in previous["cases"] if r["order"] == tag)
        for name in ("net_R", "equity_R_DD", "max_open_risk_USD"):
            assert abs(base[name] - prior[name]) < 1e-7, name
        cases.append(dict(order=tag, **decide(candidate, base)))
    result = dict(passed=all(c["passed"] for c in cases), cases=cases,
                  weights=weights, c_iso=str(c), linear_guarantee=False, prices_2024_2026_read=False)
    save("ISO-Development-decision.json", result)
    if result["passed"]:
        ids = sorted({t["id"] for t in trades})
        profile = dict(name="BASE_GUARD", gamma=None,
                       weights={i: weights[i.split("|")[1][:2]] for i in ids})
        freeze = dict(schema="V25-ISO-freeze-v1", selected="P80_20_ISO", profile=profile,
            sources=registration["sources"], registration_sha256=sha(JOB / "ISO-registration.json"),
            decision_sha256=sha(JOB / "ISO-Development-decision.json"),
            weights_hash=content_hash(weights), later_history_already_exposed=True,
            prices_2024_2026_opened_for_selection=False, prop_qualified=False)
        with FREEZE.open("x", encoding="utf-8") as stream:
            import json
            json.dump(freeze, stream, ensure_ascii=False, indent=2)
    event("ISO_Development_complete", passed=result["passed"], cases=cases, weights=weights)
    return result


def verify():
    import json
    frozen = read(FREEZE)
    committed = json.loads(subprocess.check_output(["git", "show", "HEAD:" + FREEZE.as_posix()]))
    if frozen != committed:
        raise ValueError("ISO_committed_freeze_required")
    for name, digest in frozen["sources"].items():
        if sha(name) != digest:
            raise ValueError("ISO_frozen_source_changed:" + name)
    if sha(JOB / "ISO-Development-decision.json") != frozen["decision_sha256"]:
        raise ValueError("ISO_decision_changed")
    decision = read(JOB / "ISO-Development-decision.json")
    if (decision.get("passed") is not True or
            [c["order"] for c in decision["cases"]] != ["OLHC", "OHLC"] or
            not all(c == dict(order=c["order"], **decide(c["candidate"], c["baseline"]))
                    and c["passed"] for c in decision["cases"])):
        raise ValueError("ISO_Development_gate_required")
    _, expected = iso_weights(read(V24 / "P80-Development-decision.json")["cases"][0]["decision"])
    if decision["weights"] != expected or frozen["weights_hash"] != content_hash(expected):
        raise ValueError("ISO_weights_changed")
    ids = sorted({t["id"] for t in read(V19 / "Dev-OLHC-PRIMARY-trades.json")})
    expected_profile = dict(name="BASE_GUARD", gamma=None,
                            weights={i: expected[i.split("|")[1][:2]] for i in ids})
    if frozen["profile"] != expected_profile:
        raise ValueError("ISO_profile_changed")
    return frozen


if __name__ == "__main__":
    development()
