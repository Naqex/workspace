"""Check maintained entrypoints and submodule ownership without fetching or running products."""
from __future__ import annotations

import argparse
import configparser
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = {
    "projects/trader": "https://github.com/Naqex/trader.git",
    "projects/vi-dubber": "https://github.com/Naqex/vi-dubber.git",
    "projects/quant-trading": "https://github.com/Naqex/quant-trading.git",
    "projects/TradingAgents": "https://github.com/Naqex/TradingAgents.git",
    "tooling/reverse-skill": "https://github.com/zhaoxuya520/reverse-skill.git",
}
GUIDES = (
    "README.md", "CONTRIBUTING.md", "THIRD_PARTY_NOTICES.md",
    "docs/development/README.md", "docs/licensing.md", "tooling/search/README.md",
    "docs/archive/miro/README.md",
)
MARKDOWN_LINK = re.compile(r'!?\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+["\'][^"\']*["\'])?\s*\)')
HTML_LINK = re.compile(r'\b(?:href|src)=["\']([^"\']+)["\']', re.IGNORECASE)


def check_links(root: Path, guide: Path) -> list[str]:
    errors = []
    if not guide.is_file():
        return [f"Missing guide: {guide.relative_to(root)}"]
    content = guide.read_text(encoding="utf-8")
    # Examples in fenced code blocks are not navigation targets.
    prose = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    targets = [a or b for a, b in MARKDOWN_LINK.findall(prose)] + HTML_LINK.findall(prose)
    for target in targets:
        if re.match(r"^[A-Za-z]:[/\\]", target) or target.startswith(("/", "\\")):
            errors.append(f"{guide.relative_to(root)}: local absolute link: {target}")
            continue
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path:
            continue
        destination = (guide.parent / unquote(url.path)).resolve()
        if not destination.is_relative_to(root.resolve()):
            errors.append(f"{guide.relative_to(root)}: link escapes workspace: {target}")
        elif not destination.exists():
            errors.append(f"{guide.relative_to(root)}: broken link: {target}")
    if re.search(r"\b(?:mt5-tradingview-backtester|mk-trading-workspace|WMREPLAY)\b", prose):
        errors.append(f"{guide.relative_to(root)}: old product identity in maintained guide")
    return errors


def check_topology(modules_text: str, index_text: str) -> list[str]:
    config = configparser.ConfigParser(interpolation=None)
    config.read_string(modules_text)
    paths = {}
    errors = []
    for section in config.sections():
        path, url = config.get(section, "path", fallback=""), config.get(section, "url", fallback="")
        if path in paths:
            errors.append(f"Duplicate submodule path: {path}")
        paths[path] = url
    for path in sorted(paths.keys() | PRODUCTS.keys()):
        if paths.get(path) != PRODUCTS.get(path):
            errors.append(f"Unexpected submodule identity: {path}")
    pins = {}
    for line in index_text.splitlines():
        metadata, _, path = line.partition("\t")
        fields = metadata.split()
        if fields and fields[0] == "160000" and len(fields) == 3 and fields[2] == "0":
            pins[path] = fields[1]
    for path in sorted(pins.keys() | PRODUCTS.keys()):
        if path not in PRODUCTS or not re.fullmatch(r"[0-9a-f]{40}", pins.get(path, "")):
            errors.append(f"Missing or unexpected Git submodule pin: {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    root = parser.parse_args().root.resolve()
    errors = []
    for name in GUIDES:
        errors.extend(check_links(root, root / name))
    index = subprocess.check_output(["git", "-C", str(root), "ls-files", "--stage"], text=True)
    errors.extend(check_topology((root / ".gitmodules").read_text(encoding="utf-8"), index))
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Workspace contracts passed: {len(GUIDES)} guides, {len(PRODUCTS)} pinned submodules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
