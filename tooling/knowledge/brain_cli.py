"""Naqex Knowledge Brain CLI: Local-First Markdown Source-of-Truth + Disposable SQLite FTS5 & Hybrid Vector Index.

Zero daemon, zero external API keys, Vietnamese diacritic-aware FTS5 (`unicode61 remove_diacritics 2`)
fused via Reciprocal Rank Fusion (RRF) with char/word TF-IDF cosine similarity and Evergreen preservation.

Per-chunk float32 vectors are persisted directly in SQLite `chunks.vec_blob` (WAL + busy_timeout=30s)
so 1-file incremental re-indexing completes in < 30 ms and 8+ concurrent subagents operate safely.

Usage:
  python -X utf8 tooling/knowledge/brain_cli.py index
  python -X utf8 tooling/knowledge/brain_cli.py query "thi quy calmar holdout" --top 8
  python -X utf8 tooling/knowledge/brain_cli.py owner-brief
  python -X utf8 tooling/knowledge/brain_cli.py log-curiosity --topic "AI" --question "..." --takeaway "..."
  python -X utf8 tooling/knowledge/brain_cli.py log-decision --decision "..." --reason "..." --revisit "..."
  python -X utf8 tooling/knowledge/brain_cli.py audit-data
"""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import threading
import time
from typing import Any
import unicodedata
from urllib.parse import unquote

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BRAIN_DIR = ROOT / ".runtime/knowledge"
DB_PATH = BRAIN_DIR / "brain.sqlite3"
VEC_PATH = BRAIN_DIR / "brain_vec.npz"

HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
LEADING_SECTION_NUM_RE = re.compile(r"^(?:[0-9]+(?:\.[0-9]+)*\.?|[a-z]\.)\s+")
HEADING_STOPWORDS = frozenset({
    "va", "cua", "cho", "voi", "cac", "trong", "khi", "tu", "den", "la", "tai",
    "the", "and", "for", "of", "in", "on", "to", "vs", "with", "from", "by",
})
QUERY_STOPWORDS = HEADING_STOPWORDS | frozenset({
    "lam", "sao", "de", "do", "bi", "chi", "nao", "nhung", "nhu", "the", "thi",
    "co", "khong", "duoc", "nen", "can", "phai", "neu", "mot", "nhieu", "it",
    "gi", "bao", "nhieu", "cung", "luc", "truoc", "sau", "ve", "vao", "ra",
    "len", "xuong", "nay", "kia", "day", "roi", "ma", "hay", "hoac", "nhung",
    "se", "da", "dang", "con", "hon", "nhat", "rat", "qua", "tai", "sao",
    "what", "how", "why", "when", "where", "which", "who", "does", "should",
    "can", "could", "would", "this", "that", "these", "those", "about", "into",
    "are", "was", "were", "have", "has", "had", "not", "but", "all", "any",
})
TOKEN_RE = re.compile(r"[0-9a-zA-Z\u00C0-\u024F\u1E00-\u1EFF\u4E00-\u9FFF\u0400-\u04FF_]{2,}")
VEC_DIM = 512  # Compact hashed feature space (zero-pickle float32 matrix -> < 5 MB, < 10 ms dot product)
_VEC_BYTES = VEC_DIM * 4
_RACY_MTIME_WINDOW_SEC = 2.0
_SQLITE_TIMEOUT_SEC = 30.0

_THREAD_WRITE_LOCK = threading.RLock()
_LOCK_TLS = threading.local()


