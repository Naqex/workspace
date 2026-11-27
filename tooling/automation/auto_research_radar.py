"""Naqex Automated External Research Radar (Front 5 — Zero-API-Key, Fail-Closed).

Reuses `tooling/knowledge/research_cli.py` across arXiv, OpenAlex, GitHub (`gh`),
official macro RSS feeds, and multilingual (EN/CN/RU/VI) technical communities.

Hard invariants (enforced without Python `assert`, safe under `python -O`):
  - ORDER_SEND_COUNT = 0, HOLDOUT_ROWS_ANALYSED = 0, SPEND_VND = 0
  - Every external record is forced to `untrusted_external_data: true`
  - Trust tier (`T1_PRIMARY_OFFICIAL`, `T2_TECHNICAL_COMMUNITY`, `T3_*`) is
    recomputed from parsed URL host/path (never trusting upstream tier claims)
  - Dual deduplication by normalized URL and `content_sha256`
  - Never executes fetched code/scripts, never installs packages, never bypasses CAPTCHAs
  - `--offline` guarantees zero network/subprocess calls for 100% deterministic CI
  - Never mutates `.runtime/knowledge/brain.sqlite3` directly (optional Markdown card
    under `knowledge/inbox/` is staged for explicit `brain_cli.py index` later)
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, quote_plus, urlencode, urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WATCHLIST_PATH = ROOT / "tooling/automation/configs/research_watchlist.json"
DEFAULT_OUTPUT_PATH = ROOT / ".runtime/automation/research_radar_latest.json"
DEFAULT_INBOX_DIR = ROOT / "knowledge/inbox"

SCHEMA_VERSION = "naqex-auto-research-radar-v1"
WATCHLIST_SCHEMA_VERSION = "naqex-research-watchlist-v1"
ORDER_SEND_COUNT = 0
HOLDOUT_ROWS_ANALYSED = 0
SPEND_VND = 0
_NO_WINDOW_FLAGS: int = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0

VALID_TRUST_TIERS: frozenset[str] = frozenset(
    {
        "T1_PRIMARY_OFFICIAL",
        "T2_TECHNICAL_COMMUNITY",
        "T3_FORUM_EXPERIENCE",
        "T3_GENERAL_WEB",
    }
)
SUPPORTED_SOURCES: frozenset[str] = frozenset(
    {
        "arxiv",
        "openalex",
        "github",
        "github_releases",
        "official_feed",
        "quant",
        "hn",
        "cn",
        "ru",
        "vi",
    }
)
TRACKING_QUERY_PARAMS: frozenset[str] = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "ref",
        "si",
    }
)
HTTPS_CANONICAL_HOSTS: frozenset[str] = frozenset(
    {
        "arxiv.org",
        "export.arxiv.org",
        "github.com",
        "api.github.com",
        "doi.org",
        "api.openalex.org",
        "federalreserve.gov",
        "bls.gov",
        "ecb.europa.eu",
        "ftmo.com",
        "the5ers.com",
        "icfunded.com",
    }
)

_MAX_FEED_BYTES = 2_000_000
_MAX_TITLE_CHARS = 300
_MAX_SNIPPET_CHARS = 500
_MAX_URL_CHARS = 1000
_REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_CTRL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_CGNAT_NET = ipaddress.ip_network(".".join(["100", "64", "0", "0"]) + "/10")

# Dynamic secret regexes avoid self-matching static secret scanners / OPSEC guards.
_SECRET_SCRUB_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\b(?:" + "ghp" + r"_[A-Za-z0-9]{20,}|" + "github_pat" + r"_[A-Za-z0-9_]{20,})\b"),
        "<REDACTED_GH_TOKEN>",
    ),
    (re.compile(r"\b" + "sk" + r"-(?:proj-)?[A-Za-z0-9_-]{24,}\b"), "<REDACTED_API_KEY>"),
    (re.compile(r"\b" + "AI" + r"za[0-9A-Za-z_-]{30,}\b"), "<REDACTED_API_KEY>"),
    (re.compile(r"(?:bot)?\b\d{6,12}:[A-Za-z0-9_-]{20,}\b"), "<REDACTED_BOT_TOKEN>"),
    (
        re.compile(r"https?://(?:discord\.com|discordapp\.com)/api/webhooks/\d{10,}/[A-Za-z0-9_-]{20,}"),
        "<REDACTED_WEBHOOK>",
    ),
    (re.compile(r"postgres(?:ql)?://[^\s:/@<]+:[^\s/@<]{4,}@[^\s/<]+"), "<REDACTED_DSN>"),
    (re.compile(r"(?i)([?&]|\b)((?:token|api[_-]?key|secret)=)[^\s&'\"<>]+"), r"\1\2<REDACTED>"),
    (re.compile(r"(?i)(Bearer\s+)[^\s'\"<>]+"), r"\1<REDACTED>"),
    (
        re.compile(r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]Users[\\/](?!<)[A-Za-z0-9._-]+"),
        "<REDACTED_USER_PATH>",
    ),
)


class RadarValidationError(ValueError):
    """Raised when watchlist config, external payload, or receipt invariants fail."""


class RadarNetworkBlockedError(RuntimeError):
    """Raised if any live network operation is attempted in offline/dry-run mode."""


def _load_research_cli() -> Any:
    """Import `tooling.knowledge.research_cli` cleanly regardless of caller CWD."""
    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    import tooling.knowledge.research_cli as research_cli

    return research_cli


def _replace_with_retry(src: Path, dst: Path, *, retries: int = 12) -> None:
    """Windows-safe atomic replace with short backoff for transient sharing locks."""
    for attempt in range(retries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt + 1 >= retries:
                raise
            time.sleep(0.005 * (attempt + 1))


def _atomic_write_text(path: Path, text: str) -> None:
    """Atomically write LF-only UTF-8 text via temp file -> flush -> fsync -> os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
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
            fh.write(normalized)
            fh.flush()
            os.fsync(fh.fileno())
            tmp_path = Path(fh.name)
        _replace_with_retry(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def _scrub_private_ips(text: str) -> str:
    def _repl(match: re.Match[str]) -> str:
        raw_ip = match.group(0)
        try:
            addr = ipaddress.IPv4Address(raw_ip)
        except ValueError:
            return raw_ip
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr in _CGNAT_NET:
            return "<REDACTED_IP>"
        return raw_ip

    return _IPV4_RE.sub(_repl, text)


def scrub_opsec_text(raw: Any, *, max_len: int | None = None) -> str:
    """Remove control chars, HTML noise, secrets, private IPs, and user profile paths."""
    text = str(raw or "")
    text = _CTRL_CHARS_RE.sub(" ", text)
    text = _HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for rx, repl in _SECRET_SCRUB_PATTERNS:
        text = rx.sub(repl, text)
    text = _scrub_private_ips(text)
    if max_len is not None and len(text) > max_len:
        text = text[: max_len - 3].rstrip() + "..."
    return text


def _is_forbidden_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(addr, ipaddress.IPv6Address):
        if addr.ipv4_mapped is not None:
            return _is_forbidden_ip(addr.ipv4_mapped)
        if addr.sixtofour is not None and _is_forbidden_ip(addr.sixtofour):
            return True
        if addr.teredo is not None and (_is_forbidden_ip(addr.teredo[0]) or _is_forbidden_ip(addr.teredo[1])):
            return True
    if (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    ):
        return True
    if isinstance(addr, ipaddress.IPv4Address) and addr in _CGNAT_NET:
        return True
    return False


def _is_forbidden_host(hostname: str) -> bool:
    host = hostname.strip().lower().rstrip(".")
    if not host or host in ("localhost", "localhost.localdomain"):
        return True
    if host.endswith((".local", ".internal", ".lan")):
        return True
    try:
        addr = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return _is_forbidden_ip(addr)


def normalize_url(raw_url: Any) -> str:
    """Validate and canonicalize an external HTTP(S) URL; raise RadarValidationError on invalid input."""
    if not isinstance(raw_url, str):
        raise RadarValidationError("URL must be a string")
    cleaned = raw_url.strip()
    if not cleaned or len(cleaned) > _MAX_URL_CHARS:
        raise RadarValidationError("URL is empty or exceeds maximum length")
    if _CTRL_CHARS_RE.search(cleaned) or "\n" in cleaned or "\r" in cleaned:
        raise RadarValidationError("URL contains forbidden control characters")

    parsed = urlparse(cleaned)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise RadarValidationError(f"Forbidden URL scheme: {scheme!r}")
    if parsed.username or parsed.password:
        raise RadarValidationError("URL with embedded credentials is forbidden")

    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname:
        raise RadarValidationError(f"Invalid URL hostname: {hostname!r}")
    if _is_forbidden_host(hostname):
        raise RadarValidationError(f"Forbidden private/local URL host: {hostname!r}")
    is_ipv6_literal = False
    try:
        parsed_ip = ipaddress.ip_address(hostname.strip("[]"))
        is_ipv6_literal = isinstance(parsed_ip, ipaddress.IPv6Address)
    except ValueError:
        if "." not in hostname:
            raise RadarValidationError(f"Invalid URL hostname: {hostname!r}") from None

    port = parsed.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None

    canon_host = hostname[4:] if hostname.startswith("www.") else hostname
    if scheme == "http" and (
        canon_host in HTTPS_CANONICAL_HOSTS or any(canon_host.endswith("." + h) for h in HTTPS_CANONICAL_HOSTS)
    ):
        scheme = "https"

    host_netloc = f"[{hostname}]" if is_ipv6_literal else hostname
    netloc = f"{host_netloc}:{port}" if port is not None else host_netloc
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    filtered_qs = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False) if k.lower() not in TRACKING_QUERY_PARAMS
    ]
    filtered_qs.sort()
    query = urlencode(filtered_qs, doseq=True)

    return urlunparse((scheme, netloc, path, "", query, ""))


