"""Lossless per-file Zstandard archives with preflight-before-unlink and restore."""
from pathlib import Path, PurePosixPath
import hashlib
import io
import json
import os

ARCHIVE = "evidence-zstd-v20"


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def contained(root, path):
    root, path = Path(root).absolute(), Path(path).absolute()
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("evidence_scope_escape")
    for p in (path, *path.parents):
        if p.is_symlink() or p.is_junction():
            raise ValueError("evidence_reparse_path")
        if p == root:
            break
    return path


def identity(path):
    s = path.stat(follow_symlinks=False)
    if s.st_nlink != 1:
        raise ValueError("evidence_hardlinked_original")
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def relative(value):
    p = PurePosixPath(value)
    if not value or p.is_absolute() or ".." in p.parts or "\\" in value or ":" in value:
        raise ValueError("evidence_manifest_relative_path")
    return p


class EvidenceStore:
    def __init__(self, root):
        self.root = Path(root).absolute()
        contained(self.root, self.root)
        self.manifest_path = self.root / ARCHIVE / "MANIFEST.json"
        self.manifest = None
        self.entries = {}
        if self.manifest_path.exists():
            contained(self.root, self.manifest_path)
            m = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if m.get("schema") != "lossless-evidence-zstd-v1" or Path(m["root"]).resolve() != self.root.resolve():
                raise ValueError("evidence_manifest_root_or_schema")
            for r in m["entries"]:
                src, dest = relative(r["relative"]), relative(r["compressed_relative"])
                if dest != PurePosixPath(ARCHIVE) / (str(src) + ".zst") or str(src) in self.entries:
                    raise ValueError("evidence_manifest_mapping")
                if r["bytes"] < 0 or r["compressed_bytes"] <= 0:
                    raise ValueError("evidence_manifest_sizes")
                self.entries[str(src)] = r
            self.manifest = m

    def _path(self, value):
        p = Path(value)
        return contained(self.root, p if p.is_absolute() else self.root / relative(p.as_posix()))

    def _decompress(self, row, destination=None):
        import zstandard as zstd
        p = self._path(row["compressed_relative"])
        if p.stat().st_size != row["compressed_bytes"] or digest(p) != row["compressed_sha256"]:
            raise ValueError("evidence_compressed_checksum")
        h, size = hashlib.sha256(), 0
        with p.open("rb") as f, zstd.ZstdDecompressor().stream_reader(f) as stream:
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                if size > row["bytes"]:
                    raise ValueError("evidence_decompression_size_overrun")
                h.update(chunk)
                if destination is not None:
                    destination.write(chunk)
        if size != row["bytes"] or h.hexdigest() != row["sha256"]:
            raise ValueError("evidence_original_roundtrip_checksum")

    def read_bytes(self, path):
        p = self._path(path)
        key = p.relative_to(self.root).as_posix()
        row = self.entries.get(key)
        if p.exists():
            data = p.read_bytes()
            if row and hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ValueError("evidence_changed_uncompressed_original")
            return data
        if row is None:
            raise FileNotFoundError(p)
        if row["bytes"] > 1024 ** 3:
            raise ValueError("evidence_in_memory_read_exceeds_1GiB")
        out = io.BytesIO(); self._decompress(row, out)
        return out.getvalue()

    def canonical_sha(self, path):
        p = self._path(path)
        if p.exists():
            return hashlib.sha256(self.read_bytes(p)).hexdigest()
        row = self.entries[p.relative_to(self.root).as_posix()]
        self._decompress(row)
        return row["sha256"]

    def numpy(self, path):
        import numpy as np
        return np.load(io.BytesIO(self.read_bytes(path)), allow_pickle=False)

    def restore(self, selected=None):
        rows = [self.entries[str(relative(selected))]] if selected else list(self.entries.values())
        # Verify every archive and collision before restoring any original.
        for row in rows:
            p = self._path(row["relative"])
            self._decompress(row)
            if p.exists() and digest(p) != row["sha256"]:
                raise ValueError("evidence_restore_collision")
        restored = 0
        for row in rows:
            p = self._path(row["relative"])
            if p.exists():
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            temp = self._path(row["compressed_relative"] + ".restore-tmp")
            with temp.open("xb") as out:
                self._decompress(row, out)
            os.link(temp, p)  # Atomic creation: never overwrite an existing canonical file.
            temp.unlink()
            restored += 1
        return restored