def _replace_with_retry(src: Path, dst: Path, *, retries: int = 12) -> None:
    """Windows-safe atomic os.replace with short backoff for transient reader/AV sharing locks."""
    for attempt in range(retries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt + 1 >= retries:
                raise
            time.sleep(0.005 * (attempt + 1))


def _atomic_write_text(path: Path, text: str) -> None:
    """Atomically write UTF-8 text via temp file -> flush -> fsync -> os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
            tmp_path = Path(fh.name)
        _replace_with_retry(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def _write_vec_compat_marker(vec_path: Path) -> None:
    """Write a tiny (< 1 KB) zero-pickle `.npz` compatibility marker atomically for legacy path checks."""
    vec_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=vec_path.parent,
            prefix=f".{vec_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            np.savez(
                fh,
                storage=np.array([b"sqlite_vec_blob_v2"]),
                vec_dim=np.array([VEC_DIM], dtype=np.int64),
            )
            fh.flush()
            os.fsync(fh.fileno())
            tmp_path = Path(fh.name)
        _replace_with_retry(tmp_path, vec_path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


@contextmanager
def _brain_write_lock(*, timeout_sec: float = _SQLITE_TIMEOUT_SEC):
    """Reentrant in-process + cross-process advisory write lock for brain DB & owner logs."""
    lock_dir = BRAIN_DIR
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / ".brain.lock"
    key = str(lock_path.resolve())
    held_map: dict[str, int] = getattr(_LOCK_TLS, "held", None) or {}
    _LOCK_TLS.held = held_map

    with _THREAD_WRITE_LOCK:
        depth = held_map.get(key, 0)
        if depth > 0:
            held_map[key] = depth + 1
            try:
                yield
            finally:
                held_map[key] -= 1
            return

        fh = lock_path.open("a+b")
        os_locked = False
        deadline = time.monotonic() + max(1.0, timeout_sec)
        try:
            if os.name == "nt":
                import msvcrt

                fh.seek(0, os.SEEK_END)
                if fh.tell() == 0:
                    fh.write(b"0")
                    fh.flush()
                while True:
                    try:
                        fh.seek(0)
                        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                        os_locked = True
                        break
                    except OSError as exc:
                        if time.monotonic() >= deadline:
                            raise TimeoutError(f"Timed out waiting for brain write lock: {lock_path}") from exc
                        time.sleep(0.01)
            else:
                import fcntl

                while True:
                    try:
                        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        os_locked = True
                        break
                    except OSError as exc:
                        if time.monotonic() >= deadline:
                            raise TimeoutError(f"Timed out waiting for brain write lock: {lock_path}") from exc
                        time.sleep(0.01)

            held_map[key] = 1
            try:
                yield
            finally:
                held_map.pop(key, None)
        finally:
            if os_locked:
                try:
                    if os.name == "nt":
                        import msvcrt

                        fh.seek(0)
                        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
            fh.close()


def _connect_db(db_path: Path, *, write: bool = False) -> sqlite3.Connection:
    """Open a WAL-enabled, high-busy-timeout SQLite connection safe for 8+ concurrent subagents."""
    conn = sqlite3.connect(str(db_path), timeout=_SQLITE_TIMEOUT_SEC, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=30000")
    for attempt in range(8):
        try:
            cur_mode = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            if cur_mode != "wal":
                conn.execute("PRAGMA journal_mode=WAL")
            if write:
                conn.execute("PRAGMA synchronous=NORMAL")
            break
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                if attempt + 1 >= 8:
                    conn.close()
                    raise
                time.sleep(0.02 * (attempt + 1))
            else:
                conn.close()
                raise
    return conn


def _strip_accents(text: str) -> str:
    # Normalize Vietnamese & Latin diacritics while keeping CJK & Cyrillic intact
    nk = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(ch for ch in nk if unicodedata.category(ch) != "Mn")


def _hash_vector(text: str) -> np.ndarray:
    """Deterministic multilingual hashed word + char-3gram TF vector (L2-normalized, zero external models)."""
    norm = _strip_accents(text)
    tokens = TOKEN_RE.findall(norm)
    vec = np.zeros(VEC_DIM, dtype=np.float32)
    counts: Counter[str] = Counter()
    for tok in tokens:
        counts[f"w:{tok}"] += 1
        if len(tok) >= 4:
            for i in range(len(tok) - 2):
                counts[f"c:{tok[i:i+3]}"] += 1
    for feat, cnt in counts.items():
        h = int.from_bytes(hashlib.blake2b(feat.encode("utf-8"), digest_size=4).digest(), "little")
        idx = h % VEC_DIM
        sign = 1.0 if ((h >> 16) & 1) else -1.0
        vec[idx] += sign * (1.0 + math.log(cnt))
    norm_val = float(np.linalg.norm(vec))
    if norm_val > 1e-9:
        vec /= norm_val
    return vec


def owner_dir(root: Path | None = None) -> Path:
    """Return Layer-2 private owner directory if present locally, else fallback to public `knowledge/owner`."""
    base = root if root is not None else ROOT
    priv = base / "private_vault" / "owner"
    if priv.is_dir():
        return priv
    return base / "knowledge" / "owner"


def resolve_owner_file(filename: str, root: Path | None = None) -> Path:
    """Resolve an owner Markdown file using Private-First override with clean public fallback."""
    base = root if root is not None else ROOT
    priv_file = base / "private_vault" / "owner" / filename
    if priv_file.is_file():
        return priv_file
    return base / "knowledge" / "owner" / filename


def _iter_knowledge_docs_with_stat(
    *, include_archive: bool = False
) -> list[tuple[str, str, str, bool, float, int, int]]:
    """Fast os.scandir-based discovery returning `(rel, path_str, domain, evergreen, mtime, mtime_ns, size)`."""
    root_str = str(ROOT)
    root_prefix_len = len(root_str) + (0 if root_str.endswith(os.sep) else 1)
    found: dict[str, tuple[str, str, bool, float, int, int]] = {}

    def _add_stat(p_str: str, st: os.stat_result, domain: str, evergreen: bool) -> None:
        if st.st_size > 1_000_000:
            return
        if p_str.startswith(root_str):
            rel = p_str[root_prefix_len:].replace("\\", "/")
        else:
            rel = Path(p_str).relative_to(ROOT).as_posix()
        found[rel] = (p_str, domain, evergreen, st.st_mtime, st.st_mtime_ns, st.st_size)

    def _add_file(p: Path, domain: str, evergreen: bool) -> None:
        if p.suffix.lower() != ".md":
            return
        try:
            st = p.stat()
        except OSError:
            return
        p_str = str(p)
        if not os.path.isfile(p_str):
            return
        _add_stat(p_str, st, domain, evergreen)

    def _scan_md_dir(
        folder: Path,
        domain: str,
        evergreen: bool,
        *,
        skip_names: set[str] | None = None,
        skip_prefix: str | None = None,
        only_prefix: str | None = None,
        non_evergreen_name: str | None = None,
        record_names: set[str] | None = None,
    ) -> None:
        try:
            with os.scandir(folder) as it:
                for entry in it:
                    name = entry.name
                    if not name.lower().endswith(".md"):
                        continue
                    if skip_names and name in skip_names:
                        continue
                    if skip_prefix and name.startswith(skip_prefix):
                        continue
                    if only_prefix and not name.startswith(only_prefix):
                        continue
                    try:
                        if not entry.is_file():
                            continue
                        st = entry.stat()
                    except OSError:
                        continue
                    if st.st_size > 1_000_000:
                        continue
                    is_ev = evergreen and (name != non_evergreen_name)
                    _add_stat(entry.path, st, domain, is_ev)
                    if record_names is not None:
                        record_names.add(name)
        except OSError:
            return

    # 1. Owner profile, curiosity journal, decisions (Private-First override when private_vault/owner exists)
    private_owner_names: set[str] = set()
    _scan_md_dir(
        ROOT / "private_vault/owner",
        "owner",
        True,
        non_evergreen_name="CURIOSITY-LOG.md",
        record_names=private_owner_names,
    )
    _scan_md_dir(
        ROOT / "knowledge/owner",
        "owner",
        True,
        skip_names=private_owner_names,
        non_evergreen_name="CURIOSITY-LOG.md",
    )
    _scan_md_dir(ROOT / "knowledge/topics", "knowledge", True)
    _scan_md_dir(ROOT / "knowledge/playbooks", "knowledge", True)
    _add_file(ROOT / "knowledge/README.md", "knowledge", True)

    # 2. Workspace routing, lifecycle & morning briefings
    for name in ("planning/CURRENT-CONTEXT.md", "planning/CONTEXT-LIFECYCLE.md", "README.md"):
        _add_file(ROOT / name, "workspace", True)
    _scan_md_dir(ROOT / "planning", "workspace", False, only_prefix="MORNING-BRIEFING")

    # 3. Trading research reports (excluding archive index unless requested)
    _scan_md_dir(
        ROOT / "planning/research",
        "trading_research",
        False,
        skip_prefix=None if include_archive else "ARCHIVE-INDEX",
    )

    # 4. Architecture, workflow & search docs
    for folder in ("docs/development", "tooling/search", "tooling/ai-engines"):
        _scan_md_dir(ROOT / folder, "docs", True)

    # 5. Repo skills (single os.scandir walk instead of dual Path.rglob)
    sk_dir = ROOT / ".agents/skills"
    if sk_dir.is_dir():
        stack = [str(sk_dir)]
        while stack:
            cur = stack.pop()
            cur_name = os.path.basename(cur)
            try:
                with os.scandir(cur) as it:
                    for entry in it:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                            elif entry.is_file():
                                if entry.name == "SKILL.md" or (
                                    cur_name == "references" and entry.name.lower().endswith(".md")
                                ):
                                    st = entry.stat()
                                    _add_stat(entry.path, st, "skill", True)
                        except OSError:
                            continue
            except OSError:
                continue

    return [(rel, p, dom, ev, mt, mns, sz) for rel, (p, dom, ev, mt, mns, sz) in sorted(found.items())]


def iter_knowledge_docs(*, include_archive: bool = False) -> list[tuple[str, Path, str, bool]]:
    """Discover all maintained Markdown sources across the workspace with clear domain & evergreen flags."""
    return [(rel, Path(p), dom, ev) for rel, p, dom, ev, *_ in _iter_knowledge_docs_with_stat(include_archive=include_archive)]


def chunk_markdown(text: str, rel_path: str) -> list[dict]:
    """Split Markdown by heading boundaries so retrieved snippets keep intact structure & line numbers."""
    lines = text.splitlines()
    chunks = []
    cur_heading = Path(rel_path).stem
    cur_lines: list[str] = []
    cur_start = 1

    def _flush(end_line: int) -> None:
        body = "\n".join(cur_lines).strip()
        if not body:
            return
        # Cap oversized single sections cleanly into ~1,800-char sub-chunks
        if len(body) <= 2000:
            chunks.append({"heading": cur_heading, "line_start": cur_start, "line_end": end_line, "body": body})
        else:
            step = 1800
            for off in range(0, len(body), step):
                part = body[off:off + step].strip()
                if part:
                    chunks.append({"heading": cur_heading, "line_start": cur_start, "line_end": end_line, "body": part})

    for idx, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line)
        if m:
            _flush(idx - 1)
            cur_heading = m.group(2).strip()
            cur_lines = [line]
            cur_start = idx
        else:
            cur_lines.append(line)
    _flush(len(lines))
    return chunks


def _init_db(conn: sqlite3.Connection) -> None:
    """Create tables/triggers if missing and seamlessly auto-migrate legacy schemas in place."""
    stmts = (
        """
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            sha256 TEXT NOT NULL,
            domain TEXT NOT NULL,
            evergreen INTEGER NOT NULL,
            updated_ts REAL NOT NULL,
            chunk_count INTEGER NOT NULL,
            mtime_ns INTEGER,
            file_size INTEGER
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            heading TEXT NOT NULL,
            line_start INTEGER NOT NULL,
            line_end INTEGER NOT NULL,
            domain TEXT NOT NULL,
            evergreen INTEGER NOT NULL,
            updated_ts REAL NOT NULL,
            body TEXT NOT NULL,
            vec_blob BLOB
        )
        """,
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            heading, body, content='chunks', content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        )
        """,
        """
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, heading, body) VALUES (new.id, new.heading, new.body);
        END
        """,
        """
        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, heading, body) VALUES('delete', old.id, old.heading, old.body);
        END
        """,
        "CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path)",
        "CREATE INDEX IF NOT EXISTS idx_chunks_domain ON chunks(domain)",
    )
    for sql in stmts:
        conn.execute(sql)

    chunk_cols = {r[1] for r in conn.execute("PRAGMA table_info(chunks)").fetchall()}
    if "vec_blob" not in chunk_cols:
        conn.execute("ALTER TABLE chunks ADD COLUMN vec_blob BLOB")

    file_cols = {r[1] for r in conn.execute("PRAGMA table_info(files)").fetchall()}
    if "mtime_ns" not in file_cols:
        conn.execute("ALTER TABLE files ADD COLUMN mtime_ns INTEGER")
    if "file_size" not in file_cols:
        conn.execute("ALTER TABLE files ADD COLUMN file_size INTEGER")


