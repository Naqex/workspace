"""Optional local retrieval. Every command owns and stops its loopback node."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
LOCK = json.loads(Path(__file__).with_name("xerj.lock.json").read_text())
STATE = ROOT / ".runtime" / "search"
TOOLS = ROOT / ".runtime" / "tools" / "xerj" / LOCK["version"]
BINARY = TOOLS / LOCK["asset"].removesuffix(".zip") / "xerj.exe"
MANIFEST = STATE / "manifest.json"
SOURCE_SUFFIXES = {".md", ".py", ".rs", ".js", ".jsx", ".mjs", ".css"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def allowed(path, product=False):
    if path.suffix not in SOURCE_SUFFIXES:
        return False
    if product:
        return path.as_posix() in {"README.md", "AGENTS.md", "CONTRIBUTING.md"} or path.as_posix().startswith(("foundation_v2/web/src/", "foundation_v2/api-rust/src/", "ui/", "docs/"))
    return path.as_posix() in {"README.md", "AGENTS.md", "CONTRIBUTING.md"} or path.as_posix().startswith(("docs/development/", "tooling/search/"))


def source_files():
    for repo, prefix, product in [(ROOT, Path(), False), (ROOT / "projects/trader", Path("projects/trader"), True)]:
        if not (repo / ".git").exists():
            continue
        names = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode("utf8").split("\0")
        for name in filter(None, names):
            relative, source = Path(name), repo / name
            if allowed(relative, product) and source.is_file() and not source.is_symlink() and source.resolve().is_relative_to(repo.resolve()) and source.stat().st_size <= 1_000_000:
                yield prefix / relative, source


def install():
    if os.name != "nt":
        raise RuntimeError("This pinned asset supports Windows x64 only; rg remains available.")
    TOOLS.mkdir(parents=True, exist_ok=True)
    archive = TOOLS / "package.zip"
    if not archive.exists() or digest(archive) != LOCK["sha256"]:
        url = f'https://github.com/xerj-org/xerj/releases/download/v{LOCK["version"]}/{LOCK["asset"]}'
        with urlopen(url, timeout=60) as response, archive.open("wb") as target:
            shutil.copyfileobj(response, target)
    if digest(archive) != LOCK["sha256"]:
        raise RuntimeError("Xerj archive checksum mismatch; nothing executed.")
    with zipfile.ZipFile(archive) as package:
        for name in package.namelist():
            if not (TOOLS / name).resolve().is_relative_to(TOOLS.resolve()):
                raise RuntimeError("Archive contains an unsafe path.")
        package.extractall(TOOLS)
    # Detect later replacement of the extracted executable, too.
    (TOOLS / "binary.sha256").write_text(digest(BINARY), encoding="ascii")
    print(f'Installed Xerj {LOCK["version"]}; verified archive and binary.')


def verify_binary():
    stamp = TOOLS / "binary.sha256"
    if not BINARY.is_file() or not stamp.is_file() or digest(BINARY) != stamp.read_text().strip():
        raise RuntimeError("Xerj missing or changed. Run tooling/search/xerj.py install first.")


def freshness():
    if not MANIFEST.exists():
        raise RuntimeError("No search index. Run tooling/search/xerj.py index first.")
    expected = json.loads(MANIFEST.read_text(encoding="utf8"))["files"]
    current = {path.as_posix(): digest(source) for path, source in source_files()}
    if current != expected:
        raise RuntimeError("Search index is stale. Re-run tooling/search/xerj.py index; use rg meanwhile.")


@contextmanager
def node():
    verify_binary()
    STATE.mkdir(parents=True, exist_ok=True)
    run = STATE / f"run-{uuid.uuid4().hex[:12]}"
    run.mkdir()
    sockets = [socket.socket() for _ in range(3)]
    try:
        for sock in sockets:
            sock.bind(("127.0.0.1", 0))
        rest, grpc, es = [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()
    config = run / "xerj.toml"
    config.write_text(f'''[server]
rest_port = {rest}
grpc_port = {grpc}
es_compat_port = {es}
bind_address = "127.0.0.1"
data_dir = {json.dumps((STATE / "data").as_posix())}
auto_port = false
[auth]
enabled = true
[rerank]
enabled = false
[embedding]
mode = "lexical"
default_endpoint = ""
''', encoding="utf8")
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith(("XERJ_", "TYPESAFE_", "JEV_"))}
    env["XERJ_DISABLE_FEEDBACK"] = "true"
    url = f"http://127.0.0.1:{es}"
    env["XERJ_URL"] = url
    flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    with (run / "server.log").open("wb") as log:
        process = subprocess.Popen([str(BINARY), "--config", str(config)], cwd=ROOT, env=env, stdout=log, stderr=log, **flags)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError(f"Owned search node exited. Inspect {run.relative_to(ROOT)}/server.log; another search may own the index.")
                try:
                    with urlopen(f"http://127.0.0.1:{rest}/health/ready", timeout=.2) as response:
                        ready = response.status == 200
                except OSError:
                    ready = False
                if ready and (STATE / "data/admin.key").is_file():
                    break
                time.sleep(.1)
            else:
                raise RuntimeError("Owned search node did not become ready within 10 seconds.")
            key = (STATE / "data/admin.key").read_text().strip()
            env.update(XERJ_API_KEY=key, XERJ_AUTH=f"ApiKey {key}")
            (run / "owner.json").write_text(json.dumps({"pid":process.pid,"binary":str(BINARY),"config":str(config)}))
            yield url, env, flags
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def index():
    files = dict(source_files())
    snapshot = {path.as_posix(): digest(source) for path, source in files.items()}
    corpus = STATE / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    if MANIFEST.exists():
        for old in json.loads(MANIFEST.read_text(encoding="utf8"))["files"]:
            target = (corpus / old).resolve()
            if not target.is_relative_to(corpus.resolve()):
                raise RuntimeError("Unsafe corpus manifest path.")
            if old not in snapshot and target.is_file():
                target.unlink()
    for relative, source in files.items():
        target = corpus / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    with node() as (url, env, flags):
        result = subprocess.run([str(BINARY),"autoindex",str(corpus),"--prefix","naqex","--url",url,"--workers","2"], env=env, cwd=ROOT, capture_output=True, timeout=300, **flags)
        (STATE / "index.log").write_bytes(result.stdout + result.stderr)
        result.check_returncode()
    MANIFEST.write_text(json.dumps({"version":LOCK["version"],"files":snapshot}, indent=2), encoding="utf8")
    print(f"Indexed {len(files)} tracked source/docs files; original paths are relative to workspace root.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "index", "query", "def", "mcp"])
    parser.add_argument("query", nargs="?")
    args = parser.parse_args()
    if args.action == "install":
        return install()
    if args.action == "index":
        return index()
    if args.action != "mcp" and not args.query:
        parser.error("A query or symbol is required.")
    freshness()
    with node() as (url, env, flags):
        if args.action == "mcp":
            return subprocess.run([str(BINARY),"mcp","--url",url], env=env, cwd=ROOT, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, **flags).returncode
        command = "search" if args.action == "query" else "def"
        result = subprocess.run([str(BINARY),command,args.query,"--prefix","naqex","--url",url,"-k","5"], env=env, cwd=ROOT, capture_output=True, timeout=30, **flags)
        sys.stdout.buffer.write(result.stdout)
        sys.stderr.buffer.write(result.stderr)
        return result.returncode


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except (RuntimeError, subprocess.SubprocessError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
