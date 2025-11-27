from typing import List, Dict, Any


def _filter_by_type(records: List[Dict[str, Any]], resource_type: str) -> List[Dict[str, Any]]:
    rt = resource_type.strip().lower()
    filtered = []
    for rec in records:
        # Only allow records that explicitly have approval_status == 'approved'
        approval = rec.get("approval_status")
        if approval is None:
            # if the field is missing, treat as not approved
            continue
        try:
            if str(approval).strip().lower() != "approved":
                continue
        except Exception:
            continue

        # Only allow records whose audience is 'public'
        audience = rec.get("audience") 
        if audience is None:
            # treat missing audience as not public
            continue
        try:
            if str(audience).strip().lower() != "public":
                continue
        except Exception:
            continue
        # check several possible fields
        candidates = [
            rec.get("type"),
            rec.get("resource_type"),
            rec.get("format"),
            rec.get("theme"),
            rec.get("category"),
            rec.get("topic"),
        ]
        # Special aliases: interpret `dataset`/`data` as entries that expose an API endpoint or url
        if rt in ( "data", "resource"):
            if rec.get("api_endpoint") or rec.get("url"):
                filtered.append(rec)
            continue

        # allow exact match or substring match to be more flexible
        matched = False
        for c in candidates:
            if c is None:
                continue
            cs = str(c).strip().lower()
            if rt == cs or rt in cs or cs in rt:
                matched = True
                break
        if matched:
            filtered.append(rec)
    return filtered
