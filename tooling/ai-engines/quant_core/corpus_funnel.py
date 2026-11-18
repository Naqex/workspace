"""Static structural triage; absence of flags never proves executable safety."""
import re
from quant_core.bot_lab import indicators_in

RED = {"MARTINGALE_GRID_TOXICITY": "MARTINGALE_GRID",
       "NO_STOP_LOSS_TOXICITY": "NO_STOP_LOSS",
       "BACKTEST_CHEAT_HARDCODED_DATES": "HARDCODED_DATE_REVIEW"}


def arguments(code, pattern):
    result = []
    for found in re.finditer(pattern + r"\s*\(", code):
        depth, start, items = 1, found.end(), []
        quoted, escaped = None, False
        for i in range(start, len(code)):
            ch = code[i]
            if quoted:
                if ch == quoted and not escaped:
                    quoted = None
                escaped = ch == "\\" and not escaped
                continue
            if ch in "\"'":
                quoted = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    items.append(code[start:i].strip())
                    result.append(items)
                    break
            elif ch == "," and depth == 1:
                items.append(code[start:i].strip())
                start = i + 1
    return result


def classify(profile, text=None, path=""):
    flags = sorted({RED.get(f["flag"], f["flag"]) for f in profile.get("findings", [])})
    base = dict(flags=flags, indicators=profile.get("indicators", []),
        timeframe=profile.get("timeframes", []), asset="CHART_SYMBOL_UNSPECIFIED",
        safety_proven=False, entry=profile.get("entry_logic", []),
        exits=profile.get("exit_risk_logic", []), license_status="SOURCE_ONLY_NO_REDISTRIBUTION_REVIEWED")
    if profile.get("logic_recovery") == "UNAVAILABLE_FROM_STRINGS":
        return dict(base, status="BINARY_LOGIC_UNKNOWN")
    if text is None:
        return dict(base, status="SOURCE_UNAVAILABLE")
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    base["indicators"] = sorted(set(base["indicators"]) | set(indicators_in(code)))
    if re.search(r"return\s*\(\s*true\s*\)\s*;\s*\{\s*ExtPatternDetected\s*=\s*true", code):
        flags.append("ORPHAN_SIGNAL_BLOCK_REVIEW")
    defaults = {m[0]:float(m[1]) for m in re.findall(
        r"\binput\s+(?:uint|int|double)\s+(\w+)\s*=\s*(-?\d+(?:\.\d+)?)\s*;", code)}
    base.update(defaults=defaults)
    calls = []
    for pattern, sl in ((r"\.\s*Buy",3),(r"\.\s*Sell",3),(r"\.\s*PositionOpen",4)):
        calls.extend((args, sl) for args in arguments(code, pattern))
    if profile["format"] == ".mq4":
        calls.extend((args,5) for args in arguments(code, r"\bOrderSend"))
    literal_zero = any(len(args) <= sl or args[sl] in ("0","0.0","0.00","NULL") for args,sl in calls)
    if literal_zero:
        flags.append("NO_STOP_LOSS")
    base["flags"] = sorted(set(flags))
    if flags:
        return dict(base, status="FLAGGED_REVIEW")
    if "research/bot_reverse_lab/controls" in path.replace("\\","/"):
        return dict(base, status="SYNTHETIC_CONTROL")
    positive_sl = any(v>0 and re.search(r"(?:^InpSL$|stoploss|stop_loss)",k,re.I)
                      for k,v in defaults.items())
    executable = bool(re.search(r"\bOnTick\s*\(",code) and calls)
    if not executable:
        return dict(base, status="UTILITY_OR_UNRESOLVED_ENTRY")
    if not positive_sl or not base["indicators"]:
        return dict(base, status="SL_OR_SIGNAL_BINDING_UNMEASURED")
    # A source/default-bound candidate, still requiring full rule/manual review.
    return dict(base, status="CLEAN_STRUCTURAL_CANDIDATE",
        hard_sl_scope="positive declared defaults and explicit nonzero order SL argument",
        default_SL_points=next(v for k,v in defaults.items() if v>0 and
                              re.search(r"(?:^InpSL$|stoploss|stop_loss)",k,re.I)),
        broker_safety=False, causal_translation_review_required=True,
        fingerprint_only=False)
