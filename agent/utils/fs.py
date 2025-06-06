from pathlib import Path
import portalocker

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

class FileLock:
    def __init__(self, target: Path):
        self.target = Path(target).with_suffix(".lock")
        self._fh = None

    def __enter__(self):
        self._fh = open(self.target, "w")
        portalocker.lock(self._fh, portalocker.LOCK_EX)

    def __exit__(self, exc_type, exc, tb):
        portalocker.unlock(self._fh)
        self._fh.close()