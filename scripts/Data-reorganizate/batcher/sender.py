"""Sender module: handles sending batches with retries, backoff and state updates."""
from typing import List, Dict
import time
import json
from . import client, state, utils


def send_payloads(payloads: List[List[Dict[str, str]]], args, state_path: str) -> None:
    total_batches = len(payloads)
    # parse accept status
    try:
        accept_status = set(int(s.strip()) for s in str(args.accept_status).split(",") if s.strip())
    except Exception:
        accept_status = {200}
    success_substring = (args.success_substring or "").strip().lower()

    for idx, body in enumerate(payloads, start=1):
        print(f"Sending batch {idx}/{total_batches} (items: {len(body)})...")
        attempt = 0
        sent = False
        while attempt < args.max_retries and not sent:
            attempt += 1
            status, resp_text, resp_headers = client.post_json(args.webhook, body, timeout=args.http_timeout)
            lower = (resp_text or "").lower()
            accepted = False
            if status in accept_status:
                if not success_substring:
                    accepted = True
                elif success_substring in lower:
                    accepted = True
                else:
                    # inspect JSON body
                    try:
                        parsed = json.loads(resp_text)
                        if isinstance(parsed, dict):
                            v = parsed.get("status")
                            if isinstance(v, int) and v in accept_status:
                                accepted = True
                            elif isinstance(v, str) and success_substring in v.lower():
                                accepted = True
                            else:
                                for val in parsed.values():
                                    if isinstance(val, str) and success_substring in val.lower():
                                        accepted = True
                                        break
                    except Exception:
                        pass

                    # check headers
                    try:
                        hdrs = {k.lower(): v for k, v in (resp_headers or {}).items()}
                        for key in ("status", "x-status", "result", "x-result", "message"):
                            if key in hdrs:
                                val = (hdrs.get(key) or "").strip().lower()
                                if val in ("ok", "success"):
                                    accepted = True
                                    break
                                if success_substring and success_substring in val:
                                    accepted = True
                                    break
                    except Exception:
                        pass

            if accepted:
                print(f"Batch {idx} accepted (status={status}).")
                sent = True
                batch_uids = [ (item.get("uid") or "").strip() for item in body if (item.get("uid") or "").strip() ]
                if batch_uids:
                    state.append_sent_uids(state_path, batch_uids)
                time.sleep(args.wait_seconds)
                break
            else:
                print(f"Batch {idx} attempt {attempt} failed (status={status}). Response excerpt: {resp_text[:200]!r}")
                if attempt < args.max_retries:
                    backoff = args.wait_seconds * (2 ** (attempt - 1))
                    time.sleep(backoff)
        if not sent:
            print(f"Failed to deliver batch {idx} after {args.max_retries} attempts. Aborting.")
            raise RuntimeError(f"Batch {idx} failed")