def _backfill_null_vec_blobs(conn: sqlite3.Connection) -> int:
    """Populate `vec_blob` for any legacy rows migrated via ALTER TABLE (reusing legacy VEC_PATH if valid)."""
    null_rows = conn.execute("SELECT id, heading, body FROM chunks WHERE vec_blob IS NULL").fetchall()
    if not null_rows:
        return 0

    legacy_map: dict[int, bytes] = {}
    if VEC_PATH.is_file():
        try:
            with np.load(VEC_PATH, allow_pickle=False) as z:
                if "ids" in z and "vecs" in z:
                    l_ids = z["ids"]
                    l_vecs = np.asarray(z["vecs"], dtype=np.float32)
                    if l_vecs.ndim == 2 and l_vecs.shape[1] == VEC_DIM and len(l_ids) == len(l_vecs):
                        for cid, row_vec in zip(l_ids, l_vecs, strict=True):
                            legacy_map[int(cid)] = row_vec.tobytes()
        except Exception:
            legacy_map = {}

    updates: list[tuple[bytes, int]] = []
    for cid, heading, body in null_rows:
        cid_i = int(cid)
        blob = legacy_map.get(cid_i)
        if blob is None or len(blob) != _VEC_BYTES:
            blob = _hash_vector(f"{heading}\n{body}").astype(np.float32, copy=False).tobytes()
        updates.append((blob, cid_i))
    conn.executemany("UPDATE chunks SET vec_blob = ? WHERE id = ?", updates)
    return len(updates)


