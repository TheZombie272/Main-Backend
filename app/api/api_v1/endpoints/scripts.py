from fastapi import APIRouter, HTTPException
from pathlib import Path
import asyncio
import sys
from typing import List, Optional

router = APIRouter()


async def _run_download_script(extras: Optional[List[str]] = None, script_name: str = "download_asset_inventory.py") -> dict:
    # Compute repository root (Main-Backend/) relative to this file
    base = Path(__file__).resolve().parents[4]
    script = base / "scripts" / script_name
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
async def download_inventory(wait: bool = True, csv: Optional[str] = None, app_token: Optional[str] = None, no_token: bool = False):
    """Trigger download_asset_inventory.py.

    - `wait` (bool): if true (default) the endpoint waits for the subprocess to finish and
      returns `code`, `stdout`, `stderr`. If false, the script is launched in background and
      the endpoint returns the started pid information.
    - `csv` (optional): pass a CSV path to the script (maps to `--csv` argument).
    """
    # Decide which script to run: standard (with token) or no-token paginating downloader
    script_name = "download_no_token.py" if no_token else "download_asset_inventory.py"
    base = Path(__file__).resolve().parents[4]
    script = base / "scripts" / script_name
    if not script.exists():
        raise HTTPException(status_code=404, detail=f"Script not found: {script}")

    extras: List[str] = []
    # map csv param
    if csv:
        extras += ["--csv", csv]
    # app_token only relevant for the token-based script; pass as --app-token when provided
    if app_token and not no_token:
        extras += ["--app-token", app_token]

    if wait:
        result = await _run_download_script(extras or None, script_name=script_name)
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
