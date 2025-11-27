"""HTTP client for posting batches."""
from typing import Tuple, Dict
import json


def post_json(url: str, data: object, timeout: int = 30) -> Tuple[int, str, Dict[str, str]]:
    """POST JSON to URL using urllib. Returns (status_code, text, headers).

    Headers are returned as a dict with lowercase keys.
    """
    import urllib.request
    import urllib.error

    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "send-batches/1.0"}
    for k in list(headers.keys()):
        v = str(headers[k]).replace("\r", " ").replace("\n", " ")
        headers[k] = v
    req = urllib.request.Request(url, data=payload, headers=headers)
    # debug header items shown by caller
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            try:
                hdrs = {k.lower(): v for k, v in resp.getheaders()}
            except Exception:
                hdrs = {}
            return resp.getcode(), text, hdrs
    except urllib.error.HTTPError as e:
        try:
            text = e.read().decode("utf-8", errors="replace")
        except Exception:
            text = str(e)
        try:
            hdrs = {k.lower(): v for k, v in e.headers.items()} if getattr(e, "headers", None) else {}
        except Exception:
            hdrs = {}
        return e.code or 0, text, hdrs
    except Exception as e:
        return 0, str(e), {}