def index_brain(*, force: bool = False, include_archive: bool = False) -> dict:
    """Incrementally index all workspace Markdown knowledge using SHA-256 + per-chunk SQLite `vec_blob`."""
    t0 = time.perf_counter()
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)

    with _brain_write_lock():
        conn = _connect_db(DB_PATH, write=True)
        try:
            user_ver = int(conn.execute("PRAGMA user_version").fetchone()[0])
            if user_ver < 2:
                _init_db(conn)

            existing = {
                row[0]: (row[1], row[2], row[3])
                for row in conn.execute("SELECT path, sha256, mtime_ns, file_size FROM files").fetchall()
            }
            docs = _iter_knowledge_docs_with_stat(include_archive=include_archive)
            current_paths = {rel for rel, *_ in docs}
            now_wall = time.time()

            removed_paths = sorted(set(existing) - current_paths)
            meta_updates: list[tuple[int, int, str]] = []
            changed_docs: list[tuple[str, str, str, bool, float, int, int, list[tuple[dict, bytes]]]] = []
            unchanged = 0

            for rel, p_str, domain, evergreen, st_mtime, st_mtime_ns, st_size in docs:
                prev = existing.get(rel)
                if (
                    not force
                    and prev is not None
                    and prev[1] == st_mtime_ns
                    and prev[2] == st_size
                    and (now_wall - st_mtime) > _RACY_MTIME_WINDOW_SEC
                ):
                    unchanged += 1
                    continue

                with open(p_str, "rb") as fh_raw:
                    raw = fh_raw.read()
                digest = hashlib.sha256(raw).hexdigest()
                if not force and prev is not None and prev[0] == digest:
                    unchanged += 1
                    if prev[1] != st_mtime_ns or prev[2] != st_size:
                        meta_updates.append((st_mtime_ns, st_size, rel))
                    continue

                text = raw.decode("utf-8", errors="replace")
                chunks = chunk_markdown(text, rel)
                chunk_vecs = [
                    (ch, _hash_vector(f"{ch['heading']}\n{ch['body']}").astype(np.float32, copy=False).tobytes())
                    for ch in chunks
                ]
                changed_docs.append((rel, digest, domain, evergreen, st_mtime, st_mtime_ns, st_size, chunk_vecs))

            need_backfill = (not force) and (user_ver < 2) and (
                conn.execute("SELECT 1 FROM chunks WHERE vec_blob IS NULL LIMIT 1").fetchone() is not None
            )

            removed = 0
            updated = len(changed_docs)
            if force or removed_paths or changed_docs or meta_updates or need_backfill or user_ver < 2:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    if force:
                        conn.execute("DELETE FROM chunks")
                        conn.execute("DELETE FROM files")
                    else:
                        for old_path in removed_paths:
                            conn.execute("DELETE FROM chunks WHERE path = ?", (old_path,))
                            conn.execute("DELETE FROM files WHERE path = ?", (old_path,))
                            removed += 1

                    if meta_updates and not force:
                        conn.executemany(
                            "UPDATE files SET mtime_ns = ?, file_size = ? WHERE path = ?",
                            meta_updates,
                        )

                    for rel, digest, domain, evergreen, mtime, mtime_ns, file_size, chunk_vecs in changed_docs:
                        if not force:
                            conn.execute("DELETE FROM chunks WHERE path = ?", (rel,))
                        if chunk_vecs:
                            conn.executemany(
                                "INSERT INTO chunks(path, heading, line_start, line_end, domain, evergreen, updated_ts, body, vec_blob) "
                                "VALUES (?,?,?,?,?,?,?,?,?)",
                                [
                                    (
                                        rel,
                                        ch["heading"],
                                        ch["line_start"],
                                        ch["line_end"],
                                        domain,
                                        int(evergreen),
                                        mtime,
                                        ch["body"],
                                        vec_blob,
                                    )
                                    for ch, vec_blob in chunk_vecs
                                ],
                            )
                        conn.execute(
                            "INSERT OR REPLACE INTO files(path, sha256, domain, evergreen, updated_ts, chunk_count, mtime_ns, file_size) "
                            "VALUES (?,?,?,?,?,?,?,?)",
                            (rel, digest, domain, int(evergreen), mtime, len(chunk_vecs), mtime_ns, file_size),
                        )

                    if need_backfill:
                        _backfill_null_vec_blobs(conn)
                    if user_ver < 2:
                        conn.execute("PRAGMA user_version = 2")

                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise

            total_chunks = int(conn.execute("SELECT COALESCE(SUM(chunk_count), 0) FROM files").fetchone()[0])
            if force or user_ver < 2 or not VEC_PATH.exists() or VEC_PATH.stat().st_size > 4096:
                _write_vec_compat_marker(VEC_PATH)
        finally:
            conn.close()

    return {
        "db_path": str(DB_PATH.relative_to(ROOT).as_posix()),
        "files_total": len(docs),
        "files_updated": updated,
        "files_unchanged": unchanged,
        "files_removed": removed,
        "chunks_total": total_chunks,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
    }


def _extract_query_tokens(query: str) -> list[str]:
    """Extract informative, deduplicated bilingual query tokens (filtering VI+EN filler stopwords)."""
    raw_toks = [t for t in TOKEN_RE.findall(_strip_accents(query)) if len(t) >= 2]
    filtered = [t for t in raw_toks if t not in QUERY_STOPWORDS]
    chosen = filtered if filtered else raw_toks
    # Deduplicate preserving order, preferring informative domain tokens (digits/uppercase/longer words)
    seen: set[str] = set()
    uniq: list[str] = []
    for t in chosen:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    # Prioritize tokens containing digits or length >= 4 so domain terms (ftmo, the5ers, ibkr, us100, 500, cex) never get truncated
    uniq.sort(key=lambda t: (not any(ch.isdigit() for ch in t), len(t) < 4))
    return uniq[:18]


