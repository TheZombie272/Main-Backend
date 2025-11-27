"""Utility helpers: CSV loading, chunking, payload prep and idempotency key."""
from typing import List, Dict, Iterable
import csv
import hashlib


def load_csv(path: str) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def chunked(iterable: List, size: int):
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


def _sanitize(s: str) -> str:
    if s is None:
        return ""
    return s.replace("\r", " ").replace("\x00", "")


def prepare_payload(records: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out = []
    for r in records:
        out.append({
            "uid": _sanitize((r.get("uid") or "").strip()),
            "name": _sanitize((r.get("name") or "").strip()),
            "description": _sanitize((r.get("description") or "").strip()),
            "url": _sanitize((r.get("url") or "").strip()),
            "tags": _sanitize((r.get("tags") or "").strip()),
        })
    return out


def batch_idempotency_key(batch: Iterable[Dict[str, str]]) -> str:
    uids = ",".join(sorted((item.get("uid") or "") for item in batch))
    return hashlib.sha256(uids.encode("utf-8")).hexdigest()
