"""Naqex Knowledge Brain CLI: Local-First Markdown Source-of-Truth + Disposable SQLite FTS5 & Hybrid Vector Index.

Zero daemon, zero external API keys, Vietnamese diacritic-aware FTS5 (`unicode61 remove_diacritics 2`)
fused via Reciprocal Rank Fusion (RRF) with char/word TF-IDF cosine similarity and Evergreen preservation.

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
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time
import unicodedata

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BRAIN_DIR = ROOT / ".runtime/knowledge"
DB_PATH = BRAIN_DIR / "brain.sqlite3"
VEC_PATH = BRAIN_DIR / "brain_vec.npz"

HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
TOKEN_RE = re.compile(r"[0-9a-zA-Z\u00C0-\u024F\u1E00-\u1EFF\u4E00-\u9FFF\u0400-\u04FF_]{2,}")
VEC_DIM = 512  # Compact hashed feature space (zero-pickle float32 matrix -> < 5 MB, < 10 ms dot product)


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


def iter_knowledge_docs(*, include_archive: bool = False) -> list[tuple[str, Path, str, bool]]:
    """Discover all maintained Markdown sources across the workspace with clear domain & evergreen flags."""
    found: dict[str, tuple[Path, str, bool]] = {}

    def _add(p: Path, domain: str, evergreen: bool) -> None:
        if not p.is_file() or p.suffix.lower() != ".md" or p.stat().st_size > 1_000_000:
            return
        rel = p.relative_to(ROOT).as_posix()
        found[rel] = (p, domain, evergreen)

    # 1. Owner profile, curiosity journal, decisions & synthesized topics
    for p in sorted((ROOT / "knowledge/owner").glob("*.md")):
        is_ev = p.name != "CURIOSITY-LOG.md"
        _add(p, "owner", is_ev)
    for p in sorted((ROOT / "knowledge/topics").glob("*.md")):
        _add(p, "knowledge", True)
    _add(ROOT / "knowledge/README.md", "knowledge", True)

    # 2. Workspace routing & lifecycle
    for name in ("planning/CURRENT-CONTEXT.md", "planning/CONTEXT-LIFECYCLE.md", "README.md"):
        _add(ROOT / name, "workspace", True)

    # 3. Trading research reports (excluding archive index unless requested)
    pr = ROOT / "planning/research"
    if pr.is_dir():
        for p in sorted(pr.glob("*.md")):
            if not include_archive and p.name.startswith("ARCHIVE-INDEX"):
                continue
            _add(p, "trading_research", False)

    # 4. Architecture, workflow & search docs
    for folder in ("docs/development", "tooling/search", "tooling/ai-engines"):
        d = ROOT / folder
        if d.is_dir():
            for p in sorted(d.glob("*.md")):
                _add(p, "docs", True)

    # 5. Repo skills
    sk_dir = ROOT / ".agents/skills"
    if sk_dir.is_dir():
        for p in sorted(sk_dir.rglob("SKILL.md")):
            _add(p, "skill", True)
        for p in sorted(sk_dir.rglob("references/*.md")):
            _add(p, "skill", True)

    return [(rel, p, dom, ev) for rel, (p, dom, ev) in sorted(found.items())]


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
    conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            sha256 TEXT NOT NULL,
            domain TEXT NOT NULL,
            evergreen INTEGER NOT NULL,
            updated_ts REAL NOT NULL,
            chunk_count INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            heading TEXT NOT NULL,
            line_start INTEGER NOT NULL,
            line_end INTEGER NOT NULL,
            domain TEXT NOT NULL,
            evergreen INTEGER NOT NULL,
            updated_ts REAL NOT NULL,
            body TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            heading, body, content='chunks', content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, heading, body) VALUES (new.id, new.heading, new.body);
        END;
        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, heading, body) VALUES('delete', old.id, old.heading, old.body);
        END;
    """)