def rerank_hits_typesafe(
    query: str,
    hits: list[dict],
    *,
    top_k: int = 8,
    model: str = "jev-1.14.0",
    no_match_threshold: float = 0.30,
    transport=None,
) -> dict:
    """Rerank a Stage-1 shortlist using ONE batched TypeSafe (`jev-1.14.0`) request.

    Follows TypeSafe `rerank_typesafe` + `classifying_rag_passages` + companion Noul pattern:
      - One companion Noul (`has_relevant_doc`) detects absent/off-topic queries (`< 0.30 -> no_match`).
      - One per-candidate relevance Noul (`rel_doc_i`) scores every passage in parallel.
      - One Choice (`best_doc`) selects the single best passage for Top-1 boost.
    Raises `TypeSafeUnavailableError` / `TypeSafeAPIError` fail-closed if API fails.
    """
    if not hits:
        return {
            "enabled": True,
            "model": model,
            "has_relevant_doc_noul": 0.0,
            "no_match": True,
            "best_choice": None,
            "hits": [],
            "latency_ms": 0.0,
            "est_cost_usd": 0.0,
        }
    import sys as _sys
    qf_dir = ROOT / "tooling/ai-engines/quant_factory"
    if str(qf_dir) not in _sys.path:
        _sys.path.insert(0, str(qf_dir))
    import typesafe_client as ts  # type: ignore[import-not-found]  # noqa: WPS433

    shortlist = hits[:12]
    cand_map: dict[str, dict[str, str]] = {}
    choice_criteria: dict[str, str] = {}
    questions: dict[str, dict] = {
        "has_relevant_doc": {
            "type": "noul",
            "instructions": "Does at least one passage in `candidates` directly contain factual information that answers `user_query`?",
            "criteria": {
                "true": "One or more passages in `candidates` directly address the exact topic asked in `user_query`.",
                "false": "All passages in `candidates` are about unrelated topics and do not answer `user_query`.",
            },
        },
    }
    for idx, h in enumerate(shortlist, start=1):
        cid = f"doc_{idx}"
        cand_map[cid] = {
            "path": h["path"],
            "heading": h["heading"],
            "snippet": str(h.get("snippet", ""))[:500],
        }
        choice_criteria[cid] = f"Candidate `{cid}` ({h['path']} — {h['heading']}) best answers `user_query`."
        questions[f"rel_{cid}"] = {
            "type": "noul",
            "instructions": f"Does candidate `{cid}` in `candidates` directly answer or provide key facts for `user_query`?",
            "criteria": {
                "true": f"Candidate `{cid}` directly addresses the specific topic in `user_query`.",
                "false": f"Candidate `{cid}` is tangential or unrelated to `user_query`.",
            },
        }
    questions["best_doc"] = {
        "type": "choice",
        "instructions": "Which single candidate in `candidates` best answers `user_query`?",
        "criteria": choice_criteria,
    }

    res = ts.call_system_one(
        {"user_query": query, "candidates": cand_map},
        questions,
        model=model,
        transport=transport,
    )
    answers = res["answers"]
    has_rel = ts.extract_noul(answers, "has_relevant_doc")
    best_cid = (answers.get("best_doc") or {}).get("choice")
    best_conf = (answers.get("best_doc") or {}).get("confidence")
    no_match = has_rel < no_match_threshold

    reranked: list[dict] = []
    for idx, h in enumerate(shortlist, start=1):
        cid = f"doc_{idx}"
        rel_p = ts.extract_noul(answers, f"rel_{cid}")
        is_best = (cid == best_cid) and (not no_match)
        # Rank strictly by calibrated relevance probability (with small tie-break for Choice #1 & Stage-1 RRF)
        combined = round(rel_p + (0.08 if is_best else 0.0) + 0.02 * float(h["score"]), 5)
        item = dict(h)
        item["stage1_score"] = h["score"]
        item["typesafe_relevance_noul"] = round(rel_p, 4)
        item["typesafe_is_best_choice"] = is_best
        item["score"] = combined
        reranked.append(item)
    reranked.sort(key=lambda x: -x["score"])

    return {
        "enabled": True,
        "model": res["model"],
        "has_relevant_doc_noul": round(has_rel, 4),
        "no_match": no_match,
        "best_choice": best_cid,
        "best_choice_confidence": round(float(best_conf), 4) if best_conf is not None else None,
        "latency_ms": res["latency_ms"],
        "usage": res["usage"],
        "est_cost_usd": res["est_cost_usd"],
        "hits": [] if no_match else reranked[:top_k],
        "rejected_shortlist_count": len(reranked) if no_match else 0,
    }


