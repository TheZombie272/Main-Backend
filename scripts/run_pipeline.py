#!/usr/bin/env python3
"""Run the full pipeline from project root.

This script mirrors `Data-reorganizate/run_pipeline.sh` but implemented
in Python. It will:
 - remove `Data-reorganizate/asset_inventory_reorganized.txt` if present
 - run `Data-reorganizate/reorganize_assets.py`
 - run `Data-reorganizate/send_batches.py --execute` forwarding any
   extra arguments provided to this script

Usage:
  python3 run_pipeline.py [-- <args to send_batches.py>]
Example:
  python3 run_pipeline.py -- --limit-batches 1 --batch-size 1
"""
from __future__ import annotations
import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(add_help=False)
    # capture passthrough args after `--`
    parser.add_argument("--", dest="dash", help=argparse.SUPPRESS)
    known, extras = parser.parse_known_args()

    base = Path(__file__).resolve().parent
    data_dir = base / "Data-reorganizate"

    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        sys.exit(2)

    reorganized = data_dir / "asset_inventory_reorganized.txt"
    if reorganized.exists():
        print(f"Removing existing file: {reorganized}")
        try:
            reorganized.unlink()
        except Exception as e:
            print(f"Failed to remove {reorganized}: {e}")
            sys.exit(3)

    # Run reorganize_assets.py
    reorganize_script = data_dir / "reorganize_assets.py"
    if not reorganize_script.exists():
        print(f"Reorganize script not found: {reorganize_script}")
        sys.exit(4)

    print(f"Running reorganize script: {reorganize_script}")
    try:
        subprocess.run([sys.executable, str(reorganize_script)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"reorganize_assets.py failed with exit {e.returncode}")
        sys.exit(e.returncode)

    # Run send_batches.py with --execute and pass-through extras
    send_script = data_dir / "send_batches.py"
    if not send_script.exists():
        print(f"Send script not found: {send_script}")
        sys.exit(5)

    cmd = [sys.executable, str(send_script), "--execute"]
    if extras:
        cmd += extras

    print("Running send_batches:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"send_batches.py failed with exit {e.returncode}")
        sys.exit(e.returncode)

    print("Pipeline completed successfully.")


if __name__ == "__main__":
    main()
