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

    runner = PipelineRunner()
    # The legacy CLI always executes the send step; pass-through extras are
    # forwarded to the send script.
    try:
        runner.run(extras=extras)
    except subprocess.CalledProcessError as e:
        # preserve original exit codes for compatibility with existing callers
        print(f"Pipeline failed with exit {e.returncode}")
        sys.exit(e.returncode)


class PipelineRunner:
    """Encapsulate the pipeline so it can be invoked programmatically.

    Usage:
      runner = PipelineRunner(base=Path("/path/to/scripts"))
      runner.run(extras=["--limit-batches", "1"], execute=False)
    """

    def __init__(self, base: Path | None = None):
        self.base = (Path(base).resolve() if base is not None else Path(__file__).resolve().parent)
        self.data_dir = self.base / "Data-reorganizate"
        self.reorganized = self.data_dir / "asset_inventory_reorganized.txt"
        self.reorganize_script = self.data_dir / "reorganize_assets.py"
        self.send_script = self.data_dir / "send_batches.py"

    def _ensure_data_dir(self):
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

    def _remove_reorganized(self):
        if self.reorganized.exists():
            try:
                self.reorganized.unlink()
            except Exception as e:
                raise RuntimeError(f"Failed to remove {self.reorganized}: {e}")

    def _run_reorganize(self):
        if not self.reorganize_script.exists():
            raise FileNotFoundError(f"Reorganize script not found: {self.reorganize_script}")
        subprocess.run([sys.executable, str(self.reorganize_script)], check=True)

    def _run_send(self, extras: list[str] | None = None, execute: bool = True):
        if not self.send_script.exists():
            raise FileNotFoundError(f"Send script not found: {self.send_script}")
        cmd = [sys.executable, str(self.send_script)]
        if execute:
            cmd.append("--execute")
        # Some callers pass a literal '--' to separate args; strip a leading
        # '--' if present so the downstream parser doesn't treat it as a value.
        if extras:
            if len(extras) > 0 and extras[0] == "--":
                extras = extras[1:]
            cmd += extras
        subprocess.run(cmd, check=True)

    def run(self, extras: list[str] | None = None, execute: bool = True):
        """Run the pipeline.

        - `extras` are forwarded to `send_batches.py`.
        - `execute` controls whether `--execute` is passed to the send script.
        """
        self._ensure_data_dir()
        # remove old reorganized file if present
        if self.reorganized.exists():
            print(f"Removing existing file: {self.reorganized}")
            self._remove_reorganized()

        print(f"Running reorganize script: {self.reorganize_script}")
        self._run_reorganize()

        print("Running send_batches")
        self._run_send(extras=extras, execute=execute)



if __name__ == "__main__":
    main()
