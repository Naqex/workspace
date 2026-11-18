"""Read-only source enumeration and bounded SHA-deduplicated bot profiles."""
from collections import Counter
from pathlib import Path
import hashlib
import re
import subprocess
import time
from prop_v25_common import *
from prop_v24_inventory import SKIP, SOURCE, MATCH, ENV
from quant_core.native_paths import PathGuard, io_path, read_bounded, logical_path
from quant_core.bot_lab import SOURCE as BOT_SOURCE, BINARY, inspect_bytes

FORMATS = BOT_SOURCE | {".ex4", ".ex5"}
ENTRY_SIGNATURES = (b"OrderSend", b"order_send(", b"strategy.entry", b"class Strategy",
                    b"def generate", b"def signals", b"def next(", b"OnTick(", b".Buy(",
                    b"ExecuteMarketOrder", b"ExecuteMarketRangeOrder")


def classify_error(error):
    if getattr(error, "winerror", None) == 206:
        return "MAX_PATH"
    if isinstance(error, FileNotFoundError):
        return "NOT_FOUND"
    if isinstance(error, PermissionError):
        return "ACCESS_OR_SHARING"
    if isinstance(error, UnicodeError):
        return "ENCODING"
    if isinstance(error, SyntaxError):
        return "PARSE"
    return str(error) if isinstance(error, ValueError) else type(error).__name__


def run():
    JOB.mkdir(exist_ok=True)
    old = unpack("connector-source-inventory", V24)
    guard = PathGuard()
    audit = []
    event("prior_errors_start", count=len(old["errors"]))
    for item in old["errors"]:
        if item["type"] == "RG_TRAVERSAL_ERROR":
            continue
        try:
            raw = read_bounded(item["path"], 524288, guard=guard)
            audit.append(dict(path=item["path"], status="READABLE_NATIVE_PATH", bytes=len(raw)))
        except (OSError, ValueError) as exc:
            audit.append(dict(path=item["path"], status=classify_error(exc), winerror=getattr(exc, "winerror", None)))
    compressed("prior-error-reconciliation", audit)
    event("old_errors_reconciled", counts=dict(Counter(r["status"] for r in audit)))
    paths, errors, hits, aliases, profiles, large = [], [], [], [], {}, 0
    started = time.perf_counter()
    roots = [Path("D:/ANNAM/TradingWorkspace"), Path("E:/BACKUP-TRADINGWORKSPACE")]
    for rank, root in enumerate(roots):
        stderr = JOB / f"rg-{rank}-stderr.txt"
        args = ["rg", "--files", "--hidden", "--no-ignore", "--no-follow", "--maxdepth", "18", str(io_path(root))]
        for extension in sorted(SOURCE | FORMATS):
            args += ["-g", "*" + extension]
        args += ["-g", ".env*", "-g", "*.env"]
        for name in sorted(SKIP):
            args += ["-g", "!**/" + name + "/**"]
        event("enumeration_start", root=str(root))
        with stderr.open("x", encoding="utf-8") as log:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=log, text=True, encoding="utf-8")
            for line in proc.stdout:
                path = logical_path(line.rstrip("\r\n"))
                suffix = path.suffix.lower()
                paths.append(str(path))
                try:
                    _, info = guard.admit(path)
                    limit = 16 * 1024 * 1024 if suffix in FORMATS else 524288
                    if info.st_size > limit:
                        large += 1
                        continue
                    raw = read_bounded(path, limit, guard=guard)
                    is_bot = suffix in FORMATS and (suffix not in {".py", ".cs"} or
                              any(s in raw for s in ENTRY_SIGNATURES) or
                              any(s.decode().encode("utf-16le") in raw for s in ENTRY_SIGNATURES))
                    if is_bot:
                        digest = hashlib.sha256(raw).hexdigest()
                        key = digest + suffix
                        if key not in profiles:
                            profiles[key] = inspect_bytes(raw, suffix)
                        aliases.append(dict(path=str(path), profile=key, format=suffix))
                    if len(raw) <= 524288 and suffix not in BINARY:
                        text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig", errors="replace")
                        keys = sorted(set(ENV.findall(text)))
                        if MATCH.search(text) or keys:
                            hits.append(dict(path=str(path), bytes=len(raw), credential_key_names_only=keys,
                                signatures=sorted({m.group(0) for m in MATCH.finditer(text)})[:12], values_disclosed=False))
                except (OSError, ValueError, SyntaxError, UnicodeError, RecursionError) as exc:
                    errors.append(dict(path=str(path), status=classify_error(exc), winerror=getattr(exc, "winerror", None)))
                if len(paths) % 20000 == 0:
                    event("enumeration_progress", files=len(paths), profiles=len(profiles), errors=len(errors))
            status = proc.wait()
        if status not in (0, 1):
            errors.append(dict(path=str(root), status="RG_TRAVERSAL_ERROR", exit_code=status))
    old_bots = {str(logical_path(p)).casefold() for p in old["bot_paths"]}
    bot_paths = [r for r in aliases if r["format"] in {".mq4", ".mq5", ".pine", ".ex4", ".ex5"}]
    value = dict(paths=paths, hits=hits, rows=aliases, profiles=profiles, errors=errors,
                 roots=[str(p) for p in roots], maxdepth=18, pruned=sorted(SKIP),
                 no_sample_execution=True, credential_values_exported=False)
    manifest = compressed("inventory-and-profiles", value)
    summary = dict(files=len(paths), signature_matches=len(hits), bot_paths=len(bot_paths),
        new_bot_paths=sum(str(logical_path(r["path"])).casefold() not in old_bots for r in bot_paths),
        prior_bot_paths=len(old_bots), unique_profiles=len(profiles), formats=dict(Counter(p["format"] for p in profiles.values())),
        prior_errors=dict(Counter(r["status"] for r in audit)), current_errors=dict(Counter(r["status"] for r in errors)),
        skipped_large=large, seconds=time.perf_counter()-started, manifest=manifest)
    save("inventory-summary.json", summary)
    event("inventory_complete", **{k:v for k,v in summary.items() if k not in ("manifest",)})
    return summary


if __name__ == "__main__":
    run()
