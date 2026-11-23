"""Read-only automated intake scanner & FTMO red-flag triage for D:\\ANNAM\\strategy-intel\\inbox\\."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import mq5_whitebox_exporter as mq5

DEFAULT_INBOX = Path(r"D:\ANNAM\strategy-intel\inbox")
QUARANTINE_EXTS = {".ex4", ".ex5", ".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".msi", ".rar", ".zip", ".7z"}
OPEN_CODE_EXTS = {".mq5", ".mq4", ".mqh", ".pine", ".py"}
SET_TEXT_EXTS = {".set", ".txt", ".md"}
LOG_EXTS = {".csv", ".html", ".htm"}
DOC_EXTS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}

SET_RED_FLAGS = {
    "MARTINGALE_SET": re.compile(r"(martingale|lot_?mult|maxmartingale|recoverylot|lot_?factor)", re.I),
    "GRID_SET": re.compile(r"(grid_?size|grid_?step|max_?grid|grid_?lot|averaging)", re.I),
    "HFT_TICK_EXPLOIT": re.compile(r"\b(hft|high\s+frequency|hyper\s+activity|latency|tick\s*scalp)\b", re.I),
    "ROLLOVER_WINDOW": re.compile(r"(DayStartTime\s*=\s*23:|23:00:00[\s\S]{0,80}0?1:00:00)", re.I),
}
INDICATOR_HINTS = {
    "SuperTrend": re.compile(r"\b(supertrend|st_period|st_mult)\b", re.I),
    "ATR": re.compile(r"\b(atr_?period|atr_?mult|atr_?trail)\b", re.I),
    "RSI": re.compile(r"\b(rsi_?period|rsi_?level|rsi2)\b", re.I),
    "EMA_MA": re.compile(r"\b(ema_?period|ma_?period|sma_?period|movingaverage)\b", re.I),
    "Donchian_Channel": re.compile(r"\b(donchian|channel_?period|breakout)\b", re.I),
    "Trailing_SL": re.compile(r"\b(trailing|breakeven|step_?trail)\b", re.I),
    "Session_Filter": re.compile(r"\b(starthour|endhour|session|london|tokyo|newyork)\b", re.I),
}


def safe_read_text(path: Path, max_bytes: int = 512_000) -> str:
    raw = path.read_bytes()[:max_bytes]
    # Handle UTF-16 BOM (very common for MT5 .set files!)
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    if b"\x00" in raw[:200]:
        try:
            return raw.decode("utf-16-le", errors="replace")
        except Exception:
            pass
    return raw.decode("utf-8", errors="replace")


def file_sha16(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()[:16]


def run_defender_scan(target: Path) -> dict:
    mp = Path(r"C:\Program Files\Windows Defender\MpCmdRun.exe")
    if not mp.exists():
        return {"ran": False, "status": "DEFENDER_NOT_FOUND"}
    proc = subprocess.run(
        [str(mp), "-Scan", "-ScanType", "3", "-File", str(target)],
        capture_output=True, text=True, timeout=180,
    )
    return {
        "ran": True,
        "exit_code": proc.returncode,
        "status": "CLEAN_NO_THREATS_DETECTED" if proc.returncode == 0 else "THREAT_OR_ERROR_CHECK_OUTPUT",
        "note": "Defender exit=0 does NOT certify cracked .exe/.dll/.rar/.ex5 binaries safe to run.",
    }


def scan_inbox(inbox_root: Path, *, run_defender: bool = False) -> dict:
    """Strictly read-only inventory & static FTMO red-flag triage across all source subfolders."""
    if not inbox_root.exists():
        raise FileNotFoundError(f"Inbox path does not exist: {inbox_root}")

    defender = run_defender_scan(inbox_root) if run_defender else {"ran": False, "status": "SKIPPED"}
    counts = Counter()
    open_code_items = []
    set_text_items = []
    csv_items = []
    doc_items = []
    quarantined_items = []

    for p in sorted(inbox_root.rglob("*")):
        if not p.is_file() or p.name in (".gitkeep", "README.md", "desktop.ini", "Thumbs.db"):
            continue
        rel = p.relative_to(inbox_root).as_posix()
        ext = p.suffix.lower()
        size = p.stat().st_size
        counts[ext or "(none)"] += 1

        if ext in QUARANTINE_EXTS:
            risk = "CRITICAL_EXEC_OR_ARCHIVE" if ext in {".exe", ".dll", ".rar", ".zip", ".7z", ".bat", ".ps1"} else "OPAQUE_COMPILED_EA"
            quarantined_items.append({
                "path": rel, "ext": ext, "bytes": size, "sha256_16": file_sha16(p),
                "status": "QUARANTINED_NO_EXEC", "risk": risk,
            })
        elif ext in OPEN_CODE_EXTS:
            txt = safe_read_text(p)
            if ext in {".mq5", ".mq4", ".mqh"}:
                audit = mq5.audit_open_source_mq5(txt, filename=rel)
                open_code_items.append({"path": rel, "bytes": size, **audit})
            else:
                open_code_items.append({
                    "path": rel, "bytes": size, "sha256": file_sha16(p),
                    "lines": len(txt.splitlines()), "red_flags": [],
                    "intake_verdict": "READY_FOR_CLEANROOM_TRANSLATION",
                })
        elif ext in SET_TEXT_EXTS:
            txt = safe_read_text(p)
            flags = [k for k, rx in SET_RED_FLAGS.items() if rx.search(txt)]
            hints = [k for k, rx in INDICATOR_HINTS.items() if rx.search(txt)]
            set_text_items.append({
                "path": rel, "bytes": size, "sha256_16": file_sha16(p),
                "red_flags": flags, "public_indicator_hints": hints,
                "verdict": "FLAGGED_ANTI_PROP" if flags else "CLEAN_PUBLIC_IDEA_HINT",
            })
        elif ext in LOG_EXTS:
            txt = safe_read_text(p, max_bytes=128_000)
            csv_items.append({
                "path": rel, "bytes": size, "sha256_16": file_sha16(p),
                "sample_lines": len(txt.splitlines()),
                "verdict": "READY_FOR_DNA_FORENSICS",
            })
        elif ext in DOC_EXTS:
            doc_items.append({
                "path": rel, "ext": ext, "bytes": size, "sha256_16": file_sha16(p),
                "verdict": "READY_FOR_STRATEGY_EXTRACTION",
            })

    return {
        "schema": "naqex-inbox-triage-v1",
        "utc": datetime.now(timezone.utc).isoformat(),
        "inbox_root": str(inbox_root),
        "defender": defender,
        "summary": {
            "total_files": sum(counts.values()),
            "open_source_code": len(open_code_items),
            "open_source_clean": sum(1 for x in open_code_items if x["intake_verdict"].startswith(("CLEAN", "READY"))),
            "set_and_text_files": len(set_text_items),
            "set_flagged_anti_prop": sum(1 for x in set_text_items if x["red_flags"]),
            "trade_logs_csv": len(csv_items),
            "papers_and_docs": len(doc_items),
            "quarantined_binaries_no_exec": len(quarantined_items),
        },
        "ext_counts": dict(counts),
        "open_source_code": open_code_items,
        "set_and_text": set_text_items,
        "trade_logs": csv_items,
        "papers_and_docs": doc_items,
        "quarantined_binaries": quarantined_items,
    }


def render_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        f"# Báo cáo Quét Inbox (`{report['inbox_root']}`)",
        "",
        f"- **Thời điểm (UTC):** `{report['utc']}`",
        f"- **Windows Defender:** `{report['defender']['status']}`",
        f"- **Tổng quan:** `{s['total_files']}` file · Mã nguồn mở sạch: **`{s['open_source_clean']}/{s['open_source_code']}`** · CSV lịch sử lệnh: **`{s['trade_logs_csv']}`** · Tài liệu/PDF: **`{s['papers_and_docs']}`** · Văn bản `.set/.txt`: `{s['set_and_text_files']}` (dính cờ đỏ: `{s['set_flagged_anti_prop']}`) · File nhị phân cách ly (`NO_EXEC`): **`{s['quarantined_binaries_no_exec']}`**.",
        "",
    ]
    if report["open_source_code"]:
        lines += ["## 1. Mã nguồn mở đọc được (`.mq5` / `.mq4` / `.pine` / `.py`)", "", "| File | Cờ đỏ | Kết luận |", "| --- | --- | --- |"]
        for x in report["open_source_code"]:
            lines.append(f"| `{x['path']}` | `{', '.join(x['red_flags']) or 'NONE'}` | `{x['intake_verdict']}` |")
        lines.append("")
    if report["set_and_text"]:
        lines += ["## 2. Tham số `.set` & ghi chú `.txt/.md` (chỉ đọc văn bản thuần)", "", "| File | Cờ đỏ Prop | Gợi ý chỉ báo công khai | Kết luận |", "| --- | --- | --- | --- |"]
        for x in report["set_and_text"]:
            lines.append(f"| `{x['path']}` | `{', '.join(x['red_flags']) or 'NONE'}` | `{', '.join(x['public_indicator_hints']) or '-'}` | `{x['verdict']}` |")
        lines.append("")
    if report["trade_logs"]:
        lines += ["## 3. Lịch sử lệnh CSV/HTML (sẵn sàng chạy phễu DNA Pass 8–9)", ""]
        for x in report["trade_logs"]:
            lines.append(f"- `{x['path']}` (`{x['bytes']:,}` B)")
        lines.append("")
    if report["papers_and_docs"]:
        lines += ["## 4. Bài báo / PDF / Ảnh chiến lược", ""]
        for x in report["papers_and_docs"]:
            lines.append(f"- `{x['path']}` (`{x['bytes']:,}` B)")
        lines.append("")
    if report["quarantined_binaries"]:
        lines += ["## 5. File nhị phân & nén bị cách ly (`QUARANTINED_NO_EXEC` — KHÔNG chạy, KHÔNG giải nén)", "", "| File | Kích cỡ | Mức rủi ro |", "| --- | ---: | --- |"]
        for x in report["quarantined_binaries"]:
            lines.append(f"| `{x['path']}` | `{x['bytes']:,}` B | `{x['risk']}` |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_INBOX)
    parser.add_argument("--defender", action="store_true", help="Run Windows Defender on-demand scan first")
    parser.add_argument("--report-out", type=Path, default=None)
    args = parser.parse_args()

    rep = scan_inbox(args.path, run_defender=args.defender)
    md = render_markdown(rep)
    out_base = args.report_out or (args.path.parent / "inbox-triage-report")
    out_base.with_suffix(".json").write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    out_base.with_suffix(".md").write_text(md, encoding="utf-8", newline="\n")
    print(f"INBOX_SCAN_OK: {rep['summary']}", flush=True)
    print(f"REPORT_MD: {out_base.with_suffix('.md')}", flush=True)


if __name__ == "__main__":
    main()
