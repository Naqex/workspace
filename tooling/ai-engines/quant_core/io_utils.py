"""Canonical shared I/O, cryptographic hashing, and repo-root helpers for Naqex.

Zero-dependency stdlib-only module (ZERO scipy imports) replacing duplicated
SHA-256 helpers and non-atomic JSON writers across `tooling/ai-engines/`.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

PathLike = str | os.PathLike[str]

DEFAULT_REPO_MARKERS: tuple[str, ...] = ("pyproject.toml", "AGENTS.md", ".git")
_SUPERPROJECT_MARKERS: tuple[str, ...] = ("pyproject.toml", "AGENTS.md", "tooling")


def sha256_bytes(data: bytes | bytearray | memoryview) -> str:
    """Return the lowercase hexadecimal SHA-256 digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: PathLike) -> str:
    """Return the lowercase hexadecimal SHA-256 digest of a file via `hashlib.file_digest`."""
    target = Path(path)
    with target.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def canonical_json(obj: Any, *, ensure_ascii: bool = False) -> str:
    """Serialize an object into deterministic compact JSON (sorted keys, no NaN/Inf)."""
    return json.dumps(
        obj,
        ensure_ascii=ensure_ascii,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_json_canonical(obj: Any) -> str:
    """Return the lowercase hexadecimal SHA-256 digest of an object's canonical JSON form."""
    return sha256_bytes(canonical_json(obj).encode("utf-8"))


def atomic_write_bytes(path: PathLike, data: bytes | bytearray | memoryview) -> Path:
    """Atomically write raw bytes using same-directory temp file + flush + fsync + os.replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return target


def atomic_write_text(
    path: PathLike,
    text: str,
    *,
    encoding: str = "utf-8",
    newline: str = "\n",
) -> Path:
    """Atomically write UTF-8 text (default LF) via temp file + flush + fsync + os.replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            newline=newline,
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return target


def atomic_write_json(
    path: PathLike,
    obj: Any,
    *,
    indent: int | None = 2,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
    allow_nan: bool = False,
    default: Callable[[Any], Any] | None = None,
) -> Path:
    """Atomically serialize JSON (with trailing LF) and replace `path` via fsync + os.replace."""
    text = (
        json.dumps(
            obj,
            indent=indent,
            sort_keys=sort_keys,
            ensure_ascii=ensure_ascii,
            allow_nan=allow_nan,
            default=default,
        )
        + "\n"
    )
    return atomic_write_text(path, text)


def repo_root_from(
    file_path: PathLike,
    *,
    markers: tuple[str, ...] = DEFAULT_REPO_MARKERS,
) -> Path:
    """Resolve the enclosing repository root upward from `file_path` with zero hardcoded paths."""
    resolved = Path(file_path).resolve()
    start = resolved if resolved.is_dir() else resolved.parent
    candidates = (start, *start.parents)

    if markers == DEFAULT_REPO_MARKERS:
        for candidate in candidates:
            if all((candidate / marker).exists() for marker in _SUPERPROJECT_MARKERS):
                return candidate

    for candidate in candidates:
        if any((candidate / marker).exists() for marker in markers):
            return candidate

    raise FileNotFoundError(f"Could not locate repository root upward from '{file_path}' using markers {markers!r}.")
