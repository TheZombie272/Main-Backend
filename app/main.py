from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api_v1.api import api_router

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


app = FastAPI(title="Main-Backend")

app.include_router(api_router, prefix="/api/v1")
# Configure CORS to respond to browser preflight (OPTIONS) requests.
# Allow origins can be configured via the environment variable
# `CORS_ALLOW_ORIGINS` as a comma-separated list. If not set, allow
# `https://datacensus.site` by default (adjust as needed).
cors_env = os.environ.get("CORS_ALLOW_ORIGINS")
if cors_env:
    allow_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
else:
    allow_origins = ["https://datacensus.site"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _run_pipeline_script(extras: list[str] | None = None) -> int:
    """Run the `run_pipeline.py` script as a subprocess and return its exit code.

    This avoids importing the runner at module import time and keeps the
    execution isolated from the web process.
    """
    base = Path(__file__).resolve().parents[2]  # Main-Backend/ (repo root)
    script = base / "scripts" / "run_pipeline.py"
    if not script.exists():
        print(f"run_pipeline script not found: {script}")
        return 3

    cmd = [sys.executable, str(script)]
    if extras:
        cmd += extras

    # Use create_subprocess_exec so we don't block the event loop
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stdout:
            print(stdout.decode(errors="ignore"))
        if stderr:
            print(stderr.decode(errors="ignore"), file=sys.stderr)
        return proc.returncode
    except Exception as e:
        print(f"Error running pipeline subprocess: {e}", file=sys.stderr)
        return 4


async def _pipeline_scheduler_loop():
    """Background loop: wait until local midnight, then run pipeline on odd days.

    This task is resilient: exceptions are caught and logged; it continues
    running until the application stops.
    """
    print("Pipeline scheduler started")
    while True:
        try:
            now = datetime.now()
            # next midnight (local time)
            next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            wait_seconds = (next_midnight - now).total_seconds()
            # Sleep until next midnight
            await asyncio.sleep(wait_seconds)

            # At midnight; run only on odd-numbered days
            day = datetime.now().day
            if day % 2 == 1:
                print(f"Scheduler: today is day {day} (odd) — running pipeline")
                code = await _run_pipeline_script()
                print(f"Pipeline finished with exit code {code}")
            else:
                print(f"Scheduler: today is day {day} (even) — skipping pipeline")

        except asyncio.CancelledError:
            print("Pipeline scheduler cancelled")
            raise
        except Exception as exc:
            print(f"Pipeline scheduler error: {exc}", file=sys.stderr)
            # wait a short time before retrying to avoid busy-looping on persistent errors
            await asyncio.sleep(60)


@app.on_event("startup")
async def startup_event():
    # Lugar para inicializar conexiones a DB, caches, etc.
    # Optionally enable the scheduler with the environment variable
    # `RUN_PIPELINE_SCHEDULER=1`. When enabled, a background task will wake
    # at midnight and run the pipeline on odd days.
    enabled = os.environ.get("RUN_PIPELINE_SCHEDULER", "0")
    if enabled == "1":
        app.state._pipeline_task = asyncio.create_task(_pipeline_scheduler_loop())
        print("Pipeline scheduler enabled")
    else:
        print("Pipeline scheduler not enabled (set RUN_PIPELINE_SCHEDULER=1 to enable)")


@app.on_event("shutdown")
async def shutdown_event():
    # Cancel background scheduler if running
    task = getattr(app.state, "_pipeline_task", None)
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        print("Pipeline scheduler stopped")