def query_brain(
    query: str,
    *,
    domain: str = "all",
    top_k: int = 8,
    rerank: str = "none",
    typesafe_model: str = "jev-1.14.0",
    typesafe_transport=None,
) -> dict:
    """Hybrid RRF retrieval combining SQLite FTS5 BM25 + Multilingual Hashed Vector Cosine + Evergreen Boost.

    Pass `rerank="typesafe"` (opt-in) to semantically rerank the Stage-1 Top-12 shortlist via
    TypeSafe `jev-1.14.0` with explicit `no_match` abstention. Default `rerank="none"` is 100% offline.
    """
    t0 = time.perf_counter()
    if not DB_PATH.exists() or not VEC_PATH.exists():
        index_brain()

    toks = _extract_query_tokens(query)
    fts_ranks: dict[int, int] = {}
    vec_ranks: dict[int, int] = {}
    meta_rows: dict[int, dict] = {}

    for attempt in range(6):
        conn = _connect_db(DB_PATH, write=False)
        conn.row_factory = sqlite3.Row
        try:
            user_ver = int(conn.execute("PRAGMA user_version").fetchone()[0])
            if user_ver < 2:
                cols = {r[1] for r in conn.execute("PRAGMA table_info(chunks)").fetchall()}
                need_migrate = (
                    "vec_blob" not in cols
                    or conn.execute("SELECT 1 FROM chunks WHERE vec_blob IS NULL LIMIT 1").fetchone() is not None
                )
                if need_migrate:
                    conn.close()
                    index_brain()
                    conn = _connect_db(DB_PATH, write=False)
                    conn.row_factory = sqlite3.Row

            # 1. FTS5 BM25 search with VI+EN stopword removal so informative domain tokens never get truncated
            fts_ranks = {}
            if toks:
                fts_expr = " OR ".join(f'"{t}"' for t in toks)
                sql = """
                    SELECT c.id, bm25(chunks_fts, 2.0, 1.0) AS score
                    FROM chunks_fts
                    JOIN chunks c ON c.id = chunks_fts.rowid
                    WHERE chunks_fts MATCH ?
                """
                params: list = [fts_expr]
                if domain != "all":
                    sql += " AND c.domain = ?"
                    params.append(domain)
                sql += " ORDER BY score LIMIT 80"
                for rank, row in enumerate(conn.execute(sql, params).fetchall(), start=1):
                    fts_ranks[int(row["id"])] = rank

            # 2. Vector cosine similarity loaded directly from SQLite `vec_blob` (zero .npz rebuild/contention)
            if domain == "all":
                vec_rows = conn.execute("SELECT id, vec_blob FROM chunks WHERE vec_blob IS NOT NULL ORDER BY id").fetchall()
            else:
                vec_rows = conn.execute(
                    "SELECT id, vec_blob FROM chunks WHERE domain = ? AND vec_blob IS NOT NULL ORDER BY id",
                    (domain,),
                ).fetchall()

            valid_ids: list[int] = []
            valid_blobs: list[bytes] = []
            for r in vec_rows:
                blob = r[1]
                if blob is not None and len(blob) == _VEC_BYTES:
                    valid_ids.append(int(r[0]))
                    valid_blobs.append(bytes(blob))

            vec_ranks = {}
            if valid_ids:
                ids = np.asarray(valid_ids, dtype=np.int64)
                vecs = np.frombuffer(b"".join(valid_blobs), dtype=np.float32).reshape(len(valid_ids), VEC_DIM)
                clean_q = " ".join(toks) if toks else query
                qv = _hash_vector(clean_q)
                sims = vecs @ qv
                order = np.argsort(-sims)[:80]
                rank_i = 0
                for idx in order:
                    if float(sims[idx]) <= 0.02:
                        break
                    rank_i += 1
                    vec_ranks[int(ids[idx])] = rank_i
                    if rank_i >= 60:
                        break

            cand_ids = set(fts_ranks) | set(vec_ranks)
            if not cand_ids:
                return {
                    "query": query,
                    "domain": domain,
                    "rerank": rerank,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
                    "hits": [],
                }

            placeholders = ",".join("?" for _ in cand_ids)
            meta_rows = {
                int(r["id"]): dict(r)
                for r in conn.execute(
                    f"SELECT id, path, heading, line_start, line_end, domain, evergreen, updated_ts, body FROM chunks WHERE id IN ({placeholders})",
                    tuple(cand_ids),
                )
            }
            break
        except sqlite3.OperationalError as exc:
            msg = str(exc).lower()
            if ("locked" in msg or "busy" in msg or "no such table" in msg) and attempt + 1 < 6:
                time.sleep(0.02 * (attempt + 1))
                continue
            raise
        finally:
            conn.close()

    # 3. Reciprocal Rank Fusion (RRF) + Evergreen protection & mild temporal decay
    now_ts = time.time()
    scored: list[dict[str, Any]] = []
    for cid, m in meta_rows.items():
        rrf = 0.0
        if cid in fts_ranks:
            rrf += 1.35 / (35.0 + fts_ranks[cid])
        if cid in vec_ranks:
            rrf += 1.0 / (40.0 + vec_ranks[cid])
        if m["evergreen"]:
            rrf *= 1.15 if m["domain"] == "owner" else 1.08
        else:
            age_days = max(0.0, (now_ts - float(m["updated_ts"])) / 86400.0)
            rrf *= (0.80 + 0.20 * math.exp(-age_days / 180.0))
        snippet = re.sub(r"\s+", " ", m["body"]).strip()[:420]
        scored.append({
            "score": round(rrf, 5),
            "path": m["path"],
            "lines": f"L{m['line_start']}-L{m['line_end']}",
            "domain": m["domain"],
            "evergreen": bool(m["evergreen"]),
            "heading": m["heading"],
            "fts_rank": fts_ranks.get(cid),
            "vec_rank": vec_ranks.get(cid),
            "snippet": snippet,
        })
    scored.sort(key=lambda x: -float(x["score"]))

    if rerank == "typesafe":
        rr = rerank_hits_typesafe(
            query,
            scored[:max(12, top_k * 2)],
            top_k=top_k,
            model=typesafe_model,
            transport=typesafe_transport,
        )
        return {
            "query": query,
            "domain": domain,
            "rerank": "typesafe",
            "no_match": rr["no_match"],
            "typesafe_rerank": {k: v for k, v in rr.items() if k != "hits"},
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
            "hits": rr["hits"],
        }

    return {
        "query": query,
        "domain": domain,
        "rerank": "none",
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
        "hits": scored[:top_k],
    }


def owner_brief() -> str:
    prof_p = resolve_owner_file("PROFILE.md")
    cur_p = resolve_owner_file("CURIOSITY-LOG.md")
    dec_p = resolve_owner_file("DECISIONS-JOURNAL.md")
    prof = prof_p.read_text(encoding="utf-8")
    cur_lines = cur_p.read_text(encoding="utf-8").splitlines()
    recent_cur = [l for l in cur_lines if l.startswith("- **[")][-5:]
    dec_lines = dec_p.read_text(encoding="utf-8").splitlines()
    recent_dec = [l for l in dec_lines if l.startswith("| `202")][-5:]
    src_dir = prof_p.parent.relative_to(ROOT).as_posix()
    out = [
        f"=== NAQEX OWNER BRIEF ({src_dir}) ===",
        prof.strip(),
        "\n--- Recent Curiosities (last 5) ---",
        *recent_cur,
        "\n--- Recent Strategic Decisions (last 5) ---",
        *recent_dec,
    ]
    return "\n".join(out)


