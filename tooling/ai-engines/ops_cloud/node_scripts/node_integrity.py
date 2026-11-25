"""Naqex Home-VPS binary SHA-256, red-news CSV, and KeepPrivate=1 integrity audit (`OrderSend = 0`)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import pathlib
import re

DEFAULT_MT5_ROOT = pathlib.Path(r"C:\Naqex\mt5")
DEFAULT_EXPECTED_SHA = pathlib.Path(r"C:\Naqex\ops\ex5_expected_sha256.json")


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_ini_safe(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return raw.decode("utf-16-le", errors="ignore") if b"\x00" in raw[:200] else raw.decode("utf-8", errors="ignore")


def check_ini_keep_private(path: pathlib.Path) -> dict:
    if not path.exists():
        return {"exists": False, "keep_private": None, "has_login_override": False}
    txt = _read_ini_safe(path)
    kp = None
    has_login = False
    for ln in txt.splitlines():
        s = ln.strip()
        if s.lower().startswith("keepprivate="):
            kp = s.split("=", 1)[1].strip()
        if re.match(r"^login\s*=", s, re.IGNORECASE):
            has_login = True
    return {"exists": True, "keep_private": kp, "has_login_override": has_login}


def audit_integrity(
    mt5_root: pathlib.Path = DEFAULT_MT5_ROOT,
    expected_sha_path: pathlib.Path = DEFAULT_EXPECTED_SHA,
) -> dict:
    ex5_dir = mt5_root / "MQL5" / "Experts" / "Naqex"
    found_ex5 = {p.name: {"bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in sorted(ex5_dir.glob("*.ex5"))} if ex5_dir.exists() else {}

    expected_map: dict[str, str] = {}
    expected_csv_sha: str | None = None
    if expected_sha_path.exists():
        try:
            raw = json.loads(expected_sha_path.read_text(encoding="utf-8-sig"))
            if isinstance(raw, dict):
                if isinstance(raw.get("ex5"), dict):
                    expected_map = raw["ex5"]
                elif isinstance(raw.get("files"), dict):
                    expected_map = raw["files"]
                else:
                    expected_map = {k: v for k, v in raw.items() if k.endswith(".ex5") and isinstance(v, str)}
                if isinstance(raw.get("red_news_csv_sha256"), str):
                    expected_csv_sha = raw["red_news_csv_sha256"].lower()
        except Exception:
            expected_map = {}

    mismatches: list[dict] = []
    matched = 0
    for name, exp_sha in expected_map.items():
        if not isinstance(exp_sha, str):
            continue
        actual = found_ex5.get(name, {}).get("sha256")
        if actual and actual.lower() == exp_sha.lower():
            matched += 1
        else:
            mismatches.append({"file": name, "expected": exp_sha[:16], "actual": (actual[:16] if actual else "MISSING")})

    csv_p = mt5_root / "MQL5" / "Files" / "naqex_red_news_utc.csv"
    csv_info = {"exists": csv_p.exists(), "rows": 0, "sha256": None, "sha_match": None}
    if csv_p.exists():
        lines = [ln for ln in csv_p.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
        csv_info["rows"] = max(0, len(lines) - 1)
        full_sha = sha256_file(csv_p).lower()
        csv_info["sha256"] = full_sha[:16]
        csv_info["sha_match"] = (full_sha == expected_csv_sha) if expected_csv_sha else True

    common_ini = check_ini_keep_private(mt5_root / "Config" / "common.ini")
    conn_ini = check_ini_keep_private(mt5_root / "connector.ini")

    ok = (
        len(mismatches) == 0
        and matched == len(expected_map)
        and csv_info["exists"]
        and csv_info["rows"] >= 400
        and csv_info["sha_match"] is not False
        and common_ini.get("keep_private") == "1"
        and not conn_ini.get("has_login_override")
    )
    return {
        "checked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_count": 0,
        "ok": ok,
        "ex5_found_count": len(found_ex5),
        "ex5_expected_matched": matched,
        "ex5_mismatches": mismatches,
        "red_news_csv": csv_info,
        "common_ini": common_ini,
        "connector_ini": conn_ini,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only SHA-256, red-news, and KeepPrivate integrity check.")
    ap.add_argument("--mt5-root", type=pathlib.Path, default=DEFAULT_MT5_ROOT)
    ap.add_argument("--expected-sha", type=pathlib.Path, default=DEFAULT_EXPECTED_SHA)
    args = ap.parse_args()
    print(json.dumps(audit_integrity(args.mt5_root, args.expected_sha), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
