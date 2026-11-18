"""Bounded native-path reads; logical manifest paths never carry Windows prefixes."""
from contextlib import contextmanager
import ctypes
import os
from pathlib import Path
import stat


def logical_path(path):
    value = str(path)
    if value.startswith("\\\\?\\UNC\\"):
        return Path("\\\\" + value[8:])
    return Path(value[4:] if value.startswith("\\\\?\\") else value)


def io_path(path):
    path = Path(path)
    absolute = str(path.absolute())
    if os.name != "nt" or absolute.startswith("\\\\?\\"):
        return path
    return Path("\\\\?\\UNC\\" + absolute[2:] if absolute.startswith("\\\\") else "\\\\?\\" + absolute)


class PathGuard:
    def __init__(self):
        self.checked = set()

    def admit(self, path):
        path = logical_path(path)
        if ".." in path.parts or str(path).startswith("\\\\"):
            raise ValueError("NONLOCAL_OR_PARENT_PATH")
        path = path.absolute()
        for parent in reversed((path.parent, *path.parent.parents)):
            key = str(parent).casefold()
            if key in self.checked:
                continue
            info = io_path(parent).lstat()
            if getattr(info, "st_file_attributes", 0) & 0x400 or stat.S_ISLNK(info.st_mode):
                raise ValueError("REPARSE_TRAVERSAL_BLOCKED")
            self.checked.add(key)
        info = io_path(path).lstat()
        if getattr(info, "st_file_attributes", 0) & 0x400 or stat.S_ISLNK(info.st_mode):
            raise ValueError("REPARSE_TRAVERSAL_BLOCKED")
        return path, info


@contextmanager
def read_handle(path):
    if os.name != "nt":
        with path.open("rb") as stream:
            yield stream
        return
    import msvcrt
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    create.restype = wintypes.HANDLE
    # Read-sharing only: neither a writer nor a replacement can race this read.
    handle = create(str(path), 0x80000000, 1, None, 3, 0x00200080, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel.CloseHandle(handle)
        raise
    with os.fdopen(fd, "rb") as stream:
        yield stream


def read_bounded(path, limit, *, guard=None):
    path, info = (guard or PathGuard()).admit(path)
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ValueError("REGULAR_FILE_SIZE_LIMIT")
    with read_handle(io_path(path)) as stream:
        raw = stream.read(limit + 1)
        current = os.fstat(stream.fileno())
    if len(raw) > limit or (current.st_size, current.st_mtime_ns) != (info.st_size, info.st_mtime_ns):
        raise ValueError("FILE_CHANGED_DURING_READ")
    return raw