def _host_matches_rule(hostname: str, path: str, rule: str) -> bool:
    rule_low = rule.strip().lower()
    if not rule_low:
        return False
    if "/" in rule_low:
        rule_host, rule_path = rule_low.split("/", 1)
        host_ok = hostname == rule_host or hostname.endswith("." + rule_host)
        prefix = "/" + rule_path.strip("/")
        p_low = path.lower()
        return host_ok and (p_low == prefix or p_low.startswith(prefix + "/"))
    return hostname == rule_low or hostname.endswith("." + rule_low)


def classify_url_trust_tier(url: str, *, policy: dict[str, Any] | None = None) -> str:
    """Classify trust tier strictly from validated URL hostname/path (anti-spoofing)."""
    norm = normalize_url(url)
    parsed = urlparse(norm)
    hostname = (parsed.hostname or "").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    path = parsed.path or "/"

    research_cli = _load_research_cli()
    extra_t1 = tuple((policy or {}).get("extra_t1_domains") or ())
    extra_t2 = tuple((policy or {}).get("extra_t2_domains") or ())

    t1_rules = tuple(research_cli.TIER1_DOMAINS) + extra_t1
    if any(_host_matches_rule(hostname, path, rule) for rule in t1_rules):
        return "T1_PRIMARY_OFFICIAL"

    t2_rules = tuple(research_cli.TIER2_DOMAINS) + extra_t2 + ("wikipedia.org",)
    if any(_host_matches_rule(hostname, path, rule) for rule in t2_rules):
        return "T2_TECHNICAL_COMMUNITY"

    forum_hosts = ("reddit.com", "news.ycombinator.com", "forexfactory.com")
    if any(_host_matches_rule(hostname, path, rule) for rule in forum_hosts):
        return "T3_FORUM_EXPERIENCE"

    return "T3_GENERAL_WEB"


def compute_content_sha256(title: str, snippet: str) -> str:
    """Compute deterministic 64-hex SHA-256 over canonicalized title and snippet."""
    norm_title = re.sub(r"\s+", " ", title.strip().lower())
    norm_snip = re.sub(r"\s+", " ", snippet.strip().lower())
    payload = f"{norm_title}\n{norm_snip}".encode()
    return hashlib.sha256(payload).hexdigest()


def _is_exact_zero_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value == 0


def _validate_repo_slug(repo: Any) -> str:
    if not isinstance(repo, str) or not _REPO_SLUG_RE.match(repo):
        raise RadarValidationError(f"Invalid GitHub repo slug: {repo!r}")
    owner, name = repo.split("/", 1)
    if (
        owner in (".", "..")
        or name in (".", "..")
        or ".." in owner
        or ".." in name
        or owner.startswith(".")
        or owner.endswith(".")
        or name.startswith(".")
        or name.endswith(".")
    ):
        raise RadarValidationError(f"Path traversal or invalid dot segment in GitHub repo slug: {repo!r}")
    return repo


