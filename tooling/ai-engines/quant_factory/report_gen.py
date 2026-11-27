"""Layer 4: Standardized Markdown table & SHA-256 verified atomic JSON receipt writer (zero transcription drift)."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path


def _atomic_write_text(path: Path, text: str) -> None:
    """Atomically replace a text file after full serialization, flush, and fsync."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def format_markdown_table(headers: list[str], rows: list[list], *, right_align_cols: set[int] | None = None) -> str:
    ra = right_align_cols or set()
    sep = ["---:" if i in ra else "---" for i in range(len(headers))]
    lines = [
        "| " + " | ".join(str(h) for h in headers) + " |",
        "|" + "|".join(sep) + "|",
    ]
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(lines)


def write_verified_receipt(output_path: Path, payload: dict, *, overwrite: bool = False) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Immutable receipt already exists: {output_path}")
    _atomic_write_text(output_path, body)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    sha_path = output_path.with_suffix(".sha256")
    _atomic_write_text(sha_path, f"{digest}  {output_path.name}\n")
    return digest
