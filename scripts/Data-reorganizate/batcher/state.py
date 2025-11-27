"""State handling for tracking already-sent UIDs."""
from typing import Set, Iterable
import os


def load_sent_uids(path: str) -> Set[str]:
    s = set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                v = line.strip()
                if v:
                    s.add(v)
    except FileNotFoundError:
        return s
    except Exception:
        return s
    return s


def append_sent_uids(path: str, uids: Iterable[str]):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            for uid in uids:
                f.write(uid + "\n")
    except Exception:
        # best-effort: do not raise
        pass
