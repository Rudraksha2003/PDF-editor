import os

from app.storage.base import Storage

# Base directory for all job files; paths outside this are rejected (path traversal safety)
BASE_PATH = os.path.abspath(os.environ.get("PDF_JOBS_BASE", "/tmp/pdf-jobs"))


def _ensure_path_within_base(path: str) -> None:
    """Raise ValueError if path (after resolving . and ..) is outside BASE_PATH."""
    resolved = os.path.normpath(os.path.abspath(path))
    base = os.path.normpath(BASE_PATH)
    if not (resolved == base or resolved.startswith(base + os.sep)):
        raise ValueError("Path is outside allowed storage directory.")


class LocalStorage(Storage):
    def save(self, path: str, data: bytes) -> None:
        _ensure_path_within_base(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def read(self, path: str) -> bytes:
        _ensure_path_within_base(path)
        with open(path, "rb") as f:
            return f.read()
