"""Unit tests for canonical shared I/O, SHA-256, and repo-root helpers (`quant_core.io_utils`)."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest
from quant_core import io_utils


def test_io_utils_has_zero_scipy_imports() -> None:
    path = Path(io_utils.__file__).resolve()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not (alias.name == "scipy" or alias.name.startswith("scipy."))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert not (mod == "scipy" or mod.startswith("scipy."))


def test_sha256_helpers_match_stdlib(tmp_path: Path) -> None:
    raw = b"naqex-io-utils-test-payload\n"
    expected = hashlib.sha256(raw).hexdigest()
    assert io_utils.sha256_bytes(raw) == expected

    f = tmp_path / "sample.bin"
    f.write_bytes(raw)
    assert io_utils.sha256_file(f) == expected
    assert io_utils.sha256_file(str(f)) == expected

    a = {"b": 2, "a": [1, True, None]}
    b = {"a": [1, True, None], "b": 2}
    assert io_utils.sha256_json_canonical(a) == io_utils.sha256_json_canonical(b)
    assert len(io_utils.sha256_json_canonical(a)) == 64

    with pytest.raises(ValueError):
        io_utils.sha256_json_canonical({"bad": float("nan")})


def test_atomic_writes_create_replace_and_leave_no_tmp(tmp_path: Path) -> None:
    b_path = tmp_path / "nested" / "data.bin"
    io_utils.atomic_write_bytes(b_path, b"\x00\x01\x02")
    assert b_path.read_bytes() == b"\x00\x01\x02"
    io_utils.atomic_write_bytes(b_path, b"updated")
    assert b_path.read_bytes() == b"updated"

    t_path = tmp_path / "nested" / "note.txt"
    io_utils.atomic_write_text(t_path, "line1\nline2\n")
    assert t_path.read_bytes() == b"line1\nline2\n"

    j_path = tmp_path / "nested" / "report.json"
    payload = {"z": 1, "a": "tiếng Việt"}
    io_utils.atomic_write_json(j_path, payload, indent=2)
    raw_text = j_path.read_text(encoding="utf-8")
    assert raw_text.endswith("\n")
    assert "\r\n" not in raw_text
    assert json.loads(raw_text) == payload

    with pytest.raises(ValueError):
        io_utils.atomic_write_json(j_path, {"bad": float("inf")})
    # Previous valid content must remain intact after failed write.
    assert json.loads(j_path.read_text(encoding="utf-8")) == payload

    # Zero stray temporary files left behind.
    leftover = [p.name for p in (tmp_path / "nested").iterdir() if p.name.endswith(".tmp")]
    assert leftover == []


def test_atomic_writes_cleanup_tmp_on_encode_type_and_fsync_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ascii_path = tmp_path / "ascii.txt"
    io_utils.atomic_write_text(ascii_path, "baseline\n")
    with pytest.raises(UnicodeEncodeError):
        io_utils.atomic_write_text(ascii_path, "tiếng Việt", encoding="ascii")
    assert ascii_path.read_text(encoding="utf-8") == "baseline\n"
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []

    raw_path = tmp_path / "raw.bin"
    io_utils.atomic_write_bytes(raw_path, b"orig")
    bad_bytes: Any = "not-bytes"
    with pytest.raises(TypeError):
        io_utils.atomic_write_bytes(raw_path, bad_bytes)
    assert raw_path.read_bytes() == b"orig"
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []

    fsync_path = tmp_path / "fsync.bin"
    io_utils.atomic_write_bytes(fsync_path, b"safe")

    def _boom_fsync(_fd: int) -> None:
        raise OSError("simulated fsync I/O error")

    monkeypatch.setattr(os, "fsync", _boom_fsync)
    with pytest.raises(OSError, match="simulated fsync I/O error"):
        io_utils.atomic_write_bytes(fsync_path, b"corrupted")
    assert fsync_path.read_bytes() == b"safe"
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []

    text_fsync_path = tmp_path / "fsync.txt"
    with pytest.raises(OSError, match="simulated fsync I/O error"):
        io_utils.atomic_write_text(text_fsync_path, "cannot flush")
    assert not text_fsync_path.exists()
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_repo_root_from_resolves_workspace_and_synthetic_repo(tmp_path: Path) -> None:
    root = io_utils.repo_root_from(io_utils.__file__)
    assert (root / "pyproject.toml").is_file()
    assert (root / "AGENTS.md").is_file()
    assert (root / "tooling" / "ai-engines").is_dir()

    synth = tmp_path / "repo" / "a" / "b" / "mod.py"
    synth.parent.mkdir(parents=True)
    (tmp_path / "repo" / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    synth.write_text("# mod\n", encoding="utf-8")
    assert io_utils.repo_root_from(synth) == (tmp_path / "repo").resolve()

    isolated = tmp_path / "orphan_dir" / "file.py"
    isolated.parent.mkdir(parents=True)
    isolated.write_text("", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        io_utils.repo_root_from(isolated, markers=("__never_exists_marker__",))
