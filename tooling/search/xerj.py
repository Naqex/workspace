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
import tempfile
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
NODE_LOCK = STATE / ".node.lock"
SOURCE_SUFFIXES = {".md", ".py", ".rs", ".js", ".jsx", ".mjs", ".css"}


def digest(path):
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
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
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


@contextmanager
def _acquire_node_lock(timeout_sec: float = 2.0):
    """Serialize exclusive access to STATE/data so concurrent calls fail cleanly without corrupting state."""
    STATE.mkdir(parents=True, exist_ok=True)
    lock_path = STATE / ".node.lock"
    fh = lock_path.open("a+b")
    locked = False
    deadline = time.monotonic() + max(0.0, timeout_sec)
    try:
        fh.seek(0)
        if os.name == "nt":
            import msvcrt

            if lock_path.stat().st_size == 0:
                fh.write(b"0")
                fh.flush()
            while True:
                try:
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    locked = True
                    break
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise RuntimeError(
                            "Xerj search index is currently locked by another process; "
                            "retry shortly or use rg / brain_cli."
                        ) from exc
                    time.sleep(0.05)
        else:
            import fcntl

            while True:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise RuntimeError(
                            "Xerj search index is currently locked by another process; "
                            "retry shortly or use rg / brain_cli."
                        ) from exc
                    time.sleep(0.05)
        yield
    finally:
        if locked:
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


def allowed(path, product=False, *, research=False):
    if path.is_absolute() or '..' in path.parts or path.suffix not in SOURCE_SUFFIXES:
        return False
    if product:
        if research and path.as_posix() == 'foundation_v2/docs/FOREX-RESEARCH.md':
            return True
        return path.as_posix() in {"README.md", "AGENTS.md", "CONTRIBUTING.md"} or path.as_posix().startswith(("foundation_v2/web/src/", "foundation_v2/api-rust/src/", "ui/", "docs/"))
    if research and path.suffix == '.md':
        if path.as_posix() in {'planning/CURRENT-CONTEXT.md', 'planning/CONTEXT-LIFECYCLE.md',
                              'tooling/ai-engines/STRATEGY-WORKFLOW.md',
                              'tooling/ai-engines/OBSERVABILITY.md', 'tooling/ai-engines/OPERATIONS.md'}:
            return True
        if (path.as_posix().startswith('planning/research/') and 'archive' not in {p.lower() for p in path.parts}
                and 'holdout' not in path.name.lower()):
            return True
        if (path.as_posix().startswith('knowledge/') and 'inbox' not in {p.lower() for p in path.parts}
                and 'archive' not in {p.lower() for p in path.parts}):
            return True
        if (path.as_posix().startswith('private_vault/owner/') and len(path.parts) == 3
                and 'holdout' not in path.name.lower()):
            return True
    return path.as_posix() in {"README.md", "AGENTS.md", "CONTRIBUTING.md"} or path.as_posix().startswith(("docs/development/", "tooling/search/"))


def source_files(*, research=False):
    private_owner_dir = ROOT / "private_vault" / "owner"
    private_owner_names: set[str] = set()
    if research and private_owner_dir.is_dir() and not private_owner_dir.is_symlink():
        for source in sorted(private_owner_dir.glob("*.md")):
            relative = Path("private_vault/owner") / source.name
            if (allowed(relative, False, research=True) and source.is_file() and not source.is_symlink()
                    and source.resolve().is_relative_to(private_owner_dir.resolve())
                    and source.stat().st_size <= 1_000_000):
                private_owner_names.add(source.name)
                yield relative, source
    for repo, prefix, product in [(ROOT, Path(), False), (ROOT / "projects/trader", Path("projects/trader"), True)]:
        if not (repo / ".git").exists():
            continue
        names = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode("utf8").split("\0")
        for name in filter(None, names):
            relative, source = Path(name), repo / name
            if research and not product and relative.parts[:2] == ("knowledge", "owner") and relative.name in private_owner_names:
                continue
            if allowed(relative, product, research=research) and source.is_file() and not source.is_symlink() and source.resolve().is_relative_to(repo.resolve()) and source.stat().st_size <= 1_000_000:
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
    current = {path.as_posix(): digest(source) for path, source in source_files(research=True)}
    if current != expected:
        raise RuntimeError("Search index is stale. Re-run tooling/search/xerj.py index; use rg meanwhile.")


@contextmanager
def node(*, lock_timeout: float = 2.0):
    verify_binary()
    STATE.mkdir(parents=True, exist_ok=True)
    with _acquire_node_lock(timeout_sec=lock_timeout):
        run = STATE / f"run-{uuid.uuid4().hex[:12]}"
        run.mkdir()
        try:
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
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            flags = {"creationflags": creation_flags} if os.name == "nt" else {}
            log_path = run / "server.log"
            with log_path.open("wb") as log:
                process = subprocess.Popen(
                    [str(BINARY), "--config", str(config)],
                    cwd=ROOT,
                    env=env,
                    stdout=log,
                    stderr=log,
                    creationflags=creation_flags,
                )
                try:
                    for _ in range(100):
                        if process.poll() is not None:
                            log.flush()
                            tail = ""
                            try:
                                tail = log_path.read_text(encoding="utf8", errors="replace").strip()[-300:]
                            except OSError:
                                pass
                            suffix = f" ({tail})" if tail else ""
                            raise RuntimeError(
                                "Owned search node exited cleanly before readiness; "
                                f"another search may own the index{suffix}."
                            )
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
                    owner_meta = {"pid": process.pid, "binary": str(BINARY), "config": str(config)}
                    (run / "owner.json").write_text(json.dumps(owner_meta))
                    yield url, env, flags
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
        finally:
            shutil.rmtree(run, ignore_errors=True)


def index():
    files = dict(source_files(research=True))
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
    with node(lock_timeout=10.0) as (url, env, flags):
        result = subprocess.run([str(BINARY), "autoindex", str(corpus), "--prefix", "naqex", "--url", url, "--workers", "2"], env=env, cwd=ROOT, capture_output=True, timeout=300, **flags)
        (STATE / "index.log").write_bytes(result.stdout + result.stderr)
        result.check_returncode()
    _atomic_write_text(MANIFEST, json.dumps({"version": LOCK["version"], "files": snapshot}, indent=2))
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
            return subprocess.run([str(BINARY), "mcp", "--url", url], env=env, cwd=ROOT, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, **flags).returncode
        command = "search" if args.action == "query" else "def"
        result = subprocess.run([str(BINARY), command, args.query, "--prefix", "naqex", "--url", url, "-k", "5"], env=env, cwd=ROOT, capture_output=True, timeout=30, **flags)
        sys.stdout.buffer.write(result.stdout)
        sys.stderr.buffer.write(result.stderr)
        return result.returncode


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except (RuntimeError, subprocess.SubprocessError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