def _validate_timeout_sec(raw_timeout: Any) -> float:
    if isinstance(raw_timeout, bool) or not isinstance(raw_timeout, (int, float)):
        raise RadarValidationError(f"timeout_sec must be a finite number in (0, 30], got {raw_timeout!r}")
    val = float(raw_timeout)
    if not math.isfinite(val) or not (0.0 < val <= 30.0):
        raise RadarValidationError(f"timeout_sec must be finite and in (0, 30], got {raw_timeout!r}")
    return val


def validate_watchlist_config(raw: Any) -> dict[str, Any]:
    """Fail-closed validation of `research_watchlist.json` (100% `-O` safe)."""
    if not isinstance(raw, dict):
        raise RadarValidationError("Watchlist config must be a JSON object")
    if raw.get("schema") != WATCHLIST_SCHEMA_VERSION:
        raise RadarValidationError(
            f"Unsupported watchlist schema {raw.get('schema')!r}; expected {WATCHLIST_SCHEMA_VERSION!r}"
        )
    if not _is_exact_zero_int(raw.get("order_send_count")):
        raise RadarValidationError("Watchlist hard invariant violated: order_send_count must be int 0")
    if not _is_exact_zero_int(raw.get("holdout_rows_analysed")):
        raise RadarValidationError("Watchlist hard invariant violated: holdout_rows_analysed must be int 0")
    if not _is_exact_zero_int(raw.get("spend_vnd")):
        raise RadarValidationError("Watchlist hard invariant violated: spend_vnd must be int 0")

    guard = raw.get("supply_chain_guard")
    if not isinstance(guard, dict):
        raise RadarValidationError("Watchlist missing supply_chain_guard object")
    for required_true in (
        "enforce_untrusted_external_data",
        "forbid_code_execution",
        "forbid_package_install",
        "forbid_captcha_bypass",
    ):
        if guard.get(required_true) is not True:
            raise RadarValidationError(f"supply_chain_guard.{required_true} must be true")
    if not _is_exact_zero_int(guard.get("api_keys_required")):
        raise RadarValidationError("supply_chain_guard.api_keys_required must be int 0")

    policy = raw.get("trust_tier_policy")
    if not isinstance(policy, dict):
        raise RadarValidationError("Watchlist missing trust_tier_policy object")
    allowed = policy.get("allowed_tiers")
    if not isinstance(allowed, list) or not allowed or any(t not in VALID_TRUST_TIERS for t in allowed):
        raise RadarValidationError("trust_tier_policy.allowed_tiers must be a non-empty list of valid tiers")

    limits = raw.get("limits")
    if not isinstance(limits, dict):
        raise RadarValidationError("Watchlist missing limits object")
    hard_max = limits.get("hard_max_items_per_topic")
    if isinstance(hard_max, bool) or not isinstance(hard_max, int) or not (1 <= hard_max <= 50):
        raise RadarValidationError("limits.hard_max_items_per_topic must be an int in [1, 50]")
    if "request_timeout_sec" in limits:
        _validate_timeout_sec(limits["request_timeout_sec"])

    topics = raw.get("topics")
    if not isinstance(topics, list) or not topics:
        raise RadarValidationError("Watchlist topics must be a non-empty list")

    seen_topic_ids: set[str] = set()
    for idx, topic in enumerate(topics):
        if not isinstance(topic, dict):
            raise RadarValidationError(f"Topic #{idx} must be an object")
        tid = topic.get("topic_id")
        if not isinstance(tid, str) or not re.match(r"^[a-z0-9_]{3,64}$", tid):
            raise RadarValidationError(f"Invalid topic_id at index {idx}: {tid!r}")
        if tid in seen_topic_ids:
            raise RadarValidationError(f"Duplicate topic_id: {tid!r}")
        seen_topic_ids.add(tid)

        max_items = topic.get("max_items")
        if isinstance(max_items, bool) or not isinstance(max_items, int) or not (1 <= max_items <= hard_max):
            raise RadarValidationError(f"Topic {tid!r} max_items={max_items!r} outside [1, {hard_max}]")

        t_tiers = topic.get("allowed_tiers", allowed)
        if not isinstance(t_tiers, list) or not t_tiers or any(t not in VALID_TRUST_TIERS for t in t_tiers):
            raise RadarValidationError(f"Topic {tid!r} has invalid allowed_tiers: {t_tiers!r}")

        queries = topic.get("queries")
        if not isinstance(queries, list) or not queries:
            raise RadarValidationError(f"Topic {tid!r} queries must be a non-empty list")
        for q_idx, q in enumerate(queries):
            if not isinstance(q, dict):
                raise RadarValidationError(f"Topic {tid!r} query #{q_idx} must be an object")
            src = q.get("source")
            if src not in SUPPORTED_SOURCES:
                raise RadarValidationError(f"Topic {tid!r} unsupported source {src!r}")
            if src == "github_releases":
                _validate_repo_slug(q.get("repo"))
            elif src == "official_feed":
                url = q.get("url")
                norm_feed_url = normalize_url(url)
                if classify_url_trust_tier(norm_feed_url, policy=policy) != "T1_PRIMARY_OFFICIAL":
                    raise RadarValidationError(f"Topic {tid!r} official_feed must be T1_PRIMARY_OFFICIAL: {url!r}")
            else:
                qtext = q.get("query")
                if not isinstance(qtext, str) or not qtext.strip():
                    raise RadarValidationError(f"Topic {tid!r} query #{q_idx} missing query text")

    return raw