def log_curiosity(topic: str, question: str, takeaway: str, source: str = "") -> dict:
    with _brain_write_lock():
        p = resolve_owner_file("CURIOSITY-LOG.md")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        text = p.read_text(encoding="utf-8")
        day_hdr = f"## {today}"
        src_str = f" Nguồn: {source}." if source else ""
        entry = f"- **[{topic}]** *{question}*\n  - **Tóm tắt / Kết quả:** {takeaway}{src_str}\n"
        if day_hdr in text:
            new_text = text.rstrip() + "\n" + entry
        else:
            new_text = text.rstrip() + f"\n\n{day_hdr}\n\n" + entry
        _atomic_write_text(p, new_text)
        idx_res = index_brain()
    return {"logged_to": str(p.relative_to(ROOT).as_posix()), "date": today, "index": idx_res}


def log_decision(decision: str, reason: str, revisit: str) -> dict:
    with _brain_write_lock():
        p = resolve_owner_file("DECISIONS-JOURNAL.md")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        row = f"| `{today}` | {decision} | {reason} | {revisit} |\n"
        text = p.read_text(encoding="utf-8").rstrip() + "\n" + row
        _atomic_write_text(p, text)
        idx_res = index_brain()
    return {"logged_to": str(p.relative_to(ROOT).as_posix()), "date": today, "index": idx_res}


def _dir_size_and_count(path: Path) -> tuple[int, int]:
    """Fast recursive file size + count using os.scandir (reuses Windows FindNextFile metadata)."""
    total_bytes = 0
    count = 0
    stack = [str(path)]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            count += 1
                            total_bytes += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total_bytes, count


def _iter_non_code_lines(text: str):
    """Yield (line_no, line) skipping YAML frontmatter and fenced code blocks."""
    lines = text.splitlines()
    in_fence = False
    in_frontmatter = False
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if idx == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield idx, line


def _clean_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1:target.index(">")].strip()
    else:
        # Drop optional Markdown title suffix e.g. path.md "Title"
        target = re.split(r'\s+(?=["\'])', target, maxsplit=1)[0].strip()
    return target


def find_broken_knowledge_links(root: Path | None = None) -> list[dict]:
    """Detect broken relative Markdown links inside maintained `knowledge/` docs (excluding gitignored `inbox/`)."""
    base = root if root is not None else ROOT
    kb_dir = base / "knowledge"
    if not kb_dir.is_dir():
        return []
    broken: list[dict] = []
    for md_file in sorted(kb_dir.rglob("*.md")):
        rel_parts = md_file.relative_to(kb_dir).parts
        if rel_parts and rel_parts[0] == "inbox":
            continue
        text = md_file.read_text(encoding="utf-8", errors="replace")
        for line_no, line in _iter_non_code_lines(text):
            cleaned_line = INLINE_CODE_RE.sub("", line)
            for m in MD_LINK_RE.finditer(cleaned_line):
                raw_target = _clean_link_target(m.group(1))
                if not raw_target or raw_target.startswith("#"):
                    continue
                low = raw_target.lower()
                if low.startswith(("http://", "https://", "mailto:", "file://", "conversation://", "tel:", "data:")):
                    continue
                path_only = raw_target.split("#", 1)[0].split("?", 1)[0].strip()
                if not path_only:
                    continue
                path_only = unquote(path_only)
                resolved = (md_file.parent / path_only).resolve()
                if not resolved.exists():
                    broken.append({
                        "file": md_file.relative_to(base).as_posix(),
                        "line": line_no,
                        "target": raw_target,
                    })
    return broken


def _normalize_heading_tokens(heading: str) -> tuple[str, set[str]]:
    norm = _strip_accents(heading)
    norm = re.sub(r"[`*_~]", "", norm)
    norm = LEADING_SECTION_NUM_RE.sub("", norm).strip()
    norm = re.sub(r"\s+", " ", norm)
    raw_toks = TOKEN_RE.findall(norm)
    filtered = {t for t in raw_toks if t not in HEADING_STOPWORDS}
    toks = filtered if len(filtered) >= 2 else set(raw_toks)
    return norm, toks


def find_near_duplicate_topic_headings(
    root: Path | None = None,
    *,
    similarity_threshold: float = 0.70,
) -> list[dict]:
    """Detect exact or near-duplicate headings across `knowledge/topics/*.md` using diacritic-free token Jaccard & sequence similarity."""
    base = root if root is not None else ROOT
    topics_dir = base / "knowledge/topics"
    if not topics_dir.is_dir():
        return []

    records: list[tuple[str, int, str, str, set[str]]] = []
    for md_file in sorted(topics_dir.glob("*.md")):
        rel = md_file.relative_to(base).as_posix()
        text = md_file.read_text(encoding="utf-8", errors="replace")
        for line_no, line in _iter_non_code_lines(text):
            m = HEADING_RE.match(line)
            if not m:
                continue
            heading_txt = m.group(2).strip()
            norm, toks = _normalize_heading_tokens(heading_txt)
            if not norm:
                continue
            records.append((rel, line_no, heading_txt, norm, toks))

    dups: list[dict] = []
    for i in range(len(records)):
        rel_a, line_a, h_a, norm_a, toks_a = records[i]
        for j in range(i + 1, len(records)):
            rel_b, line_b, h_b, norm_b, toks_b = records[j]
            sim = 0.0
            if norm_a == norm_b:
                sim = 1.0
            else:
                union = toks_a | toks_b
                jaccard = (len(toks_a & toks_b) / len(union)) if union else 0.0
                seq_ratio = (
                    SequenceMatcher(None, norm_a, norm_b).ratio()
                    if min(len(norm_a), len(norm_b)) >= 12
                    else 0.0
                )
                if jaccard >= similarity_threshold or seq_ratio >= 0.85:
                    sim = max(jaccard, seq_ratio)
            if sim >= similarity_threshold:
                dups.append({
                    "file_a": rel_a,
                    "line_a": line_a,
                    "heading_a": h_a,
                    "file_b": rel_b,
                    "line_b": line_b,
                    "heading_b": h_b,
                    "similarity": round(sim, 3),
                })
    dups.sort(key=lambda x: (-x["similarity"], x["file_a"], x["line_a"]))
    return dups


