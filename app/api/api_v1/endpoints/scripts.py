from fastapi import APIRouter, HTTPException
from pathlib import Path
import asyncio
import sys
from typing import List, Optional

router = APIRouter()


async def _run_download_script(extras: Optional[List[str]] = None) -> dict:
    # Compute repository root (Main-Backend/) relative to this file
    base = Path(__file__).resolve().parents[4]
    script = base / "scripts" / "download_asset_inventory.py"
    if not script.exists():
        return {"code": 3, "stdout": "", "stderr": f"Script not found: {script}"}

    cmd = [sys.executable, str(script)]
    if extras:
        cmd += extras

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    except Exception as e:
        return {"code": 4, "stdout": "", "stderr": f"Failed to start subprocess: {e}"}

    stdout, stderr = await proc.communicate()
    out = stdout.decode(errors="ignore") if stdout else ""
    err = stderr.decode(errors="ignore") if stderr else ""
    return {"code": proc.returncode, "stdout": out, "stderr": err}


@router.post("/download-inventory")
async def download_inventory(wait: bool = True, csv: Optional[str] = None):
    """Trigger download_asset_inventory.py.

    - `wait` (bool): if true (default) the endpoint waits for the subprocess to finish and
      returns `code`, `stdout`, `stderr`. If false, the script is launched in background and
      the endpoint returns the started pid information.
    - `csv` (optional): pass a CSV path to the script (maps to `--csv` argument).
    """
    # If running in wait mode, run and await result
    base = Path(__file__).resolve().parents[4]
    script = base / "scripts" / "download_asset_inventory.py"
    if not script.exists():
        raise HTTPException(status_code=404, detail=f"Script not found: {script}")

    extras: List[str] = []
    if csv:
        extras += ["--csv", csv]

    if wait:
        result = await _run_download_script(extras or None)
        return result

    # Launch in background without awaiting
    cmd = [sys.executable, str(script)]
    if extras:
        cmd += extras

    # Start subprocess detached
    try:
        proc = await asyncio.create_subprocess_exec(*cmd)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start subprocess: {e}")

    return {"started": True, "pid": proc.pid}
