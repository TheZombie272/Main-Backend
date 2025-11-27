import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import HTTPException


async def _fetch_records_from_source(_source_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load asset inventory from a project-local file only.

    The function ignores any URL and will only read `asset_inventory.json` or
    `asset_inventory.csv` located at the project root. If neither file exists
    it raises an HTTPException with a clear message.
    """
    # Try several candidate locations for the project root where the asset file may live.
    # Historically we used `parents[4]` but the workspace root is `parents[5]`.
    resolved = Path(__file__).resolve()
    candidates = [
        resolved.parents[5] if len(resolved.parents) > 5 else None,  # workspace root (Main-Backend)
        resolved.parents[4] if len(resolved.parents) > 4 else None,  # app/
        Path.cwd(),
    ]

    local_json = None
    local_csv = None
    for cand in candidates:
        if not cand:
            continue
        j = cand / "asset_inventory.json"
        c = cand / "asset_inventory.csv"
        if j.exists():
            local_json = j
            break
        if c.exists():
            local_csv = c
            break

    if local_json:
        try:
            data = json.loads(local_json.read_text(encoding="utf-8"))
            print(f"[metrics.fetch] Using project-local JSON '{local_json}' records={len(data) if hasattr(data,'__len__') else 'unknown'}")
            return data
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading local JSON '{local_json}': {e}")

    if local_csv:
        try:
            with local_csv.open(newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                rows = [row for row in reader]
                print(f"[metrics.fetch] Using project-local CSV '{local_csv}' rows={len(rows)}")
                return rows
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading local CSV '{local_csv}': {e}")

    raise HTTPException(
        status_code=500,
        detail=(
            "No local asset inventory found. Place 'asset_inventory.json' or 'asset_inventory.csv' "
            "in the project root so the metrics endpoints can operate without network access."
        ),
    )
