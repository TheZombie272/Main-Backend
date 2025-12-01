#!/usr/bin/env python3
"""Orchestrator for sending batches. Delegates logic to `batcher` package."""
import argparse
import os
import sys
import json
from pathlib import Path
from batcher import utils, state, send_payloads

try:
    from filtering import _filter_by_type
except Exception:
    _filter_by_type = None


def basic_prefilter(records):
    out = []
    for rec in records:
        approval = rec.get("approval_status")
        if approval is None:
            continue
        try:
            if str(approval).strip().lower() != "approved":
                continue
        except Exception:
            continue

        audience = rec.get("audience")
        if audience is None:
            continue
        try:
            if str(audience).strip().lower() != "public":
                continue
        except Exception:
            continue

        out.append(rec)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--webhook", default=os.environ.get("WEBHOOK_URL", "https://uzuma.duckdns.org/webhook/28f6ad24-074c-4914-84a5-695e2eff505d"),
                        help="Webhook URL (or set env WEBHOOK_URL)")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--type")
    # Compute default path to asset_inventory.csv located at project root
    base_dir = Path(__file__).resolve().parent
    project_root = base_dir.parents[1]
    default_input = str(project_root / "asset_inventory.csv")
    parser.add_argument("--input", default=default_input)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--state-file", default=os.path.join(os.path.dirname(__file__), "batcher", "sent_uids.txt"))
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--wait-seconds", type=float, default=1.0)
    parser.add_argument("--http-timeout", type=int, default=180)
    parser.add_argument("--accept-status", default="200")
    parser.add_argument("--success-substring", default="terminado")
    parser.add_argument("--limit-batches", type=int, default=0)
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f"Input CSV not found: {input_path}")
        sys.exit(2)

    records = utils.load_csv(input_path)

    if args.type and _filter_by_type is not None:
        try:
            filtered = _filter_by_type(records, args.type)
        except Exception:
            print("Warning: filtering._filter_by_type failed, falling back to basic prefilter", file=sys.stderr)
            filtered = basic_prefilter(records)
    elif args.type and _filter_by_type is None:
        print("Warning: local filtering._filter_by_type not available, using basic filters", file=sys.stderr)
        filtered = basic_prefilter(records)
    else:
        filtered = basic_prefilter(records)

    print(f"Total records after filtering: {len(filtered)}")

    state_path = os.path.abspath(args.state_file)
    sent_uids = state.load_sent_uids(state_path)
    if sent_uids:
        remaining = []
        skipped = 0
        for r in filtered:
            uid = (r.get("uid") or "").strip()
            if uid and uid in sent_uids:
                skipped += 1
                continue
            remaining.append(r)
        filtered = remaining
        print(f"Skipped {skipped} records already marked as sent (state file: {state_path})")

    payloads = [utils.prepare_payload(chunk) for chunk in utils.chunked(filtered, args.batch_size)]
    total_batches = len(payloads)
    print(f"Batches to send (size {args.batch_size}): {total_batches}")

    if args.limit_batches and args.limit_batches > 0:
        payloads = payloads[: args.limit_batches]
        print(f"Limiting to first {len(payloads)} batches for testing")

    if not args.execute:
        print("Dry-run mode (no HTTP requests sent). Showing preview of first batch:")
        if total_batches > 0:
            print(json.dumps(payloads[0][:5], ensure_ascii=False, indent=2))
        print("Run with --execute to actually POST batches to the webhook.")
        return

    # send
    try:
        send_payloads(payloads, args, state_path)
    except Exception as e:
        print("Error during sending:", e)
        sys.exit(3)


if __name__ == "__main__":
    main()
