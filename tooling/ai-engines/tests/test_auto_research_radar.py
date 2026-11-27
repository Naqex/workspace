"""Offline deterministic CI test suite for Front 5 External Auto-Research Radar.

100% offline (zero network calls), `-O`-safe (explicit `_check` guards instead of
bare `assert` statements), and OPSEC-clean (all synthetic sensitive test tokens
and paths constructed dynamically).
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tooling.automation import auto_research_radar as radar  # noqa: E402
from tooling.knowledge import research_cli  # noqa: E402


def _check(condition: bool, message: str) -> None:
    """Explicit invariant check that never gets stripped under `python -O`."""
    if not condition:
        raise AssertionError(message)


def _block_all_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("NETWORK_CALL_FORBIDDEN_IN_OFFLINE_TESTS")

    monkeypatch.setattr(socket, "create_connection", _boom)
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    monkeypatch.setattr(subprocess, "run", _boom)
    monkeypatch.setattr(research_cli, "_http_get", _boom)


def test_real_watchlist_loads_and_covers_required_topics() -> None:
    wl = radar.load_watchlist(radar.DEFAULT_WATCHLIST_PATH)
    _check(wl["schema"] == radar.WATCHLIST_SCHEMA_VERSION, "watchlist schema mismatch")
    _check(wl["order_send_count"] == 0, "order_send_count must be 0")
    _check(wl["holdout_rows_analysed"] == 0, "holdout_rows_analysed must be 0")
    _check(wl["spend_vnd"] == 0, "spend_vnd must be 0")
    _check(wl["supply_chain_guard"]["enforce_untrusted_external_data"] is True, "untrusted guard missing")
    _check(wl["supply_chain_guard"]["api_keys_required"] == 0, "api_keys_required must be 0")

    topics_by_id = {t["topic_id"]: t for t in wl["topics"]}
    for required_id in (
        "arxiv_qfin_tr_pm_st",
        "arxiv_cs_ai_agent_harness",
        "gh_releases_quant_and_tools",
        "official_macro_and_prop_sources",
        "multilingual_quant_community",
    ):
        _check(required_id in topics_by_id, f"missing required topic: {required_id}")

    gh_repos = set(topics_by_id["gh_releases_quant_and_tools"]["repos"])
    for expected_repo in (
        "nautechsystems/nautilus_trader",
        "astral-sh/ruff",
        "astral-sh/ty",
        "nomadkaraoke/python-audio-separator",
    ):
        _check(expected_repo in gh_repos, f"missing GitHub release repo: {expected_repo}")

    qfin_cats = set(topics_by_id["arxiv_qfin_tr_pm_st"]["arxiv_categories"])
    _check({"q-fin.TR", "q-fin.PM", "q-fin.ST"}.issubset(qfin_cats), "missing q-fin categories")


def test_watchlist_validation_fails_closed_on_mutations() -> None:
    base = radar.load_watchlist(radar.DEFAULT_WATCHLIST_PATH)

    bad_order = json.loads(json.dumps(base))
    bad_order["order_send_count"] = 1
    with pytest.raises(radar.RadarValidationError):
        radar.validate_watchlist_config(bad_order)

    bad_untrusted = json.loads(json.dumps(base))
    bad_untrusted["supply_chain_guard"]["enforce_untrusted_external_data"] = False
    with pytest.raises(radar.RadarValidationError):
        radar.validate_watchlist_config(bad_untrusted)

    bad_repo = json.loads(json.dumps(base))
    bad_repo["topics"][2]["queries"][0]["repo"] = "astral-sh/ruff; rm -rf /"
    with pytest.raises(radar.RadarValidationError):
        radar.validate_watchlist_config(bad_repo)

    bad_feed = json.loads(json.dumps(base))
    bad_feed["topics"][3]["queries"][0]["url"] = "https://random-blog.example.com/rss.xml"
    with pytest.raises(radar.RadarValidationError):
        radar.validate_watchlist_config(bad_feed)


def test_trust_tier_classification_and_anti_spoofing() -> None:
    policy = radar.load_watchlist(radar.DEFAULT_WATCHLIST_PATH)["trust_tier_policy"]

    _check(
        radar.classify_url_trust_tier("https://arxiv.org/abs/2611.19530", policy=policy) == "T1_PRIMARY_OFFICIAL",
        "arxiv should be T1",
    )
    _check(
        radar.classify_url_trust_tier("https://github.com/astral-sh/ruff/releases/tag/0.17.6", policy=policy)
        == "T1_PRIMARY_OFFICIAL",
        "github should be T1",
    )
    _check(
        radar.classify_url_trust_tier("https://www.federalreserve.gov/feeds/press_monetary.xml", policy=policy)
        == "T1_PRIMARY_OFFICIAL",
        "fed should be T1",
    )
    _check(
        radar.classify_url_trust_tier("https://ftmo.com/en/trading-objectives/", policy=policy)
        == "T1_PRIMARY_OFFICIAL",
        "ftmo should be T1",
    )
    _check(
        radar.classify_url_trust_tier("https://the5ers.com/high-stakes/", policy=policy) == "T1_PRIMARY_OFFICIAL",
        "the5ers should be T1",
    )
    _check(
        radar.classify_url_trust_tier("https://icfunded.com/rules", policy=policy) == "T1_PRIMARY_OFFICIAL",
        "icfunded should be T1",
    )
    _check(
        radar.classify_url_trust_tier("https://quant.stackexchange.com/questions/123", policy=policy)
        == "T2_TECHNICAL_COMMUNITY",
        "quant SE should be T2",
    )
    _check(
        radar.classify_url_trust_tier("https://habr.com/ru/articles/123/", policy=policy) == "T2_TECHNICAL_COMMUNITY",
        "habr should be T2",
    )
    _check(
        radar.classify_url_trust_tier("https://www.reddit.com/r/algotrading/comments/abc/x/", policy=policy)
        == "T3_FORUM_EXPERIENCE",
        "reddit should be T3_FORUM_EXPERIENCE",
    )

    # Anti-spoofing negative mutants: query/path/subdomain tricks must NOT elevate to T1.
    _check(
        radar.classify_url_trust_tier("https://evil.example.com/?ref=arxiv.org&x=github.com", policy=policy)
        == "T3_GENERAL_WEB",
        "query spoofing must not elevate trust tier",
    )
    _check(
        radar.classify_url_trust_tier("https://evil-arxiv.org/abs/1234", policy=policy) == "T3_GENERAL_WEB",
        "suffix spoofing must not elevate trust tier",
    )
    _check(
        radar.classify_url_trust_tier("https://mql5.com/en/articles/999", policy=policy) == "T2_TECHNICAL_COMMUNITY",
        "mql5 articles should remain T2, only /en/docs is T1",
    )
    _check(
        radar.classify_url_trust_tier("https://www.mql5.com/en/docs/trading", policy=policy) == "T1_PRIMARY_OFFICIAL",
        "mql5/en/docs should be T1",
    )


def test_normalize_url_rejects_dangerous_schemes_and_private_hosts() -> None:
    local_ip = ".".join(["127", "0", "0", "1"])
    lan_ip = ".".join(["192", "168", "1", "99"])
    cgnat_ip = ".".join(["100", "72", "5", "9"])
    bad_urls = [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "data:text/html,<h1>x</h1>",
        f"http://{local_ip}:8080/health",
        f"http://{lan_ip}/admin",
        f"https://{cgnat_ip}/metrics",
        "http://localhost/status",
        "https://user:pass@arxiv.org/abs/1234",
        "https://arxiv.org/abs/1234\nInjected: header",
        "",
        None,
    ]
    for bad in bad_urls:
        with pytest.raises(radar.RadarValidationError):
            radar.normalize_url(bad)


def test_deduplication_by_normalized_url_and_content_sha256(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _block_all_network(monkeypatch)
    fixture = {
        "arxiv_qfin_tr_pm_st": [
            {
                "source": "arxiv",
                "title": "Causal Volatility Targeting Paper",
                "url": "https://arxiv.org/abs/2611.99999",
                "snippet": "Exact same abstract body for content sha256 test.",
            },
            {
                # Duplicate by normalized URL (http vs https, trailing slash, tracking params, fragment)
                "source": "openalex",
                "title": "Different Title Same Normalized URL",
                "url": "http://ARXIV.ORG:80/abs/2611.99999/?utm_source=x&fbclid=y#top",
                "snippet": "Different snippet text but exact same URL.",
            },
            {
                # Duplicate by content_sha256 (different URL, same normalized title + snippet)
                "source": "openalex",
                "title": "  causal   volatility targeting paper ",
                "url": "https://doi.org/10.1000/mirror-copy-99999",
                "snippet": "exact same abstract body for content sha256 test.  ",
            },
        ]
    }
    out_file = tmp_path / "radar.json"
    receipt = radar.run_radar(
        mode="offline",
        out_path=out_file,
        topic_filter=["arxiv_qfin_tr_pm_st"],
        offline_fixture=fixture,
    )
    _check(receipt["summary"]["raw_items"] == 3, "expected 3 raw items")
    _check(receipt["summary"]["accepted_items"] == 1, "expected 1 accepted item after dual dedup")
    _check(receipt["summary"]["deduplicated_count"] == 2, "expected 2 deduplicated items")
    _check(receipt["items"][0]["normalized_url"] == "https://arxiv.org/abs/2611.99999", "canonical URL mismatch")


def test_forced_untrusted_external_data_and_malformed_payloads_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_all_network(monkeypatch)
    fixture: dict[str, list[Any]] = {
        "arxiv_cs_ai_agent_harness": [
            # Attempt to spoof untrusted_external_data=False (must be forced True!)
            {
                "source": "arxiv",
                "title": "Legit Harness Paper Trying To Drop Untrusted Flag",
                "url": "https://arxiv.org/abs/2611.55555",
                "snippet": "Safe abstract text.",
                "untrusted_external_data": False,
                "trust_tier": "T1_PRIMARY_OFFICIAL",
            },
            # Attempt to spoof T1 on a T3 blog URL (must be recomputed T3 and filtered out!)
            {
                "source": "github",
                "title": "Untrusted Blog Claiming T1",
                "url": "https://untrusted-blog.example.org/post",
                "snippet": "Should be filtered as T3_GENERAL_WEB.",
                "untrusted_external_data": False,
                "trust_tier": "T1_PRIMARY_OFFICIAL",
            },
            # Malformed payloads (must be rejected fail-closed without crashing)
            None,
            42,
            "raw string",
            {"title": "Missing URL"},
            {"url": "https://arxiv.org/abs/2611.66666", "title": "   "},
            {"url": "javascript:alert(1)", "title": "XSS Attempt"},
        ]
    }
    receipt = radar.run_radar(
        mode="offline",
        out_path=tmp_path / "radar.json",
        topic_filter=["arxiv_cs_ai_agent_harness"],
        offline_fixture=fixture,
    )
    _check(receipt["summary"]["accepted_items"] == 1, "expected exactly 1 accepted item")
    _check(receipt["summary"]["filtered_tier_count"] == 1, "expected 1 T3 item filtered")
    _check(receipt["summary"]["rejected_malformed_count"] == 6, "expected 6 malformed items rejected")
    _check(receipt["items"][0]["untrusted_external_data"] is True, "untrusted_external_data must be forced True")

    # Tampering with receipt must raise RadarValidationError even under -O.
    tampered = json.loads(json.dumps(receipt))
    tampered["items"][0]["untrusted_external_data"] = False
    with pytest.raises(radar.RadarValidationError):
        radar.verify_receipt_invariants(tampered)

    # Corrupt fixture file fails closed.
    bad_fixture = tmp_path / "corrupt_fixture.json"
    bad_fixture.write_text('["not-a-dict"]', encoding="utf-8")
    with pytest.raises(radar.RadarValidationError):
        radar.load_offline_fixture(bad_fixture)


def test_offline_cli_zero_network_and_dry_run_no_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _block_all_network(monkeypatch)
    out_file = tmp_path / "radar_offline.json"

    # Dry-run must make 0 network calls AND write 0 files.
    rc_dry = radar.main(["--dry-run", "--out", str(out_file), "--json"])
    _check(rc_dry == 0, f"dry-run rc expected 0, got {rc_dry}")
    _check(not out_file.exists(), "dry-run must not write output file")
    dry_payload = json.loads(capsys.readouterr().out)
    _check(dry_payload["mode"] == "dry-run", "dry-run mode mismatch")
    _check(dry_payload["network_calls_made"] == 0, "dry-run network calls must be 0")

    # Offline CLI writes sanitized receipt atomically with 0 network calls.
    rc_off = radar.main(["--offline", "--out", str(out_file), "--json"])
    _check(rc_off == 0, f"offline rc expected 0, got {rc_off}")
    _check(out_file.is_file(), "offline mode should write receipt to --out")
    off_payload = json.loads(capsys.readouterr().out)
    _check(off_payload["mode"] == "offline", "offline mode mismatch")
    _check(off_payload["network_calls_made"] == 0, "offline network calls must be 0")
    _check(off_payload["order_send_count"] == 0, "order_send_count must be 0")
    _check(off_payload["summary"]["accepted_items"] >= 8, "expected >= 8 offline items across 5 topics")
    _check(off_payload["summary"]["deduplicated_count"] >= 1, "expected offline duplicate removal")
    _check(off_payload["summary"]["filtered_tier_count"] >= 1, "expected offline T3 filtering")
    _check(all(it["untrusted_external_data"] is True for it in off_payload["items"]), "all items must be untrusted")

    # Live + offline together must fail closed (rc=2).
    rc_conflict = radar.main(["--live", "--offline", "--out", str(out_file)])
    _check(rc_conflict == 2, f"--live --offline conflict should return 2, got {rc_conflict}")


def test_live_pipeline_with_mocked_sources_and_inbox_card(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sample_arxiv_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>https://arxiv.org/abs/2611.77777</id>
        <published>2026-11-25T12:00:00Z</published>
        <title>Dispersion Premia Under Transaction Costs ($100M Test)</title>
        <summary>Out-of-sample dispersion study costing $50 per contract.</summary>
      </entry>
    </feed>"""

    sample_rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel><title>Fed</title>
      <item>
        <title>FOMC Statement</title>
        <link>https://www.federalreserve.gov/newsevents/pressreleases/monetary20261125a.htm</link>
        <description>Official release text.</description>
        <pubDate>Wed, 25 Nov 2026 19:00:00 GMT</pubDate>
      </item>
    </channel></rss>"""

    class _FakeResp:
        def __init__(self, text: str = "", json_obj: Any = None) -> None:
            self.text = text
            self._json = json_obj

        def json(self) -> Any:
            return self._json

    def _fake_http_get(url: str, **_kwargs: Any) -> _FakeResp:
        if "export.arxiv.org" in url:
            return _FakeResp(text=sample_arxiv_xml)
        if "federalreserve.gov" in url:
            return _FakeResp(text=sample_rss_xml)
        if "bls.gov" in url:
            return _FakeResp(text="<broken-xml")  # malformed XML must fail closed cleanly!
        if "api.github.com/repos/" in url and "/releases" in url:
            return _FakeResp(
                json_obj=[
                    {
                        "tag_name": "v0.17.6",
                        "name": "0.17.6",
                        "html_url": "https://github.com/astral-sh/ruff/releases/tag/0.17.6",
                        "published_at": "2026-11-21T00:00:00Z",
                        "body": "Ruff release notes.",
                    }
                ]
            )
        raise AssertionError(f"Unexpected mocked URL: {url}")

    def _fake_multi_source_search(query: str, *, sources: list[str], max_per_source: int = 4) -> dict[str, Any]:
        return {
            "schema": "naqex-multisource-search-v1",
            "query": query,
            "sources": sources,
            "results": {
                sources[0]: [
                    {
                        "title": "[2026, 9 cites] OpenAlex Quantitative Microstructure",
                        "url": "https://doi.org/10.1000/mock-openalex-1",
                        "snippet": "Mocked OpenAlex result via research_cli.",
                        "trust_tier": "T1_PRIMARY_OFFICIAL",
                    }
                ]
            },
            "errors": {},
        }

    def _fake_gh_fail(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=["gh"], returncode=1, stdout="", stderr="not logged in")

    monkeypatch.setattr(research_cli, "_http_get", _fake_http_get)
    monkeypatch.setattr(research_cli, "multi_source_search", _fake_multi_source_search)
    monkeypatch.setattr(subprocess, "run", _fake_gh_fail)

    out_file = tmp_path / "live_receipt.json"
    inbox_dir = tmp_path / "inbox"
    fixed_now = datetime(2026, 11, 27, 6, 45, 0, tzinfo=UTC)
    receipt = radar.run_radar(
        mode="live",
        out_path=out_file,
        topic_filter=["arxiv_qfin_tr_pm_st", "gh_releases_quant_and_tools", "official_macro_and_prop_sources"],
        max_per_topic_override=2,
        write_inbox=True,
        inbox_dir=inbox_dir,
        now_utc=fixed_now,
    )

    _check(receipt["status"] == "PARTIAL_OK", f"expected PARTIAL_OK due to malformed BLS XML, got {receipt['status']}")
    _check(receipt["network_calls_made"] > 0, "live mode should record network calls")
    _check(receipt["summary"]["accepted_items"] >= 4, "expected >= 4 mocked live items")
    _check(receipt["summary"]["error_count"] == 1, "expected 1 captured malformed XML error")
    _check(out_file.is_file(), "live receipt file not written")
    _check(b"\r\n" not in out_file.read_bytes(), "receipt must be LF-only")

    cards = list(inbox_dir.glob("20261127-auto-research-radar-*.md"))
    _check(len(cards) == 1, f"expected 1 inbox card, found {len(cards)}")
    card_text = cards[0].read_text(encoding="utf-8")
    _check(b"\r\n" not in cards[0].read_bytes(), "inbox card must be LF-only")
    _check("untrusted_external_data: true" in card_text, "inbox card missing untrusted_external_data frontmatter")
    _check("$" not in card_text, "inbox card must contain zero bare dollar signs")


def test_opsec_scrubber_and_python_O_enforcement() -> None:
    fake_gh = "ghp" + "_" + "A" * 34
    fake_openai = "sk" + "-" + "B" * 36
    fake_user_path = "C:" + "\\Users\\" + "Alice\\secret.txt"
    fake_lan_ip = ".".join(["192", "168", "1", "28"])
    fake_ts_ip = ".".join(["100", "72", "9", "4"])

    dirty = f"tok={fake_gh} key={fake_openai} path={fake_user_path} ip={fake_lan_ip} ts={fake_ts_ip}"
    clean = radar.scrub_opsec_text(dirty)
    for leaked in (fake_gh, fake_openai, "Alice", fake_lan_ip, fake_ts_ip):
        _check(leaked not in clean, f"OPSEC scrubber leaked sensitive token: {leaked}")

    # Verify -O does not strip RadarNetworkBlockedError or verify_receipt_invariants!
    code = (
        "import sys; from pathlib import Path; "
        f"sys.path.insert(0, {str(ROOT)!r}); "
        "from tooling.automation import auto_research_radar as r; "
        "raised = 0\n"
        "try:\n"
        "    r._fetch_live_query({'source': 'arxiv', 'query': 'x'}, timeout_sec=5.0, mode='offline')\n"
        "except r.RadarNetworkBlockedError:\n"
        "    raised += 1\n"
        "try:\n"
        "    r.verify_receipt_invariants({'schema': r.SCHEMA_VERSION, 'order_send_count': 1})\n"
        "except r.RadarValidationError:\n"
        "    raised += 1\n"
        "if raised != 2:\n"
        "    raise SystemExit(1)\n"
    )
    proc = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True, check=False)
    _check(proc.returncode == 0, f"-O guard check failed: rc={proc.returncode} stderr={proc.stderr}")


def test_adversarial_security_regressions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _block_all_network(monkeypatch)
    base_wl = radar.load_watchlist(radar.DEFAULT_WATCHLIST_PATH)
    policy = base_wl["trust_tier_policy"]

    # 1. Path-prefix segment boundary anti-spoofing
    _check(
        radar.classify_url_trust_tier("https://mql5.com/en/docs-spoofed/evil", policy=policy)
        == "T2_TECHNICAL_COMMUNITY",
        "path-prefix spoofing must not elevate to T1",
    )
    _check(
        radar.classify_url_trust_tier("https://mql5.com/en/docs", policy=policy) == "T1_PRIMARY_OFFICIAL",
        "exact /en/docs path should still classify as T1",
    )

    # 2. Bare '$' leak via URL path and watchlist_path in render_inbox_markdown
    dollar_fixture = {
        "gh_releases_quant_and_tools": [
            {
                "source": "github_releases",
                "title": "Release $100 Test",
                "url": "https://github.com/org/repo/releases/tag/v1$beta",
                "snippet": "Costs $0 USD.",
            }
        ]
    }
    rec = radar.run_radar(
        mode="offline",
        out_path=tmp_path / "dollar.json",
        topic_filter=["gh_releases_quant_and_tools"],
        offline_fixture=dollar_fixture,
    )
    rec["watchlist_path"] = "tooling/automation/configs/watch$list.json"
    md_text = radar.render_inbox_markdown(rec)
    _check("$" not in md_text, "rendered Markdown must contain zero bare dollar signs")
    _check("tag/v1%24beta" in md_text, "URL dollar sign must be percent-encoded")
    _check("watch%24list.json" in md_text, "frontmatter watchlist_path dollar sign must be percent-encoded")

    # 3. Bool (False == 0) rejected on all exact-zero invariants
    for field in ("order_send_count", "holdout_rows_analysed", "spend_vnd"):
        bad_wl = json.loads(json.dumps(base_wl))
        bad_wl[field] = False
        with pytest.raises(radar.RadarValidationError):
            radar.validate_watchlist_config(bad_wl)
        bad_rec = json.loads(json.dumps(rec))
        bad_rec[field] = False
        with pytest.raises(radar.RadarValidationError):
            radar.verify_receipt_invariants(bad_rec)
    bad_api_wl = json.loads(json.dumps(base_wl))
    bad_api_wl["supply_chain_guard"]["api_keys_required"] = False
    with pytest.raises(radar.RadarValidationError):
        radar.validate_watchlist_config(bad_api_wl)

    # 4. GitHub repo slug path traversal rejected in watchlist & fetcher
    for bad_repo in ("../users", "org/..", "./repo", "org/.hidden", "a..b/repo", "org/name..evil"):
        bad_slug_wl = json.loads(json.dumps(base_wl))
        bad_slug_wl["topics"][2]["queries"][0]["repo"] = bad_repo
        with pytest.raises(radar.RadarValidationError):
            radar.validate_watchlist_config(bad_slug_wl)
        with pytest.raises(radar.RadarValidationError):
            radar._fetch_github_releases_live(bad_repo, max_results=1, timeout_sec=5.0)

    # 5. IPv4-mapped IPv6 CGNAT / loopback / private SSRF blocked
    cgnat_v4 = ".".join(["100", "72", "1", "1"])
    loop_v4 = ".".join(["127", "0", "0", "1"])
    lan_v4 = ".".join(["192", "168", "1", "10"])
    for ssrf_url in (
        f"http://[::ffff:{cgnat_v4}]/admin",
        f"http://[::ffff:{loop_v4}]/metrics",
        f"http://[::ffff:{lan_v4}]/secret",
        "http://[::1]/local",
        "http://[::]/any",
    ):
        with pytest.raises(radar.RadarValidationError):
            radar.normalize_url(ssrf_url)

    # 6. Invalid --fixture returns rc=2 cleanly (not uncaught exception) + non-finite/bad timeout rejected
    rc_bad_fix = radar.main(["--offline", "--no-write", "--fixture", str(tmp_path / "nonexistent_fixture_xyz.json")])
    _check(rc_bad_fix == 2, f"missing --fixture must return rc=2, got {rc_bad_fix}")
    err_out = capsys.readouterr().err
    _check("ERROR:" in err_out, "missing --fixture must print scrubbed ERROR message to stderr")

    for bad_timeout in (float("nan"), float("inf"), float("-inf"), -5.0, 0.0, 31.0, True, False):
        with pytest.raises(radar.RadarValidationError):
            radar.run_radar(mode="dry-run", timeout_sec=bad_timeout, write_receipt=False)
