"""
Downloader for Asset Inventory (datos.gov.co Socrata endpoint).
Fetches records in pages of 1000 using $limit/$offset and saves as NDJSON and CSV.

Usage examples:
  # optional: export APP token to increase rate limits
  export SODATA_APP_TOKEN=your_token_here

  # run and save JSON ndjson + csv
  python3 scripts/download_asset_inventory.py --out asset_inventory.json --csv asset_inventory.csv

The script will keep fetching until a page with fewer than `page_size` records is returned.
"""

from __future__ import annotations
import os
import time
import json
import csv
import argparse
from typing import List, Dict, Any, Optional

# Try to import requests; if it's not available, provide a minimal shim
# using urllib so the script can run without installing external packages.
try:
    import urllib.request
    import urllib.parse
except Exception:
    import urllib.request as _urllib_request
    import urllib.parse as _urllib_parse
    import ssl as _ssl

    class _Response:
        def __init__(self, code: int, headers: Dict[str, str], content: bytes):
            self.status_code = code
            self.headers = headers
            self._content = content
            self.text = content.decode('utf-8', errors='replace')

        def raise_for_status(self) -> None:
            if not (200 <= self.status_code < 300):
                raise Exception(f'HTTP {self.status_code}')

        def json(self) -> Any:
            return json.loads(self.text)

    class Session:
        def get(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[float] = None):
            if params:
                # urlencode will percent-encode keys like "$limit"; this works for query strings
                query = _urllib_parse.urlencode(params, doseq=True)
                sep = '&' if '?' in url else '?'
                url = url + sep + query
            req = _urllib_request.Request(url, headers=headers or {})
            ctx = _ssl.create_default_context()
            with _urllib_request.urlopen(req, timeout=timeout, context=ctx) as resp:
                content = resp.read()
                code = resp.getcode()
                hdrs = dict(resp.getheaders())
            return _Response(code, hdrs, content)

    # expose a requests-like interface used by the rest of the script
    class _RequestsModuleLike:
        Session = Session

    requests = _RequestsModuleLike()

BASE_URL = "https://www.datos.gov.co/resource/uzcf-b9dh.json"
DEFAULT_PAGE_SIZE = 1000


def fetch_page(_session, offset: int, limit: int, app_token: Optional[str] = None, timeout: int = 30) -> List[Dict[str, Any]]:
    params = {"$limit": limit, "$offset": offset}
    query = urllib.parse.urlencode(params)
    url = BASE_URL + "?" + query
    req = urllib.request.Request(url)
    if app_token:
        req.add_header("X-App-Token", app_token)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        text = data.decode("utf-8")
        return json.loads(text)


def download_all(out_path: str, page_size: int = DEFAULT_PAGE_SIZE, app_token: Optional[str] = None, max_retries: int = 5, backoff_base: float = 1.5) -> List[Dict[str, Any]]:
    session = None
    offset = 0
    all_records: List[Dict[str, Any]] = []

    while True:
        tries = 0
        while True:
            try:
                print(f"Fetching offset={offset} limit={page_size} ...", flush=True)
                page = fetch_page(session, offset=offset, limit=page_size, app_token=app_token)
                break
            except Exception as e:
                tries += 1
                if tries > max_retries:
                    raise
                sleep = backoff_base ** tries
                print(f"Fetch failed (try {tries}/{max_retries}): {e}. Backing off {sleep:.1f}s...", flush=True)
                time.sleep(sleep)

        count = len(page)
        print(f"Received {count} records")
        if count == 0:
            break

        all_records.extend(page)
        offset += count

        # If we got less than page_size, it's the last page
        if count < page_size:
            break

    # Save NDJSON (newline-delimited JSON) for robust streaming + JSON list
    ndjson_path = out_path if out_path.endswith('.ndjson') else out_path + '.ndjson'
    with open(ndjson_path, 'w', encoding='utf-8') as fh:
        for rec in all_records:
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(f"Saved NDJSON -> {ndjson_path}")

    # Also save pretty JSON array
    json_path = out_path if out_path.endswith('.json') else out_path + '.json'
    with open(json_path, 'w', encoding='utf-8') as fh:
        json.dump(all_records, fh, ensure_ascii=False)
    print(f"Saved JSON -> {json_path}")

    return all_records


def write_csv_from_records(records: List[Dict[str, Any]], csv_path: str):
    if not records:
        print("No records to write to CSV")
        return

    # determine the full set of fieldnames across records (union)
    fieldnames = []
    seen = set()
    for r in records:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)

    # write csv
    with open(csv_path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for r in records:
            # ensure all keys present
            row = {k: r.get(k, '') for k in fieldnames}
            writer.writerow(row)

    print(f"Saved CSV -> {csv_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', '-o', default='asset_inventory', help='Output base path (without extension). Creates <out>.json and <out>.ndjson')
    parser.add_argument('--csv', help='Also write CSV to this path (e.g. asset_inventory.csv)')
    parser.add_argument('--page-size', type=int, default=DEFAULT_PAGE_SIZE, help='Page size (default 1000)')
    parser.add_argument('--app-token', default=os.environ.get('SODATA_APP_TOKEN') or os.environ.get('SODATA_TOKEN'), help='Socrata app token (or env SODATA_APP_TOKEN)')
    parser.add_argument('--max-retries', type=int, default=5, help='Retries per page on failure')
    args = parser.parse_args()

    print('Downloading Asset Inventory from datos.gov.co')
    print(f'Base URL: {BASE_URL}')
    if args.app_token:
        print('Using app token from argument or environment')

    records = download_all(out_path=args.out, page_size=args.page_size, app_token=args.app_token, max_retries=args.max_retries)

    if args.csv:
        write_csv_from_records(records, args.csv)
    else:
        # if user didn't pass csv, also create CSV next to JSON by default
        default_csv = args.out if args.out.endswith('.csv') else args.out + '.csv'
        write_csv_from_records(records, default_csv)

    print(f'Done. Total records downloaded: {len(records)}')


if __name__ == '__main__':
    main()
