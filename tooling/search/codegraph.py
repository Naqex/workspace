"""Pinned, on-demand code graph over the existing tracked-source allowlist."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

from xerj import ROOT, digest, source_files

VERSION = "1.6.2"
BUNDLE = ROOT / ".runtime/tools/codegraph" / VERSION / "node_modules/@colbymchenry/codegraph-win32-x64"
STATE = ROOT / ".runtime/search/codegraph"
CORPUS = STATE / "corpus"
MANIFEST = STATE / "manifest.json"


def snapshot():
    return {path.as_posix(): digest(source) for path, source in source_files()}


def freshness():
    if not MANIFEST.is_file():
        raise RuntimeError("No CodeGraph index. Run tooling/search/codegraph.py index.")
    saved = json.loads(MANIFEST.read_text(encoding="utf8"))
    if saved != {"version": VERSION, "files": snapshot()}:
        raise RuntimeError("CodeGraph index is stale. Re-run tooling/search/codegraph.py index; use rg meanwhile.")


def run(arguments):
    if os.name != "nt" or not (BUNDLE / "node.exe").is_file():
        raise RuntimeError("Pinned Windows x64 CodeGraph is missing. See tooling/search/README.md.")
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("CODEGRAPH_")}
    env.update(CODEGRAPH_NO_DOWNLOAD="1", CODEGRAPH_TELEMETRY="0", DO_NOT_TRACK="1",
               CODEGRAPH_NO_DAEMON="1", CODEGRAPH_NO_UPDATE_CHECK="1", NO_COLOR="1")
    return subprocess.run(
        [str(BUNDLE / "node.exe"), "--liftoff-only", "--disable-warning=ExperimentalWarning", *arguments],
        cwd=ROOT, env=env, capture_output=True, timeout=180,
        **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}),
    )


def checked(arguments):
    result = run(arguments)
    sys.stdout.buffer.write(result.stdout)
    sys.stderr.buffer.write(result.stderr)
    result.check_returncode()


def index():
    files = dict(source_files())
    expected = {path.as_posix(): digest(source) for path, source in files.items()}
    previous = json.loads(MANIFEST.read_text(encoding="utf8"))["files"] if MANIFEST.exists() else {}
    CORPUS.mkdir(parents=True, exist_ok=True)
    # Keep cleanup inventory after an interrupted rebuild, but never serve it.
    MANIFEST.write_text(json.dumps({"version": None, "files": {**previous, **expected}}), encoding="utf8")
    for old in previous.keys() - expected.keys():
        target = (CORPUS / old).resolve()
        if not target.is_relative_to(CORPUS.resolve()):
            raise RuntimeError("Unsafe corpus manifest path.")
        target.unlink(missing_ok=True)
    for relative, source in files.items():
        target = CORPUS / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if not (CORPUS / ".codegraph").exists():
        # Native init CLI also offers agent configuration rewrites; use only its DB API.
        checked(["-e", "require(process.argv[1]).CodeGraph.initSync(process.argv[2]).close()",
                 str(BUNDLE / "lib/dist/index.js"), str(CORPUS)])
    checked([str(BUNDLE / "lib/dist/bin/codegraph.js"), "index", str(CORPUS), "--quiet"])
    if snapshot() != expected or any(digest(CORPUS / path) != value for path, value in expected.items()):
        raise RuntimeError("Source changed during indexing; retry after edits settle.")
    MANIFEST.write_text(json.dumps({"version": VERSION, "files": expected}, indent=2), encoding="utf8")
    print(f"Indexed snapshot of {len(files)} tracked source/docs files; unsupported languages are not graphed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["index", "status", "query", "node", "callers", "callees", "impact", "explore"])
    parser.add_argument("target", nargs="?")
    parser.add_argument("--json", action="store_true", help="Native JSON output (except node/explore).")
    args = parser.parse_args()
    if args.action == "index":
        return index()
    if args.action != "status" and not args.target:
        parser.error("A symbol or query is required.")
    if args.json and args.action in {"node", "explore"}:
        parser.error("This command has no native JSON output.")
    freshness()
    command = [str(BUNDLE / "lib/dist/bin/codegraph.js"), args.action]
    command += [str(CORPUS)] if args.action == "status" else [args.target, "--path", str(CORPUS)]
    if args.json:
        command.append("--json")
    checked(command)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