def audit_data() -> dict:
    """Read-only workspace data hygiene & knowledge index health audit."""
    rt = ROOT / ".runtime"
    empty_tmp_dirs: list[str] = []
    heavy_rt_dirs: list[dict[str, Any]] = []
    if rt.is_dir():
        for d in sorted(rt.iterdir()):
            if not d.is_dir():
                continue
            total_b, f_count = _dir_size_and_count(d)
            sz_mb = total_b / (1024 * 1024)
            if f_count == 0 and any(tok in d.name.lower() for tok in ("tmp", "temp", "smoke", "dry", "quant-suite-")):
                empty_tmp_dirs.append(d.name)
            elif sz_mb >= 200.0:
                heavy_rt_dirs.append({"dir": d.name, "size_mb": round(sz_mb, 1), "files": f_count})
    heavy_rt_dirs.sort(key=lambda x: -float(x["size_mb"]))

    pr_count = len(list((ROOT / "planning/research").glob("*"))) if (ROOT / "planning/research").is_dir() else 0
    kb_count = len(list((ROOT / "knowledge").rglob("*.md"))) if (ROOT / "knowledge").is_dir() else 0
    db_ok = DB_PATH.exists() and VEC_PATH.exists()
    db_kb = round((DB_PATH.stat().st_size + VEC_PATH.stat().st_size) / 1024.0, 1) if db_ok else 0.0
    broken_links = find_broken_knowledge_links(ROOT)
    near_dup_headings = find_near_duplicate_topic_headings(ROOT)
    return {
        "brain_index_ready": db_ok,
        "brain_index_kb": db_kb,
        "owner_source": resolve_owner_file("PROFILE.md").parent.relative_to(ROOT).as_posix(),
        "knowledge_md_files": kb_count,
        "planning_research_files": pr_count,
        "dead_empty_runtime_dirs": empty_tmp_dirs,
        "heavy_runtime_dirs_ge_200mb": heavy_rt_dirs,
        "broken_knowledge_links_count": len(broken_links),
        "broken_knowledge_links": broken_links,
        "near_duplicate_topic_headings_count": len(near_dup_headings),
        "near_duplicate_topic_headings": near_dup_headings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Naqex Knowledge Brain CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_idx = sub.add_parser("index")
    p_idx.add_argument("--force", action="store_true")
    p_idx.add_argument("--include-archive", action="store_true")

    p_q = sub.add_parser("query")
    p_q.add_argument("text")
    p_q.add_argument("--domain", default="all", choices=("all", "owner", "knowledge", "workspace", "trading_research", "docs", "skill"))
    p_q.add_argument("--top", type=int, default=8)
    p_q.add_argument("--rerank", default="none", choices=("none", "typesafe"), help="Optional Stage-2 semantic reranker (default: none/offline).")
    p_q.add_argument("--model", default="jev-1.14.0", help="Pinned TypeSafe model ID when --rerank typesafe.")
    p_q.add_argument("--json", action="store_true", dest="as_json")

    sub.add_parser("owner-brief")

    p_cur = sub.add_parser("log-curiosity")
    p_cur.add_argument("--topic", required=True)
    p_cur.add_argument("--question", required=True)
    p_cur.add_argument("--takeaway", required=True)
    p_cur.add_argument("--source", default="")

    p_dec = sub.add_parser("log-decision")
    p_dec.add_argument("--decision", required=True)
    p_dec.add_argument("--reason", required=True)
    p_dec.add_argument("--revisit", required=True)

    sub.add_parser("audit-data")

    args = ap.parse_args()
    if args.cmd == "index":
        print(json.dumps(index_brain(force=args.force, include_archive=args.include_archive), indent=2, ensure_ascii=False))
    elif args.cmd == "query":
        res = query_brain(args.text, domain=args.domain, top_k=args.top, rerank=args.rerank, typesafe_model=args.model)
        if args.as_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            extra = f", rerank={res.get('rerank', 'none')}"
            if res.get("no_match"):
                extra += ", NO_MATCH"
            print(f"Brain Query ({res['elapsed_ms']}ms, domain={res['domain']}{extra}): {res['query']}")
            if res.get("no_match"):
                rr = res.get("typesafe_rerank", {})
                print(f"  [NO MATCH] has_relevant_doc={rr.get('has_relevant_doc_noul')} (< 0.30) — rejected {rr.get('rejected_shortlist_count', 0)} unrelated candidates.")
            for i, h in enumerate(res["hits"], 1):
                tag = "EVERGREEN" if h["evergreen"] else "DATED"
                rel_s = f"|jev={h['typesafe_relevance_noul']:.2f}" if "typesafe_relevance_noul" in h else ""
                print(f"  {i}. [{h['domain']}|{tag}|score={h['score']:.4f}{rel_s}] {h['path']}#{h['lines']} — {h['heading']}")
                print(f"     {h['snippet'][:200]}")
    elif args.cmd == "owner-brief":
        print(owner_brief())
    elif args.cmd == "log-curiosity":
        print(json.dumps(log_curiosity(args.topic, args.question, args.takeaway, args.source), indent=2, ensure_ascii=False))
    elif args.cmd == "log-decision":
        print(json.dumps(log_decision(args.decision, args.reason, args.revisit), indent=2, ensure_ascii=False))
    elif args.cmd == "audit-data":
        print(json.dumps(audit_data(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
