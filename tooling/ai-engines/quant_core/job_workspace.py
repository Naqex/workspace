"""Worktree-bound offline jobs: one writer and private temporary files."""
import atexit
import hashlib
import json
import os
from pathlib import Path
import uuid
from quant_core.native_paths import PathGuard, io_path, read_bounded


class JobWorkspace:
    def __init__(self, base, workspace):
        self.workspace = str(Path(workspace).resolve())
        identity = hashlib.sha256(os.path.normcase(self.workspace).encode()).hexdigest()[:12]
        self.root = Path(base) / identity
        self.token = uuid.uuid4().hex
        self.lock = None

    def activate(self):
        if self.lock is not None:
            return self.root
        if ".." in self.root.parts or str(self.root).startswith("\\\\"):
            raise ValueError("JOB_ROOT_MUST_BE_LOCAL")
        missing, at = [], self.root.absolute()
        while not at.exists():
            missing.append(at)
            at = at.parent
        guard = PathGuard()
        guard.admit(at)
        for path in reversed(missing):
            try:
                io_path(path).mkdir()
            except FileExistsError:
                pass
            guard.admit(path)
        guard.admit(self.root)
        owner = self.root / "workspace-owner.json"
        expected = dict(schema="OfflineJobWorkspace-v1", workspace=self.workspace,
                        root=str(self.root.absolute()))
        try:
            with io_path(owner).open("x", encoding="utf-8") as out:
                json.dump(expected, out, indent=2)
        except FileExistsError:
            current = json.loads(read_bounded(owner,4096))
            if current != expected:
                raise ValueError("FOREIGN_JOB_OWNER")
        path = self.root / "writer.lock"
        try:
            handle = io_path(path).open("x", encoding="utf-8")
        except FileExistsError:
            raise ValueError("JOB_WRITER_ALREADY_OWNED") from None
        json.dump(dict(pid=os.getpid(), token=self.token, workspace=self.workspace), handle)
        handle.flush()
        self.lock = handle
        io_path(self.root / "tmp").mkdir(exist_ok=True)
        guard.admit(self.root / "tmp")
        atexit.register(self.close)
        return self.root

    def close(self):
        if self.lock is None:
            return
        self.lock.close()
        self.lock = None
        path = self.root / "writer.lock"
        value = json.loads(read_bounded(path,4096))
        if value.get("token") == self.token:
            io_path(path).unlink()

    def environment(self, inherited=None):
        self.activate()
        result = dict(os.environ if inherited is None else inherited)
        for key in tuple(result):
            if key.startswith(("TW_V2_", "TW_AI_", "TW_CHATGPT_", "MT5_", "FTMO_")):
                result.pop(key)
        result.update(TEMP=str(self.root/"tmp"), TMP=str(self.root/"tmp"),
                      TW_RESEARCH_WORKSPACE=self.workspace, TW_RESEARCH_JOB_ROOT=str(self.root))
        return result
