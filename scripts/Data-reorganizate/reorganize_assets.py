#!/usr/bin/env python3
"""Reorganize asset inventory

Reads Main-Backend/asset_inventory.csv, applies approval/audience/type
filters consistent with app/api/api_v1/endpoints/metrics_pkg/filtering.py
and writes an output file where each record is formatted as:

uid-name
description, url, tags

If `--type` is provided, the script applies the same type matching
logic as `_filter_by_type`. If omitted, the script applies only the
approval_status == 'approved' and audience == 'public' filters.
"""
import csv
import argparse
import sys
import os
from pathlib import Path


def basic_prefilter(records):
    """Apply approval_status == 'approved' and audience == 'public'"""
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


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", help="resource type to filter by (optional)")
    # Compute sensible defaults relative to this script's location. The
    # repository layout places `asset_inventory.csv` two parents above this
    # file (Main-Backend/asset_inventory.csv). Use pathlib for clarity.
    base_dir = Path(__file__).resolve().parent
    # parent[0] -> scripts, parent[1] -> Main-Backend (project root)
    project_root = base_dir.parents[1]
    default_input = str(project_root / "asset_inventory.csv")
    default_output = str(base_dir / "asset_inventory_reorganized.txt")

    parser.add_argument("--input", help="path to asset_inventory.csv", default=default_input)
    parser.add_argument("--output", help="output file", default=default_output)
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)

    if not os.path.exists(input_path):
        print(f"Input CSV not found: {input_path}")
        sys.exit(2)

    records = load_csv(input_path)

    filtered = None

    # If a type is provided, try to import and use the exact filtering logic
    if args.type:
        # Prefer the local filtering module placed in this folder (Data-reorganizate/filtering.py)
        try:
            from filtering import _filter_by_type

            filtered = _filter_by_type(records, args.type)
        except Exception:
            # If import or call fails, fallback to basic prefilter and warn
            print("Warning: could not import local filtering module, falling back to basic filters", file=sys.stderr)
            filtered = basic_prefilter(records)
    else:
        filtered = basic_prefilter(records)

    # Write reorganized output
    Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as out:
        for rec in filtered:
            uid = (rec.get("uid") or "").strip()
            name = (rec.get("name") or "").strip()
            department = (rec.get("department") or "").strip()
            line1 = f"{uid}-{name}"

            description = (rec.get("description") or "").replace("\n", " ").strip()
            url = (rec.get("url") or "").strip()
            tags = (rec.get("tags") or "").strip()
            line2 = ", ".join([part for part in (description, url, tags) if part != ""]) or ""

            out.write(line1 + "\n")
            out.write(line2 + "\n\n")
            count += 1

    print(f"Wrote {count} records to {output_path}")


if __name__ == "__main__":
    main()
