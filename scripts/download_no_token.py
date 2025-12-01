"""Download Asset Inventory by paginating the public endpoint without an App Token.

This script paginates the SODA JSON endpoint and writes NDJSON and pretty JSON.
It uses a conservative User-Agent and inserts a small sleep between pages to
reduce the chance of rate-limiting.
"""
from __future__ import annotations
import time
import json
import argparse
import urllib.request
import urllib.parse
import sys
from typing import List, Dict, Any, Optional

DEFAULT_LIMIT = 1000
BASE_URL = "https://www.datos.gov.co/resource/uzcf-b9dh.json"


def fetch_page(offset: int, limit: int, base_url: Optional[str] = None, timeout: int = 30) -> List[Dict[str, Any]]:
    base = base_url or BASE_URL
    params = {"$limit": limit, "$offset": offset}
    query = urllib.parse.urlencode(params)
    url = base + "?" + query
    headers = {"User-Agent": "Main-Backend/1.0 (+https://github.com/TheZombie272/Main-Backend)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            text = data.decode("utf-8")
            return json.loads(text)
    except urllib.error.HTTPError as e:
        # Try to show body if present
        body = ""
        try:
            body = e.read().decode(errors="ignore")
        except Exception:
            pass
        print(f"HTTPError {e.code}: {e.reason} - {body}", file=sys.stderr)
        raise


def write_ndjson(records: List[Dict[str, Any]], ndjson_path: str):
    with open(ndjson_path, "a", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_json(records: List[Dict[str, Any]], json_path: str):
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False)


def write_csv(records: List[Dict[str, Any]], csv_path: str):
    import csv

    if not records:
        print("No records to write to CSV")
        return
    # union of keys
    fieldnames = []
    seen = set()
    for r in records:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)

    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            row = {k: r.get(k, "") for k in fieldnames}
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", "-o", default="asset_inventory", help="Output base path (without extension)")
    parser.add_argument("--csv", help="Also write CSV to this path (e.g. asset_inventory.csv)")
    parser.add_argument("--page-size", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds to sleep between pages")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--max-pages", type=int, default=0, help="Optional limit on pages to fetch (0 = no limit)")
    args = parser.parse_args()

    out_base = args.out
    ndjson_path = out_base if out_base.endswith(".ndjson") else out_base + ".ndjson"
    json_path = out_base if out_base.endswith(".json") else out_base + ".json"

    # truncate NDJSON file if exists
    open(ndjson_path, "w", encoding="utf-8").close()

    all_records: List[Dict[str, Any]] = []
    offset = 0
    page_num = 0
    while True:
        page_num += 1
        try:
            print(f"Fetching offset={offset} limit={args.page_size} ...", flush=True)
            page = fetch_page(offset=offset, limit=args.page_size, base_url=args.base_url)
        except Exception as e:
            print(f"Fetch failed: {e}", file=sys.stderr)
            sys.exit(2)

        count = len(page)
        print(f"Received {count} records")
        if count == 0:
            break

        # append to NDJSON and collect for JSON + CSV
        write_ndjson(page, ndjson_path)
        all_records.extend(page)

        if count < args.page_size:
            break

        offset += count
        if args.max_pages and page_num >= args.max_pages:
            break
        time.sleep(args.sleep)

    # write pretty JSON
    write_json(all_records, json_path)
    print(f"Saved NDJSON -> {ndjson_path}")
    print(f"Saved JSON -> {json_path}")

    if args.csv:
        write_csv(all_records, args.csv)
        print(f"Saved CSV -> {args.csv}")


if __name__ == '__main__':
    main()