def prepare(root, *, min_bytes=1024 ** 2, level=9):
    import zstandard as zstd
    root = Path(root).absolute(); contained(root, root)
    if level < 9 or min_bytes < 1:
        raise ValueError("evidence_compression_contract")
    folder = root / ARCHIVE
    if folder.exists():
        raise ValueError("evidence_archive_attempt_already_exists")
    candidates = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs:
            contained(root, Path(directory) / name)
        for name in names:
            p = contained(root, Path(directory) / name)
            if p.suffix in (".json", ".jsonl", ".npy") and p.stat().st_size >= min_bytes:
                candidates.append((p, identity(p)))
    folder.mkdir()
    rows = []
    for p, original_identity in sorted(candidates):
        rel = p.relative_to(root).as_posix(); dest = folder / (rel + ".zst")
        contained(root, dest); dest.parent.mkdir(parents=True, exist_ok=True)
        h, count = hashlib.sha256(), 0
        with p.open("rb") as src, dest.open("xb") as out:
            with zstd.ZstdCompressor(level=level, write_checksum=True).stream_writer(
                    out, size=original_identity[2], closefd=False) as writer:
                while chunk := src.read(1024 * 1024):
                    h.update(chunk); count += len(chunk); writer.write(chunk)
        if identity(p) != original_identity or count != original_identity[2]:
            raise ValueError("evidence_original_changed_while_compressing")
        row = dict(relative=rel, bytes=count, sha256=h.hexdigest(), identity=original_identity,
                   compressed_relative=dest.relative_to(root).as_posix(), compressed_bytes=dest.stat().st_size,
                   compressed_sha256=digest(dest))
        EvidenceStore(root)._decompress(row)
        rows.append(row)
    manifest = dict(schema="lossless-evidence-zstd-v1", root=str(root), level=level,
        codec="Zstandard", entries=rows, all_original_bytes_roundtrip_verified=True,
        originals_removed=False, original_bytes=sum(r["bytes"] for r in rows),
        compressed_bytes=sum(r["compressed_bytes"] for r in rows))
    with (folder / "MANIFEST.json").open("x", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def apply(root, expected_manifest_sha256):
    store = EvidenceStore(root)
    if store.manifest is None or digest(store.manifest_path) != expected_manifest_sha256:
        raise ValueError("evidence_manifest_hash_mismatch")
    receipt = store.root / ARCHIVE / "APPLIED.json"
    if receipt.exists():
        raise ValueError("evidence_apply_attempt_already_exists")
    rows = list(store.entries.values())
    for row in rows:
        p = store._path(row["relative"])
        if identity(p) != row["identity"] or digest(p) != row["sha256"]:
            raise ValueError("evidence_original_drift_preflight")
        store._decompress(row)
    removed = []
    for row in rows:
        p = store._path(row["relative"])
        if identity(p) != row["identity"]:
            raise ValueError("evidence_original_drift_before_unlink")
        p.unlink(); removed.append(row["relative"])
    result = dict(manifest_sha256=expected_manifest_sha256, removed=removed,
        original_bytes=sum(r["bytes"] for r in rows), compressed_bytes=sum(r["compressed_bytes"] for r in rows),
        net_payload_bytes_saved=sum(r["bytes"] - r["compressed_bytes"] for r in rows),
        originals_removed=True, restored_originals_available=True, physical_freed_bytes_not_measured=True)
    with receipt.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, indent=2)
    return result


if __name__ == "__main__":
    import argparse
    from prop_v20_common import V19
    p=argparse.ArgumentParser();p.add_argument("action",choices=("prepare","apply","restore"))
    p.add_argument("--root",type=Path,default=V19);p.add_argument("--manifest-sha256");p.add_argument("--relative")
    a=p.parse_args()
    if a.root.resolve() != V19.resolve():raise ValueError("CLI_scope_is_only_completed_V19_job")
    value=prepare(a.root) if a.action=="prepare" else apply(a.root,a.manifest_sha256) if a.action=="apply" else dict(restored=EvidenceStore(a.root).restore(a.relative))
    print(json.dumps(value if a.action!="prepare" else {k:v for k,v in value.items() if k!="entries"}))