def index_brain(*, force: bool = False, include_archive: bool = False) -> dict:
    """Incrementally index all workspace Markdown knowledge using SHA-256 change detection."""
    t0 = time.perf_counter()
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    if force and DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    _init_db(conn)

    existing = {row[0]: row[1] for row in conn.execute("SELECT path, sha256 FROM files")}
    docs = iter_knowledge_docs(include_archive=include_archive)
    current_paths = {rel for rel, *_ in docs}

    removed = 0
    for old_path in set(existing) - current_paths:
        conn.execute("DELETE FROM chunks WHERE path = ?", (old_path,))
        conn.execute("DELETE FROM files WHERE path = ?", (old_path,))
        removed += 1

    updated = 0
    unchanged = 0
    for rel, p, domain, evergreen in docs:
        raw = p.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if existing.get(rel) == digest and not force:
            unchanged += 1
            continue
        text = raw.decode("utf-8", errors="replace")
        chunks = chunk_markdown(text, rel)
        mtime = p.stat().st_mtime
        conn.execute("DELETE FROM chunks WHERE path = ?", (rel,))
        for ch in chunks:
            conn.execute(
                "INSERT INTO chunks(path, heading, line_start, line_end, domain, evergreen, updated_ts, body) VALUES (?,?,?,?,?,?,?,?)",
                (rel, ch["heading"], ch["line_start"], ch["line_end"], domain, int(evergreen), mtime, ch["body"]),
            )
        conn.execute(
            "INSERT OR REPLACE INTO files(path, sha256, domain, evergreen, updated_ts, chunk_count) VALUES (?,?,?,?,?,?)",
            (rel, digest, domain, int(evergreen), mtime, len(chunks)),
        )
        updated += 1
    conn.commit()

    # Rebuild compact zero-pickle vector matrix only if index changed or vector file missing
    total_chunks = int(conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
    if updated > 0 or removed > 0 or not VEC_PATH.exists():
        rows = conn.execute("SELECT id, heading, body FROM chunks ORDER BY id").fetchall()
        ids = np.array([r[0] for r in rows], dtype=np.int64)
        vecs = np.vstack([_hash_vector(f"{r[1]}\n{r[2]}") for r in rows]) if rows else np.empty((0, VEC_DIM), dtype=np.float32)
        np.savez(VEC_PATH, ids=ids, vecs=vecs)
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


def query_brain(query: str, *, domain: str = "all", top_k: int = 8) -> dict:
    """Hybrid RRF retrieval combining SQLite FTS5 BM25 + Multilingual Hashed Vector Cosine + Evergreen Boost."""
    t0 = time.perf_counter()
    if not DB_PATH.exists() or not VEC_PATH.exists():
        index_brain()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 1. FTS5 BM25 search (OR-joined clean tokens for recall + exact phrase match)
    toks = [t for t in TOKEN_RE.findall(_strip_accents(query)) if len(t) >= 2]
    fts_ranks: dict[int, int] = {}
    if toks:
        fts_expr = " OR ".join(f'"{t}"' for t in toks[:12])
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
        sql += " ORDER BY score LIMIT 40"
        for rank, row in enumerate(conn.execute(sql, params).fetchall(), start=1):
            fts_ranks[int(row["id"])] = rank

    # 2. Vector cosine similarity across all chunks (< 5 ms matrix-vector multiply)
    z = np.load(VEC_PATH, allow_pickle=False)
    ids = z["ids"]
    vecs = z["vecs"]
    vec_ranks: dict[int, int] = {}
    if len(ids) > 0:
        qv = _hash_vector(query)
        sims = vecs @ qv
        order = np.argsort(-sims)[:60]
        if domain != "all":
            allowed_ids = {int(r[0]) for r in conn.execute("SELECT id FROM chunks WHERE domain = ?", (domain,))}
        else:
            allowed_ids = None
        rank_i = 0
        for idx in order:
            cid = int(ids[idx])
            if allowed_ids is not None and cid not in allowed_ids:
                continue
            if float(sims[idx]) <= 0.02:
                break
            rank_i += 1
            vec_ranks[cid] = rank_i
            if rank_i >= 40:
                break

    # 3. Reciprocal Rank Fusion (RRF) + Evergreen protection & mild temporal decay
    cand_ids = set(fts_ranks) | set(vec_ranks)
    if not cand_ids:
        conn.close()
        return {"query": query, "domain": domain, "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1), "hits": []}

    placeholders = ",".join("?" for _ in cand_ids)
    meta_rows = {
        int(r["id"]): dict(r)
        for r in conn.execute(f"SELECT id, path, heading, line_start, line_end, domain, evergreen, updated_ts, body FROM chunks WHERE id IN ({placeholders})", tuple(cand_ids))
    }
    conn.close()

    now_ts = time.time()
    scored = []
    for cid in cand_ids:
        m = meta_rows[cid]
        rrf = 0.0
        if cid in fts_ranks:
            rrf += 1.2 / (40.0 + fts_ranks[cid])
        if cid in vec_ranks:
            rrf += 1.0 / (40.0 + vec_ranks[cid])
        if m["evergreen"]:
            rrf *= 1.15 if m["domain"] == "owner" else 1.08
        else:
            age_days = max(0.0, (now_ts - float(m["updated_ts"])) / 86400.0)
            rrf *= (0.80 + 0.20 * math.exp(-age_days / 180.0))
        snippet = re.sub(r"\s+", " ", m["body"]).strip()[:280]
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
    scored.sort(key=lambda x: -x["score"])
    return {
        "query": query,
        "domain": domain,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1),
        "hits": scored[:top_k],
    }


def owner_brief() -> str:
    prof = (ROOT / "knowledge/owner/PROFILE.md").read_text(encoding="utf-8")
    cur_lines = (ROOT / "knowledge/owner/CURIOSITY-LOG.md").read_text(encoding="utf-8").splitlines()
    recent_cur = [l for l in cur_lines if l.startswith("- **[")][-5:]
    dec_lines = (ROOT / "knowledge/owner/DECISIONS-JOURNAL.md").read_text(encoding="utf-8").splitlines()
    recent_dec = [l for l in dec_lines if l.startswith("| `202")][-5:]
    out = [
        "=== NAQEX OWNER BRIEF ===",
        prof.strip(),
        "\n--- Recent Curiosities (last 5) ---",
        *recent_cur,
        "\n--- Recent Strategic Decisions (last 5) ---",
        *recent_dec,
    ]
    return "\n".join(out)


def log_curiosity(topic: str, question: str, takeaway: str, source: str = "") -> dict:
    p = ROOT / "knowledge/owner/CURIOSITY-LOG.md"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    text = p.read_text(encoding="utf-8")
    day_hdr = f"## {today}"
    src_str = f" Nguồn: {source}." if source else ""
    entry = f"- **[{topic}]** *{question}*\n  - **Tóm tắt / Kết quả:** {takeaway}{src_str}\n"
    if day_hdr in text:
        new_text = text.rstrip() + "\n" + entry
    else:
        new_text = text.rstrip() + f"\n\n{day_hdr}\n\n" + entry
    p.write_text(new_text, encoding="utf-8", newline="\n")
    idx_res = index_brain()
    return {"logged_to": str(p.relative_to(ROOT).as_posix()), "date": today, "index": idx_res}


def log_decision(decision: str, reason: str, revisit: str) -> dict:
    p = ROOT / "knowledge/owner/DECISIONS-JOURNAL.md"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = f"| `{today}` | {decision} | {reason} | {revisit} |\n"
    text = p.read_text(encoding="utf-8").rstrip() + "\n" + row
    p.write_text(text, encoding="utf-8", newline="\n")
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


def audit_data() -> dict:
    """Read-only workspace data hygiene & knowledge index health audit."""
    rt = ROOT / ".runtime"
    empty_tmp_dirs = []
    heavy_rt_dirs = []
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
    heavy_rt_dirs.sort(key=lambda x: -x["size_mb"])

    pr_count = len(list((ROOT / "planning/research").glob("*"))) if (ROOT / "planning/research").is_dir() else 0
    kb_count = len(list((ROOT / "knowledge").rglob("*.md"))) if (ROOT / "knowledge").is_dir() else 0
    db_ok = DB_PATH.exists() and VEC_PATH.exists()
    db_kb = round((DB_PATH.stat().st_size + VEC_PATH.stat().st_size) / 1024.0, 1) if db_ok else 0.0
    return {
        "brain_index_ready": db_ok,
        "brain_index_kb": db_kb,
        "knowledge_md_files": kb_count,
        "planning_research_files": pr_count,
        "dead_empty_runtime_dirs": empty_tmp_dirs,
        "heavy_runtime_dirs_ge_200mb": heavy_rt_dirs,
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
        res = query_brain(args.text, domain=args.domain, top_k=args.top)
        if args.as_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"Brain Query ({res['elapsed_ms']}ms, domain={res['domain']}): {res['query']}")
            for i, h in enumerate(res["hits"], 1):
                tag = "EVERGREEN" if h["evergreen"] else "DATED"
                print(f"  {i}. [{h['domain']}|{tag}|score={h['score']:.4f}] {h['path']}#{h['lines']} — {h['heading']}")
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
