"""Naqex Multi-Source Research CLI: EN/VI/CN/RU Web, Reddit JSON, arXiv, GitHub, PDF/Office & YouTube -> Clean Markdown.

Zero API keys required. Every fetched document receives provenance YAML frontmatter (`trust_tier`,
`content_sha256`, `fetched_utc`, `untrusted_external_data: true`) and optionally saves to `knowledge/inbox/`.

Usage:
  python -X utf8 tooling/knowledge/research_cli.py search "volatility targeting portfolio" --sources web,reddit,arxiv,cn,ru --max 4
  python -X utf8 tooling/knowledge/research_cli.py fetch "https://arxiv.org/abs/2305.00000" --mode directed --question "..." --save
  python -X utf8 tooling/knowledge/research_cli.py fetch "path/to/paper.pdf" --stdout
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote, urlparse
import warnings
import xml.etree.ElementTree as ET

warnings.filterwarnings("ignore", message=".*SOCKS.*")

ROOT = Path(__file__).resolve().parents[2]
INBOX_DIR = ROOT / "knowledge/inbox"
UA = "NaqexResearchAgent/1.0 (https://github.com/naqex; read-only)"

TIER1_DOMAINS = (
    "arxiv.org", "github.com", "docs.python.org", "developer.mozilla.org",
    "federalreserve.gov", "bls.gov", "mql5.com/en/docs", "ftmo.com", "the5ers.com",
    "sqlite.org", "numba.pydata.org", "learn.microsoft.com", "openai.com", "anthropic.com",
)
TIER2_DOMAINS = (
    "habr.com", "zhihu.com", "juejin.cn", "joinquant.com", "smart-lab.ru", "mql5.com",
    "towardsdatascience.com", "quantpedia.com", "ssrn.com", "substack.com", "medium.com",
)


def classify_trust_tier(url: str) -> str:
    low = url.lower()
    if any(d in low for d in TIER1_DOMAINS):
        return "T1_PRIMARY_OFFICIAL"
    if any(d in low for d in TIER2_DOMAINS):
        return "T2_TECHNICAL_COMMUNITY"
    if "reddit.com" in low or "news.ycombinator.com" in low or "forexfactory.com" in low:
        return "T3_FORUM_EXPERIENCE"
    return "T3_GENERAL_WEB"


def _ddgs_search(query: str, *, region: str = "wt-wt", max_results: int = 5) -> list[dict]:
    from ddgs import DDGS
    out = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, region=region, max_results=max_results):
            url = str(r.get("href") or r.get("url") or "").strip()
            if not url:
                continue
            out.append({
                "title": str(r.get("title", "")).strip(),
                "url": url,
                "snippet": str(r.get("body") or r.get("snippet") or "").strip()[:280],
                "trust_tier": classify_trust_tier(url),
            })
    return out


def _http_get(url: str, *, timeout: float = 15.0, headers: dict | None = None):
    import httpx
    hdrs = {"User-Agent": UA}
    if headers:
        hdrs.update(headers)
    with httpx.Client(timeout=timeout, headers=hdrs, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp


def _arxiv_search(query: str, *, max_results: int = 4) -> list[dict]:
    url = f"https://export.arxiv.org/api/query?search_query=all:{quote(query)}&start=0&max_results={max_results}&sortBy=relevance"
    resp = _http_get(url, timeout=15.0)
    root = ET.fromstring(resp.text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for entry in root.findall("a:entry", ns):
        title = re.sub(r"\s+", " ", (entry.findtext("a:title", "", ns) or "")).strip()
        link = (entry.findtext("a:id", "", ns) or "").strip()
        summ = re.sub(r"\s+", " ", (entry.findtext("a:summary", "", ns) or "")).strip()[:280]
        pub = (entry.findtext("a:published", "", ns) or "")[:10]
        if link:
            out.append({
                "title": f"[{pub}] {title}",
                "url": link,
                "snippet": summ,
                "trust_tier": "T1_PRIMARY_OFFICIAL",
            })
    return out


def _github_search(query: str, *, max_results: int = 4) -> list[dict]:
    try:
        p = subprocess.run(
            ["gh", "search", "repos", query, "--sort", "stars", "--limit", str(max_results), "--json", "fullName,url,description,stargazersCount"],
            capture_output=True, text=True, timeout=15,
        )
        if p.returncode == 0 and p.stdout.strip():
            items = json.loads(p.stdout)
            if items:
                return [{
                    "title": f"{it['fullName']} ({it.get('stargazersCount', 0)}★)",
                    "url": it["url"],
                    "snippet": str(it.get("description") or "")[:240],
                    "trust_tier": "T1_PRIMARY_OFFICIAL",
                } for it in items]
    except Exception:
        pass
    url = f"https://api.github.com/search/repositories?q={quote(query)}&sort=stars&per_page={max_results}"
    resp = _http_get(url, timeout=15.0, headers={"Accept": "application/vnd.github+json"})
    items = resp.json().get("items", [])
    return [{
        "title": f"{it['full_name']} ({it.get('stargazers_count', 0)}★)",
        "url": it["html_url"],
        "snippet": str(it.get("description") or "")[:240],
        "trust_tier": "T1_PRIMARY_OFFICIAL",
    } for it in items[:max_results]]


def _openalex_search(query: str, *, max_results: int = 4, lang: str = "") -> list[dict]:
    filt = f"&filter=language:{lang}" if lang else ""
    url = f"https://api.openalex.org/works?search={quote(query)}&per-page={max_results}{filt}"
    works = _http_get(url, timeout=15.0).json().get("results", [])
    out = []
    for w in works[:max_results]:
        title = str(w.get("display_name") or "").strip()
        yr = w.get("publication_year") or "?"
        cites = w.get("cited_by_count", 0)
        link = str(w.get("doi") or w.get("id") or "").strip()
        src_name = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
        if link:
            out.append({
                "title": f"[{yr}, {cites} cites] {title}",
                "url": link,
                "snippet": f"Source: {src_name}" if src_name else "OpenAlex academic work",
                "trust_tier": "T1_PRIMARY_OFFICIAL",
            })
    return out


def _hn_search(query: str, *, max_results: int = 4) -> list[dict]:
    url = f"https://hn.algolia.com/api/v1/search?query={quote(query)}&tags=story&hitsPerPage={max_results}"
    hits = _http_get(url, timeout=15.0).json().get("hits", [])
    out = []
    for h in hits[:max_results]:
        oid = h.get("objectID", "")
        link = str(h.get("url") or f"https://news.ycombinator.com/item?id={oid}").strip()
        pts = h.get("points", 0)
        cmts = h.get("num_comments", 0)
        out.append({
            "title": f"[HN {pts}p/{cmts}c] {h.get('title', '')}",
            "url": link,
            "snippet": f"HN thread: https://news.ycombinator.com/item?id={oid}",
            "trust_tier": "T3_FORUM_EXPERIENCE",
        })
    return out


def _quant_se_search(query: str, *, max_results: int = 4) -> list[dict]:
    url = f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance&q={quote(query)}&site=quant&pagesize={max_results}"
    items = _http_get(url, timeout=15.0).json().get("items", [])
    return [{
        "title": f"[QuantSE score={it.get('score', 0)}, ans={it.get('answer_count', 0)}] {it.get('title', '')}",
        "url": it.get("link", ""),
        "snippet": f"Tags: {', '.join(it.get('tags', []))}",
        "trust_tier": "T2_TECHNICAL_COMMUNITY",
    } for it in items[:max_results] if it.get("link")]


def _habr_ru_search(query: str, *, max_results: int = 4) -> list[dict]:
    url = f"https://habr.com/ru/rss/search/?q={quote(query)}&order_by=relevance"
    resp = _http_get(url, timeout=15.0)
    root = ET.fromstring(resp.text)
    out = []
    for item in root.findall("./channel/item")[:max_results]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = re.sub(r"<[^>]+>", " ", item.findtext("description") or "")
        desc = re.sub(r"\s+", " ", desc).strip()[:240]
        if link:
            out.append({
                "title": f"[Habr RU] {title}",
                "url": link,
                "snippet": desc,
                "trust_tier": "T2_TECHNICAL_COMMUNITY",
            })
    return out


def _wiki_search(query: str, *, lang: str = "en", max_results: int = 3) -> list[dict]:
    url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote(query)}&format=json&srlimit={max_results}"
    hits = _http_get(url, timeout=12.0).json().get("query", {}).get("search", [])
    out = []
    for h in hits[:max_results]:
        title = str(h.get("title") or "").strip()
        snip = re.sub(r"<[^>]+>", "", str(h.get("snippet") or "")).strip()[:240]
        out.append({
            "title": f"[Wiki {lang.upper()}] {title}",
            "url": f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
            "snippet": snip,
            "trust_tier": "T2_TECHNICAL_COMMUNITY",
        })
    return out


def _safe_call(fn, *args, **kwargs) -> list[dict]:
    try:
        return fn(*args, **kwargs)
    except Exception:
        return []


def _cn_search(query: str, *, max_results: int = 4) -> list[dict]:
    rows = _safe_call(_github_search, query, max_results=max(2, max_results // 2))
    rows += _safe_call(_openalex_search, query, max_results=max(1, max_results // 2), lang="zh")
    if len(rows) < max_results:
        rows += _safe_call(_wiki_search, query, lang="zh", max_results=max_results - len(rows))
    return rows[:max_results]


def _ru_search(query: str, *, max_results: int = 4) -> list[dict]:
    rows = _safe_call(_habr_ru_search, query, max_results=max_results)
    if len(rows) < max_results:
        rows += _safe_call(_wiki_search, query, lang="ru", max_results=max_results - len(rows))
    return rows[:max_results]


def _vi_search(query: str, *, max_results: int = 4) -> list[dict]:
    rows = _safe_call(_wiki_search, query, lang="vi", max_results=max(2, max_results // 2))
    rows += _safe_call(_openalex_search, query, max_results=max(2, max_results - len(rows)), lang="vi")
    return rows[:max_results]


def multi_source_search(query: str, *, sources: list[str], max_per_source: int = 4) -> dict:
    """Run parallel structured multi-source, multi-language research discovery with deduplication and trust-tier tagging."""
    buckets: dict[str, list[dict]] = {s: [] for s in sources}
    errors: dict[str, str] = {}
    seen: set[str] = set()

    def _run_one(src: str) -> tuple[str, list[dict], str | None]:
        try:
            if src == "arxiv":
                return src, _arxiv_search(query, max_results=max_per_source), None
            if src == "openalex":
                return src, _openalex_search(query, max_results=max_per_source), None
            if src == "github":
                return src, _github_search(query, max_results=max_per_source), None
            if src == "hn":
                return src, _hn_search(query, max_results=max_per_source), None
            if src == "quant":
                return src, _quant_se_search(query, max_results=max_per_source), None
            if src == "ru":
                return src, _ru_search(query, max_results=max_per_source), None
            if src == "cn":
                return src, _cn_search(query, max_results=max_per_source), None
            if src == "vi":
                return src, _vi_search(query, max_results=max_per_source), None
            if src == "web":
                return src, _ddgs_search(query, region="wt-wt", max_results=max_per_source), None
            if src == "reddit":
                return src, _ddgs_search(f"site:reddit.com {query}", region="wt-wt", max_results=max_per_source), None
            return src, [], f"Unknown source '{src}'"
        except Exception as exc:
            hint = " (use agent native search_web for open-web/Reddit if search engine throttles CLI)" if src in ("web", "reddit") else ""
            return src, [], f"{exc}{hint}"

    with ThreadPoolExecutor(max_workers=min(6, max(1, len(sources)))) as pool:
        futs = [pool.submit(_run_one, s) for s in sources]
        raw_results: dict[str, list[dict]] = {}
        for fut in as_completed(futs):
            src, rows, err = fut.result()
            if err:
                errors[src] = err
            raw_results[src] = rows

    for src in sources:
        clean = []
        for r in raw_results.get(src, []):
            u = r["url"].rstrip("/")
            if u and u not in seen:
                seen.add(u)
                clean.append(r)
        buckets[src] = clean

    return {
        "schema": "naqex-multisource-search-v1",
        "searched_utc": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "sources": sources,
        "results": buckets,
        "errors": errors,
    }


def _fetch_reddit_json(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    json_url = f"https://old.reddit.com{parsed.path.rstrip('/')}.json?limit=25&sort=top"
    data = _http_get(json_url, timeout=20.0).json()
    post = data[0]["data"]["children"][0]["data"]
    title = str(post.get("title", "Reddit Thread"))
    body = str(post.get("selftext", "")).strip()
    lines = [f"# {title}", f"*r/{post.get('subreddit', '')} | score={post.get('score', 0)}*", "", body, "", "## Top Comments"]
    for ch in data[1]["data"]["children"][:15]:
        cd = ch.get("data", {})
        if cd.get("body"):
            lines.append(f"- **[score={cd.get('score', 0)}, u/{cd.get('author', '?')}]** {str(cd['body']).strip()[:600]}")
    return title, "\n".join(lines)


def _fetch_youtube_transcript(url: str) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as td:
        out_tmpl = str(Path(td) / "%(title)s.%(ext)s")
        p = subprocess.run(
            ["yt-dlp", "--write-auto-sub", "--write-sub", "--sub-lang", "en,vi", "--skip-download", "-o", out_tmpl, url],
            capture_output=True, text=True, timeout=60,
        )
        vtts = sorted(Path(td).glob("*.vtt"))
        if not vtts:
            raise RuntimeError(f"No subtitles extracted via yt-dlp (rc={p.returncode})")
        raw = vtts[0].read_text(encoding="utf-8", errors="replace")
        # Strip VTT headers, timestamps & consecutive duplicate lines
        clean_lines = []
        prev = ""
        for ln in raw.splitlines():
            s = re.sub(r"<[^>]+>", "", ln).strip()
            if not s or s.startswith(("WEBVTT", "Kind:", "Language:")) or "-->" in s or s.isdigit():
                continue
            if s != prev:
                clean_lines.append(s)
                prev = s
        title = vtts[0].stem
        return title, f"# {title}\n\n" + "\n".join(clean_lines)


def _fetch_local_file(path: Path) -> tuple[str, str]:
    from markitdown import MarkItDown
    md = MarkItDown()
    res = md.convert(str(path))
    return path.name, str(res.text_content or "").strip()


def fetch_to_markdown(
    target: str,
    *,
    mode: str = "directed",
    question: str = "",
    save: bool = False,
) -> dict:
    """Convert any Web URL (EN/VI/CN/RU), Reddit thread, YouTube video, or local PDF/Office file to clean Markdown."""
    p_local = Path(target)
    if p_local.exists() and p_local.is_file():
        title, content = _fetch_local_file(p_local)
        trust = "T1_LOCAL_ARTIFACT"
        source_ref = str(p_local.resolve())
    elif "reddit.com" in target.lower() and "/comments/" in target.lower():
        title, content = _fetch_reddit_json(target)
        trust = "T3_FORUM_EXPERIENCE"
        source_ref = target
    elif "youtube.com/" in target.lower() or "youtu.be/" in target.lower():
        title, content = _fetch_youtube_transcript(target)
        trust = "T2_MEDIA_TRANSCRIPT"
        source_ref = target
    else:
        import trafilatura
        downloaded = trafilatura.fetch_url(target)
        if not downloaded:
            downloaded = _http_get(target, timeout=20.0).text
        extracted = trafilatura.extract(
            downloaded,
            output_format="markdown",
            include_tables=True,
            include_links=True,
            favor_precision=False,
        )
        if not extracted:
            raise RuntimeError(f"Could not extract clean article body from {target}")
        meta = trafilatura.extract_metadata(downloaded)
        title = (meta.title if meta and meta.title else urlparse(target).netloc) or "web-capture"
        content = extracted.strip()
        trust = classify_trust_tier(target)
        source_ref = target

    fetched_utc = datetime.now(timezone.utc).isoformat()
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    frontmatter = "\n".join([
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"source_url: {json.dumps(source_ref, ensure_ascii=False)}",
        f"fetched_utc: {fetched_utc}",
        f"trust_tier: {trust}",
        f"research_mode: {mode}",
        f"owner_question: {json.dumps(question, ensure_ascii=False)}",
        f"content_sha256: {digest[:16]}",
        "untrusted_external_data: true",
        "---",
        "",
    ])
    full_md = frontmatter + content + "\n"

    saved_path = None
    if save:
        INBOX_DIR.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")[:48] or "capture"
        day_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
        out_file = INBOX_DIR / f"{day_tag}-{slug}-{digest[:6]}.md"
        out_file.write_text(full_md, encoding="utf-8", newline="\n")
        saved_path = str(out_file.relative_to(ROOT).as_posix())

    return {
        "title": title,
        "source": source_ref,
        "trust_tier": trust,
        "chars": len(content),
        "content_sha256": digest[:16],
        "saved_path": saved_path,
        "markdown": full_md,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Naqex Multi-Source Research CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("search")
    ps.add_argument("query")
    ps.add_argument("--sources", default="arxiv,openalex,github,hn,quant")
    ps.add_argument("--max", type=int, default=4)
    ps.add_argument("--json", action="store_true", dest="as_json")

    pf = sub.add_parser("fetch")
    pf.add_argument("target")
    pf.add_argument("--mode", default="directed", choices=("autonomous", "directed"))
    pf.add_argument("--question", default="")
    pf.add_argument("--save", action="store_true")
    pf.add_argument("--stdout", action="store_true")

    args = ap.parse_args()
    if args.cmd == "search":
        srcs = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
        res = multi_source_search(args.query, sources=srcs, max_per_source=args.max)
        if args.as_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"Research Search [{', '.join(srcs)}]: {args.query}")
            for src, rows in res["results"].items():
                print(f"\n  [{src.upper()}] ({len(rows)} hits)")
                for r in rows:
                    print(f"   - ({r['trust_tier']}) {r['title']}\n     {r['url']}\n     {r['snippet'][:180]}")
            if res["errors"]:
                print(f"\n  Errors: {res['errors']}")
    elif args.cmd == "fetch":
        res = fetch_to_markdown(args.target, mode=args.mode, question=args.question, save=args.save)
        if args.stdout:
            print(res["markdown"])
        else:
            print(json.dumps({k: v for k, v in res.items() if k != "markdown"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
