"""Layer 4: Standardized Markdown table & SHA-256 verified JSON receipt writer (zero manual transcription drift)."""

import hashlib
import json
from pathlib import Path


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
    output_path.write_text(body, encoding="utf-8", newline="\n")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    sha_path = output_path.with_suffix(".sha256")
    sha_path.write_text(f"{digest}  {output_path.name}\n", encoding="utf-8", newline="\n")
    return digest