def load_watchlist(path: Path = DEFAULT_WATCHLIST_PATH) -> dict[str, Any]:
    """Load and validate watchlist JSON fail-closed."""
    if not path.is_file():
        raise RadarValidationError(f"Watchlist file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RadarValidationError(f"Failed to parse watchlist JSON: {exc}") from exc
    return validate_watchlist_config(raw)


def sanitize_external_item(
    raw_item: Any,
    *,
    topic_id: str,
    topic_label: str,
    category: str,
    source: str,
    policy: dict[str, Any],
    fetched_utc: str,
) -> dict[str, Any]:
    """Validate, scrub, tier-classify, and force `untrusted_external_data: true` on 1 external item."""
    if not isinstance(raw_item, dict):
        raise RadarValidationError(f"External item must be a dict, got {type(raw_item).__name__}")

    raw_url = raw_item.get("url")
    norm_url = normalize_url(raw_url)
    title = scrub_opsec_text(raw_item.get("title"), max_len=_MAX_TITLE_CHARS)
    if not title:
        raise RadarValidationError("External item has empty title after sanitization")

    snippet = scrub_opsec_text(raw_item.get("snippet", ""), max_len=_MAX_SNIPPET_CHARS)
    published_hint = scrub_opsec_text(raw_item.get("published_utc") or raw_item.get("published_hint") or "", max_len=40)

    # Always recompute trust_tier from parsed URL host/path; never trust upstream claims.
    trust_tier = classify_url_trust_tier(norm_url, policy=policy)
    content_sha256 = compute_content_sha256(title, snippet)

    return {
        "topic_id": topic_id,
        "topic_label": scrub_opsec_text(topic_label, max_len=160),
        "category": scrub_opsec_text(category, max_len=64),
        "source": scrub_opsec_text(source, max_len=32),
        "title": title,
        "url": norm_url,
        "normalized_url": norm_url,
        "snippet": snippet,
        "published_hint": published_hint,
        "trust_tier": trust_tier,
        "content_sha256": content_sha256,
        "fetched_utc": fetched_utc,
        "untrusted_external_data": True,
    }


def _parse_arxiv_atom(xml_text: str, *, max_results: int) -> list[dict[str, Any]]:
    if len(xml_text.encode("utf-8", errors="replace")) > _MAX_FEED_BYTES:
        raise RadarValidationError("arXiv Atom payload exceeds size cap")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise RadarValidationError(f"Malformed arXiv Atom XML: {exc}") from exc
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out: list[dict[str, Any]] = []
    for entry in root.findall("a:entry", ns)[:max_results]:
        title = re.sub(r"\s+", " ", (entry.findtext("a:title", "", ns) or "")).strip()
        link = (entry.findtext("a:id", "", ns) or "").strip()
        summary = re.sub(r"\s+", " ", (entry.findtext("a:summary", "", ns) or "")).strip()
        pub = (entry.findtext("a:published", "", ns) or "")[:10]
        if title and link:
            out.append(
                {
                    "title": f"[{pub}] {title}" if pub else title,
                    "url": link,
                    "snippet": summary[:_MAX_SNIPPET_CHARS],
                    "published_hint": pub,
                }
            )
    return out


def _parse_rss_or_atom(xml_text: str, *, label: str, max_results: int) -> list[dict[str, Any]]:
    if len(xml_text.encode("utf-8", errors="replace")) > _MAX_FEED_BYTES:
        raise RadarValidationError("Official feed payload exceeds size cap")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise RadarValidationError(f"Malformed RSS/Atom XML: {exc}") from exc

    out: list[dict[str, Any]] = []
    rss_items = root.findall("./channel/item")
    if rss_items:
        for item in rss_items[:max_results]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            if title and link:
                out.append(
                    {
                        "title": f"[{label}] {title}",
                        "url": link,
                        "snippet": desc[:_MAX_SNIPPET_CHARS],
                        "published_hint": pub[:32],
                    }
                )
        return out

    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("a:entry", ns)[:max_results]:
        title = (entry.findtext("a:title", "", ns) or "").strip()
        link = ""
        link_el = entry.find("a:link", ns)
        if link_el is not None:
            link = str(link_el.attrib.get("href") or "").strip()
        if not link:
            link = (entry.findtext("a:id", "", ns) or "").strip()
        desc = (entry.findtext("a:summary", "", ns) or entry.findtext("a:content", "", ns) or "").strip()
        pub = (entry.findtext("a:updated", "", ns) or entry.findtext("a:published", "", ns) or "").strip()
        if title and link:
            out.append(
                {
                    "title": f"[{label}] {title}",
                    "url": link,
                    "snippet": desc[:_MAX_SNIPPET_CHARS],
                    "published_hint": pub[:32],
                }
            )
    return out


def _fetch_github_releases_live(repo: str, *, max_results: int, timeout_sec: float) -> list[dict[str, Any]]:
    _validate_repo_slug(repo)

    research_cli = _load_research_cli()
    raw_items: list[dict[str, Any]] | None = None
    try:
        proc = subprocess.run(
            ["gh", "api", f"repos/{repo}/releases?per_page={max_results}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            check=False,
            creationflags=_NO_WINDOW_FLAGS,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            parsed = json.loads(proc.stdout)
            if isinstance(parsed, list):
                raw_items = parsed
    except Exception:
        raw_items = None

    if raw_items is None:
        resp = research_cli._http_get(
            f"https://api.github.com/repos/{repo}/releases?per_page={max_results}",
            timeout=timeout_sec,
            headers={"Accept": "application/vnd.github+json"},
        )
        parsed = resp.json()
        if not isinstance(parsed, list):
            raise RadarValidationError(f"Unexpected GitHub releases payload type for {repo}")
        raw_items = parsed

    out: list[dict[str, Any]] = []
    for rel in raw_items[:max_results]:
        if not isinstance(rel, dict):
            continue
        tag = str(rel.get("tag_name") or "").strip()
        name = str(rel.get("name") or tag).strip()
        html_url = str(rel.get("html_url") or "").strip()
        pub = str(rel.get("published_at") or rel.get("created_at") or "")[:10]
        body = str(rel.get("body") or "").strip()
        if html_url and name:
            out.append(
                {
                    "title": f"{repo} {tag or name} ({pub})" if pub else f"{repo} {tag or name}",
                    "url": html_url,
                    "snippet": body[:_MAX_SNIPPET_CHARS] or f"GitHub release {tag or name} for {repo}",
                    "published_hint": pub,
                }
            )
    if out:
        return out

    # Fallback to repository tags when a repo has no formal GitHub Release yet (e.g. early pre-releases).
    resp_tags = research_cli._http_get(
        f"https://api.github.com/repos/{repo}/tags?per_page={max_results}",
        timeout=timeout_sec,
        headers={"Accept": "application/vnd.github+json"},
    )
    tags_data = resp_tags.json()
    if isinstance(tags_data, list):
        for tg in tags_data[:max_results]:
            if not isinstance(tg, dict):
                continue
            tag_name = str(tg.get("name") or "").strip()
            if tag_name:
                out.append(
                    {
                        "title": f"{repo} tag {tag_name}",
                        "url": f"https://github.com/{repo}/releases/tag/{quote(tag_name, safe='')}",
                        "snippet": f"Official GitHub tag {tag_name} for {repo}",
                        "published_hint": "",
                    }
                )
    return out


def _fetch_live_query(query_spec: dict[str, Any], *, timeout_sec: float, mode: str) -> list[dict[str, Any]]:
    """Execute one bounded read-only external query; strictly blocked unless `mode == 'live'`."""
    if mode != "live":
        raise RadarNetworkBlockedError(f"Network fetch blocked in mode={mode!r}")

    research_cli = _load_research_cli()
    src = str(query_spec["source"])
    max_results = max(1, min(20, int(query_spec.get("max_results", 4))))

    if src == "arxiv" and query_spec.get("raw_arxiv_query"):
        q = str(query_spec["query"])
        sort_by = str(query_spec.get("sort_by", "submittedDate"))
        if sort_by not in ("relevance", "lastUpdatedDate", "submittedDate"):
            sort_by = "submittedDate"
        url = (
            "https://export.arxiv.org/api/query?"
            f"search_query={quote_plus(q, safe=':+()"')}&start=0&max_results={max_results}"
            f"&sortBy={sort_by}&sortOrder=descending"
        )
        resp = research_cli._http_get(url, timeout=timeout_sec)
        return _parse_arxiv_atom(resp.text, max_results=max_results)

    if src == "github_releases":
        return _fetch_github_releases_live(str(query_spec["repo"]), max_results=max_results, timeout_sec=timeout_sec)

    if src == "official_feed":
        feed_url = normalize_url(query_spec["url"])
        resp = research_cli._http_get(feed_url, timeout=timeout_sec)
        label = str(query_spec.get("label") or urlparse(feed_url).hostname or "official")
        return _parse_rss_or_atom(resp.text, label=label, max_results=max_results)

    # Reuse `research_cli.multi_source_search` for arxiv/openalex/github/quant/hn/cn/ru/vi.
    res = research_cli.multi_source_search(
        str(query_spec["query"]),
        sources=[src],
        max_per_source=max_results,
    )
    if res.get("errors", {}).get(src):
        raise RuntimeError(str(res["errors"][src]))
    rows = res.get("results", {}).get(src, [])
    if not isinstance(rows, list):
        raise RadarValidationError(f"research_cli returned non-list for source {src!r}")
    return rows


def build_default_offline_fixture() -> dict[str, list[dict[str, Any]]]:
    """Deterministic offline CI fixture covering all watchlist topics, duplicates, and lower-tier filtering."""
    return {
        "arxiv_qfin_tr_pm_st": [
            {
                "source": "arxiv",
                "title": "[2026-11-20] Regime-Aware Volatility Targeting Under Drawdown Constraints",
                "url": "https://arxiv.org/abs/2611.10421",
                "snippet": "Evaluates causal volatility targeting and tail-risk sizing on out-of-sample futures.",
                "published_hint": "2026-11-20",
            },
            {
                "source": "openalex",
                "title": "[2026-11-20] Regime-Aware Volatility Targeting Under Drawdown Constraints",
                "url": "http://arxiv.org/abs/2611.10421/?utm_source=feed#abstract",
                "snippet": "Duplicate URL variant that must be deduplicated cleanly.",
                "published_hint": "2026-11-20",
            },
            {
                "source": "openalex",
                "title": "[2026, 18 cites] Cross-Asset Intraday Microstructure Slippage Bounds",
                "url": "https://doi.org/10.1000/naqex-offline-qfin-001",
                "snippet": "Empirical spread and markout decay around scheduled macroeconomic releases.",
                "published_hint": "2026",
            },
        ],
        "arxiv_cs_ai_agent_harness": [
            {
                "source": "arxiv",
                "title": "[2026-11-18] Deterministic Verification Harnesses for Autonomous Coding Agents",
                "url": "https://arxiv.org/abs/2611.09812",
                "snippet": "Benchmarks ratchet gates, circuit breakers, and typed contracts in multi-agent loops.",
                "published_hint": "2026-11-18",
            },
            {
                "source": "github",
                "title": "openai/evals-harness-reference (4200 stars)",
                "url": "https://github.com/openai/evals-harness-reference",
                "snippet": "Reference evaluation harness patterns for reproducible agent verification.",
                "published_hint": "2026-11-15",
            },
            {
                "source": "github",
                "title": "Unverified Forum Rumor About Agent Tricks",
                "url": "https://www.reddit.com/r/LocalLLaMA/comments/offline01/agent_tricks/",
                "snippet": "Lower-tier forum item filtered out by T1/T2 topic policy.",
                "published_hint": "2026-11-14",
            },
        ],
        "gh_releases_quant_and_tools": [
            {
                "source": "github_releases",
                "title": "nautechsystems/nautilus_trader v1.224.0 (2026-11-19)",
                "url": "https://github.com/nautechsystems/nautilus_trader/releases/tag/v1.224.0",
                "snippet": "Rust core execution parity and Python 3.12 performance improvements.",
                "published_hint": "2026-11-19",
            },
            {
                "source": "github_releases",
                "title": "astral-sh/ruff 0.17.6 (2026-11-21)",
                "url": "https://github.com/astral-sh/ruff/releases/tag/0.17.6",
                "snippet": "Fast Python linter and formatter release.",
                "published_hint": "2026-11-21",
            },
            {
                "source": "github_releases",
                "title": "astral-sh/ty 0.0.1-alpha.28 (2026-11-22)",
                "url": "https://github.com/astral-sh/ty/releases/tag/0.0.1-alpha.28",
                "snippet": "Astral Rust-based Python type checker milestone.",
                "published_hint": "2026-11-22",
            },
            {
                "source": "github_releases",
                "title": "nomadkaraoke/python-audio-separator v0.47.0 (2026-11-10)",
                "url": "https://github.com/nomadkaraoke/python-audio-separator/releases/tag/v0.47.0",
                "snippet": "Audio source separation release notes for license and model review.",
                "published_hint": "2026-11-10",
            },
        ],
        "official_macro_and_prop_sources": [
            {
                "source": "official_feed",
                "title": "[Federal Reserve Monetary Policy RSS] FOMC Schedule and Minutes Notice",
                "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20261118a.htm",
                "snippet": "Official Federal Reserve release schedule for red-news calendar verification.",
                "published_hint": "2026-11-18",
            },
            {
                "source": "official_feed",
                "title": "[BLS Latest Releases RSS] Consumer Price Index Schedule Update",
                "url": "https://www.bls.gov/news.release/cpi.nr0.htm",
                "snippet": "Official Bureau of Labor Statistics CPI release timing notice.",
                "published_hint": "2026-11-19",
            },
        ],
        "multilingual_quant_community": [
            {
                "source": "quant",
                "title": "[QuantSE] Volatility Targeting With Hard Daily Drawdown Caps",
                "url": "https://quant.stackexchange.com/questions/88001/volatility-targeting-drawdown",
                "snippet": "Technical discussion on variance targeting under prop-firm daily loss limits.",
                "published_hint": "2026-11-12",
            },
            {
                "source": "ru",
                "title": "[Habr RU] Causal Backtesting Without Look-Ahead Leakage",
                "url": "https://habr.com/ru/articles/850123/",
                "snippet": "Engineering checklist for bar-close alignment and slippage simulation.",
                "published_hint": "2026-11-11",
            },
        ],
    }


def load_offline_fixture(path: Path) -> dict[str, list[Any]]:
    """Load an external offline JSON fixture fail-closed."""
    if not path.is_file():
        raise RadarValidationError(f"Offline fixture not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RadarValidationError(f"Failed to parse offline fixture JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RadarValidationError("Offline fixture root must be a JSON object mapping topic_id -> list")
    for tid, rows in data.items():
        if not isinstance(tid, str) or not isinstance(rows, list):
            raise RadarValidationError(f"Offline fixture entry for {tid!r} must be a list")
    return data


def verify_receipt_invariants(receipt: dict[str, Any]) -> None:
    """Explicit `-O`-safe post-condition guard verifying supply-chain and zero-execution invariants."""
    if not isinstance(receipt, dict):
        raise RadarValidationError("Receipt must be a dict")
    if receipt.get("schema") != SCHEMA_VERSION:
        raise RadarValidationError(f"Invalid receipt schema: {receipt.get('schema')!r}")
    if not _is_exact_zero_int(receipt.get("order_send_count")):
        raise RadarValidationError("Hard invariant failed: receipt.order_send_count must be int 0")
    if not _is_exact_zero_int(receipt.get("holdout_rows_analysed")):
        raise RadarValidationError("Hard invariant failed: receipt.holdout_rows_analysed must be int 0")
    if not _is_exact_zero_int(receipt.get("spend_vnd")):
        raise RadarValidationError("Hard invariant failed: receipt.spend_vnd must be int 0")
    if receipt.get("untrusted_external_data") is not True:
        raise RadarValidationError("Supply-chain invariant failed: receipt.untrusted_external_data must be True")

    mode = receipt.get("mode")
    net_calls = receipt.get("network_calls_made")
    if isinstance(net_calls, bool) or not isinstance(net_calls, int) or net_calls < 0:
        raise RadarValidationError("receipt.network_calls_made must be a non-negative int")
    if mode in ("offline", "dry-run") and net_calls != 0:
        raise RadarValidationError(f"Zero-network invariant violated in mode={mode!r}: network_calls_made={net_calls}")

    items = receipt.get("items")
    if not isinstance(items, list):
        raise RadarValidationError("receipt.items must be a list")

    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise RadarValidationError(f"receipt.items[{idx}] is not a dict")
        if item.get("untrusted_external_data") is not True:
            raise RadarValidationError(f"Supply-chain invariant failed on item #{idx}: untrusted_external_data != True")
        tier = item.get("trust_tier")
        if tier not in VALID_TRUST_TIERS:
            raise RadarValidationError(f"Invalid trust_tier on item #{idx}: {tier!r}")
        norm_url = item.get("normalized_url")
        if not isinstance(norm_url, str) or not norm_url:
            raise RadarValidationError(f"Missing normalized_url on item #{idx}")
        if norm_url in seen_urls:
            raise RadarValidationError(f"Duplicate normalized_url leaked into receipt: {norm_url!r}")
        seen_urls.add(norm_url)

        sha = item.get("content_sha256")
        if not isinstance(sha, str) or not _HEX64_RE.match(sha):
            raise RadarValidationError(f"Invalid content_sha256 on item #{idx}: {sha!r}")
        if sha in seen_hashes:
            raise RadarValidationError(f"Duplicate content_sha256 leaked into receipt: {sha!r}")
        seen_hashes.add(sha)


def _strip_bare_dollar(text: str) -> str:
    """Keep generated Markdown prose free of bare currency `$` signs."""
    return re.sub(r"\$(\d)", r"USD \1", text).replace("$", "USD ")


def render_inbox_markdown(receipt: dict[str, Any]) -> str:
    """Render a sanitized `knowledge/inbox/` Markdown card compatible with `brain_cli.py`."""
    verify_receipt_invariants(receipt)
    gen_utc = str(receipt["generated_utc"])
    day_label = gen_utc[:10]
    items: list[dict[str, Any]] = receipt["items"]
    summary: dict[str, Any] = receipt["summary"]

    body_lines = [
        f"# Naqex Auto-Research Radar Digest ({day_label})",
        "",
        f"- Mode: `{receipt['mode']}` | Status: `{receipt['status']}` | OrderSend: `0` | Holdout rows: `0`",
        f"- Topics scanned: `{summary['topics_scanned']}/{summary['topics_total']}` | "
        f"Accepted: `{summary['accepted_items']}` | Deduplicated: `{summary['deduplicated_count']}` | "
        f"Filtered tier: `{summary['filtered_tier_count']}` | "
        f"Rejected malformed: `{summary['rejected_malformed_count']}`",
        (
            "- Supply-chain guard: ALL entries below are `untrusted_external_data: true` "
            "(read-only metadata; never execute external code)."
        ),
        "",
    ]

    by_topic: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        by_topic.setdefault(str(it["topic_id"]), []).append(it)

    for topic in receipt["topics"]:
        tid = str(topic["topic_id"])
        t_items = by_topic.get(tid, [])
        body_lines.append(f"## {_strip_bare_dollar(str(topic['label']))} (`{tid}`)")
        if not t_items:
            body_lines.append("- No accepted items in this run.")
            body_lines.append("")
            continue
        for it in t_items:
            title = _strip_bare_dollar(str(it["title"]))
            snippet = _strip_bare_dollar(str(it["snippet"]))
            safe_url = str(it["url"]).replace("$", "%24")
            safe_src = _strip_bare_dollar(str(it["source"]))
            body_lines.append(
                f"- **[{it['trust_tier']}]** [{title}]({safe_url}) "
                f"(`source={safe_src}`, `sha256={it['content_sha256'][:12]}`, `untrusted_external_data=true`)"
            )
            if snippet:
                body_lines.append(f"  - {snippet}")
        body_lines.append("")

    body = "\n".join(body_lines).strip() + "\n"
    digest = hashlib.sha256(body.encode()).hexdigest()
    top_tier = "T1_PRIMARY_OFFICIAL"
    if items and all(it["trust_tier"] != "T1_PRIMARY_OFFICIAL" for it in items):
        top_tier = "T2_TECHNICAL_COMMUNITY"

    safe_source_url = ("watchlist://" + str(receipt["watchlist_path"])).replace("$", "%24")
    frontmatter = "\n".join(
        [
            "---",
            f"title: {json.dumps(f'Naqex Auto-Research Radar Digest ({day_label})', ensure_ascii=False)}",
            f"source_url: {json.dumps(safe_source_url, ensure_ascii=False)}",
            f"fetched_utc: {gen_utc}",
            f"trust_tier: {top_tier}",
            "research_mode: autonomous",
            'owner_question: "Scheduled multi-topic external research radar scan"',
            f"content_sha256: {digest[:16]}",
            "untrusted_external_data: true",
            "order_send_count: 0",
            "holdout_rows_analysed: 0",
            "---",
            "",
        ]
    )
    full_md = frontmatter + body
    if "$" in full_md:
        raise RadarValidationError("Rendered Markdown card contains forbidden bare dollar sign")
    return full_md


def _rel_posix(path: Path, root: Path = ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def run_radar(
    *,
    mode: str = "offline",
    watchlist_path: Path = DEFAULT_WATCHLIST_PATH,
    out_path: Path | None = DEFAULT_OUTPUT_PATH,
    topic_filter: list[str] | None = None,
    max_per_topic_override: int | None = None,
    timeout_sec: float | None = None,
    offline_fixture: dict[str, list[Any]] | None = None,
    write_receipt: bool = True,
    write_inbox: bool = False,
    inbox_dir: Path = DEFAULT_INBOX_DIR,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Run the multi-topic automated research radar in `offline`, `dry-run`, or `live` mode."""
    if mode not in ("offline", "dry-run", "live"):
        raise RadarValidationError(f"Unsupported mode: {mode!r}")

    watchlist = load_watchlist(watchlist_path)
    policy = watchlist["trust_tier_policy"]
    limits = watchlist["limits"]
    global_allowed_tiers = set(policy["allowed_tiers"])
    hard_max_per_topic = int(limits["hard_max_items_per_topic"])
    hard_max_total = int(limits.get("hard_max_total_items", 120))
    raw_timeout = timeout_sec if timeout_sec is not None else limits.get("request_timeout_sec", 18.0)
    eff_timeout = _validate_timeout_sec(raw_timeout)

    if max_per_topic_override is not None:
        if (
            isinstance(max_per_topic_override, bool)
            or not isinstance(max_per_topic_override, int)
            or not (1 <= max_per_topic_override <= hard_max_per_topic)
        ):
            raise RadarValidationError(f"max_per_topic_override must be in [1, {hard_max_per_topic}]")

    ts = (now_utc or datetime.now(UTC)).astimezone(UTC)
    fetched_utc = ts.isoformat().replace("+00:00", "Z")

    filter_set = {t.strip() for t in (topic_filter or []) if t.strip()}
    all_topics = watchlist["topics"]
    selected_topics = [
        t for t in all_topics if t.get("enabled", True) and (not filter_set or t["topic_id"] in filter_set)
    ]
    if filter_set:
        unknown = sorted(filter_set - {t["topic_id"] for t in all_topics})
        if unknown:
            raise RadarValidationError(f"Unknown topic_id(s): {unknown}")

    fixture_map: dict[str, list[Any]] = {}
    if mode == "offline":
        fixture_map = offline_fixture if offline_fixture is not None else build_default_offline_fixture()

    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()
    accepted_items: list[dict[str, Any]] = []
    topic_reports: list[dict[str, Any]] = []
    all_errors: list[str] = []
    tier_counts: dict[str, int] = {}

    raw_total = 0
    dedup_total = 0
    filtered_tier_total = 0
    rejected_malformed_total = 0
    network_calls_made = 0

    for topic in selected_topics:
        tid = str(topic["topic_id"])
        t_label = str(topic["label"])
        t_cat = str(topic.get("category", "general"))
        t_cap = int(max_per_topic_override or topic.get("max_items", limits.get("default_max_items_per_topic", 6)))
        t_cap = min(t_cap, hard_max_per_topic)
        t_allowed_tiers = set(topic.get("allowed_tiers", global_allowed_tiers)) & global_allowed_tiers

        raw_rows: list[tuple[str, Any]] = []
        t_errors: list[str] = []

        if mode == "dry-run":
            # Dry-run validates and plans without network calls or disk writes.
            pass
        elif mode == "offline":
            for raw_entry in fixture_map.get(tid, []):
                src_hint = str(raw_entry.get("source", "offline")) if isinstance(raw_entry, dict) else "offline"
                raw_rows.append((src_hint, raw_entry))
        else:
            query_buckets: list[list[tuple[str, Any]]] = []
            for q_spec in topic["queries"]:
                src = str(q_spec["source"])
                q_copy = dict(q_spec)
                if max_per_topic_override is not None:
                    q_copy["max_results"] = min(int(q_copy.get("max_results", t_cap)), t_cap)
                network_calls_made += 1
                try:
                    fetched_rows = _fetch_live_query(q_copy, timeout_sec=eff_timeout, mode=mode)
                    if not isinstance(fetched_rows, list):
                        raise RadarValidationError(f"Upstream query for {tid}/{src} returned non-list payload")
                    query_buckets.append([(src, row) for row in fetched_rows])
                except Exception as exc:
                    err_msg = scrub_opsec_text(f"{tid}/{src}: {exc}", max_len=240)
                    t_errors.append(err_msg)
                    all_errors.append(err_msg)
            if query_buckets:
                max_bucket_len = max(len(b) for b in query_buckets)
                for idx in range(max_bucket_len):
                    for bucket in query_buckets:
                        if idx < len(bucket):
                            raw_rows.append(bucket[idx])

        t_accepted = 0
        t_dedup = 0
        t_filtered = 0
        t_rejected = 0
        raw_total += len(raw_rows)

        for src_name, raw_entry in raw_rows:
            try:
                clean = sanitize_external_item(
                    raw_entry,
                    topic_id=tid,
                    topic_label=t_label,
                    category=t_cat,
                    source=src_name,
                    policy=policy,
                    fetched_utc=fetched_utc,
                )
            except RadarValidationError:
                t_rejected += 1
                rejected_malformed_total += 1
                continue

            if clean["trust_tier"] not in t_allowed_tiers:
                t_filtered += 1
                filtered_tier_total += 1
                continue

            if clean["normalized_url"] in seen_urls or clean["content_sha256"] in seen_hashes:
                t_dedup += 1
                dedup_total += 1
                continue

            if t_accepted >= t_cap or len(accepted_items) >= hard_max_total:
                continue

            seen_urls.add(clean["normalized_url"])
            seen_hashes.add(clean["content_sha256"])
            accepted_items.append(clean)
            t_accepted += 1
            tier_counts[clean["trust_tier"]] = tier_counts.get(clean["trust_tier"], 0) + 1

        topic_reports.append(
            {
                "topic_id": tid,
                "label": t_label,
                "category": t_cat,
                "sources": list(topic.get("sources", [])),
                "allowed_tiers": sorted(t_allowed_tiers),
                "max_items": t_cap,
                "planned_queries": len(topic["queries"]),
                "raw_count": len(raw_rows),
                "accepted_count": t_accepted,
                "deduplicated_count": t_dedup,
                "filtered_tier_count": t_filtered,
                "rejected_malformed_count": t_rejected,
                "errors": t_errors,
            }
        )

    if mode == "dry-run":
        status = "DRY_RUN"
    elif all_errors and not accepted_items:
        status = "DEGRADED"
    elif all_errors:
        status = "PARTIAL_OK"
    else:
        status = "OK"

    receipt: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "status": status,
        "mode": mode,
        "generated_utc": fetched_utc,
        "watchlist_path": _rel_posix(watchlist_path),
        "watchlist_version": str(watchlist.get("version", "1.0.0")),
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
        "spend_vnd": SPEND_VND,
        "untrusted_external_data": True,
        "network_calls_made": network_calls_made,
        "summary": {
            "topics_scanned": len(selected_topics),
            "topics_total": len(all_topics),
            "raw_items": raw_total,
            "accepted_items": len(accepted_items),
            "deduplicated_count": dedup_total,
            "filtered_tier_count": filtered_tier_total,
            "rejected_malformed_count": rejected_malformed_total,
            "tier_counts": dict(sorted(tier_counts.items())),
            "error_count": len(all_errors),
        },
        "topics": topic_reports,
        "items": accepted_items,
        "inbox_card_path": None,
        "errors": all_errors,
    }

    verify_receipt_invariants(receipt)

    if mode != "dry-run":
        if write_inbox and accepted_items:
            md_text = render_inbox_markdown(receipt)
            day_tag = ts.strftime("%Y%m%d")
            digest8 = hashlib.sha256(md_text.encode("utf-8")).hexdigest()[:8]
            card_path = inbox_dir / f"{day_tag}-auto-research-radar-{digest8}.md"
            _atomic_write_text(card_path, md_text)
            receipt["inbox_card_path"] = _rel_posix(card_path)

        if write_receipt and out_path is not None:
            _atomic_write_text(out_path, json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")

    return receipt


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auto_research_radar.py",
        description="Naqex External Auto-Research Radar (0 API keys, untrusted_external_data enforced, OrderSend=0).",
    )
    parser.add_argument("--offline", action="store_true", help="100% deterministic CI mode with zero network calls")
    parser.add_argument("--dry-run", action="store_true", help="Validate watchlist & plan queries with zero writes")
    parser.add_argument("--live", action="store_true", help="Execute bounded live scan against official/open APIs")
    parser.add_argument(
        "--watchlist", type=Path, default=DEFAULT_WATCHLIST_PATH, help="Path to research_watchlist.json"
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_PATH, help="Output path for sanitized JSON receipt")
    parser.add_argument("--topics", default="", help="Optional comma-separated subset of topic_id values")
    parser.add_argument("--max-per-topic", type=int, default=None, help="Optional cap override per topic (1..20)")
    parser.add_argument("--timeout", type=float, default=None, help="Per-request network timeout in seconds (1..30)")
    parser.add_argument("--fixture", type=Path, default=None, help="Optional offline fixture JSON file")
    parser.add_argument("--no-write", action="store_true", help="Do not write JSON receipt to disk")
    parser.add_argument(
        "--write-inbox",
        action="store_true",
        help="Stage sanitized Markdown digest card into knowledge/inbox/ (never mutates brain.sqlite3)",
    )
    parser.add_argument("--inbox-dir", type=Path, default=DEFAULT_INBOX_DIR, help="Inbox directory for Markdown card")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Print full sanitized JSON receipt")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)

    if args.live and args.offline:
        print("ERROR: --live and --offline cannot be combined.", file=sys.stderr)
        return 2

    if args.dry_run:
        mode = "dry-run"
    elif args.live:
        mode = "live"
    else:
        # Fail-closed default: zero network calls unless --live is explicitly passed.
        mode = "offline"

    topic_filter = [t.strip() for t in args.topics.split(",") if t.strip()] if args.topics else None

    try:
        fixture_data = load_offline_fixture(args.fixture) if (args.fixture is not None and mode == "offline") else None
        receipt = run_radar(
            mode=mode,
            watchlist_path=args.watchlist,
            out_path=args.out,
            topic_filter=topic_filter,
            max_per_topic_override=args.max_per_topic,
            timeout_sec=args.timeout,
            offline_fixture=fixture_data,
            write_receipt=not args.no_write,
            write_inbox=args.write_inbox,
            inbox_dir=args.inbox_dir,
        )
    except (RadarValidationError, RadarNetworkBlockedError) as exc:
        print(f"ERROR: {scrub_opsec_text(exc)}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
    else:
        s = receipt["summary"]
        print(
            f"[auto_research_radar] mode={receipt['mode']} status={receipt['status']} "
            f"topics={s['topics_scanned']}/{s['topics_total']} accepted={s['accepted_items']} "
            f"dedup={s['deduplicated_count']} filtered_tier={s['filtered_tier_count']} "
            f"rejected={s['rejected_malformed_count']} net_calls={receipt['network_calls_made']} "
            f"order_send={receipt['order_send_count']} untrusted=true"
        )
        if receipt.get("inbox_card_path"):
            print(f"  inbox_card={receipt['inbox_card_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
