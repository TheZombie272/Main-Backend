from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime


class Resource(BaseModel):
    id: Optional[str]
    title: Optional[str]
    description: Optional[str]
    license: Optional[str]
    contact: Optional[Any]
    format: Optional[str]
    publisher: Optional[str]
    category: Optional[str]
    size_bytes: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    downloads: Optional[int]
    accesses: Optional[int]
    schema: Optional[bool]


def _safe_parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        # handle Z suffix
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _normalize_record(rec: Dict[str, Any]) -> Resource:
    # map common field names from the asset inventory to our Resource model
    title = rec.get("title") or rec.get("name") or rec.get("resource_name") or rec.get("dataset")
    description = rec.get("description") or rec.get("notes")
    license = (
        rec.get("license")
        or rec.get("rights")
        or rec.get("license_title")
        or rec.get("commoncore_license")
    )
    contact = (
        rec.get("contact_point")
        or rec.get("contact")
        or rec.get("contact_point_email")
        or rec.get("commoncore_contactemail")
    )
    # Robust format detection: check many possible keys, handle lists and dicts
    fmt = None
    for k in (
        "format",
        "resource_format",
        "media_type",
        "mediaType",
        "filetype",
        "file_type",
        "mimetype",
        "mime_type",
        "distribution_format",
        "commoncore_format",
        "resource_type",
        "type",
    ):
        if k in rec and rec.get(k) is not None:
            v = rec.get(k)
            # if it's a list, take the first non-empty entry
            if isinstance(v, (list, tuple)):
                v = next((x for x in v if x), None)
            # if it's a dict, try to grab likely keys
            if isinstance(v, dict):
                v = v.get("format") or v.get("name") or v.get("type") or None
            if v is None:
                continue
            try:
                s = str(v).strip()
                if s:
                    fmt = s
                    break
            except Exception:
                continue
    publisher = (
        rec.get("organization")
        or rec.get("publisher")
        or rec.get("owner_org")
        or rec.get("commoncore_publisher")
        or rec.get("owner")
    )
    category = rec.get("category") or rec.get("theme") or rec.get("topic") or rec.get("commoncore_theme")
    size_bytes = None
    for k in ("size", "size_bytes", "file_size"):
        if k in rec:
            try:
                size_bytes = int(rec.get(k))
                break
            except Exception:
                pass
    created_at = _safe_parse_datetime(
        rec.get("metadata_created")
        or rec.get("created_at")
        or rec.get("date_created")
        or rec.get("creation_date")
        or rec.get("commoncore_issued")
    )
    updated_at = _safe_parse_datetime(
        rec.get("metadata_modified")
        or rec.get("updated_at")
        or rec.get("date_modified")
        or rec.get("last_metadata_updated_date")
        or rec.get("last_data_updated_date")
        or rec.get("commoncore_lastupdate")
    )
    downloads = None
    for k in ("download_count", "downloads", "view_count", "views"):
        if k in rec:
            try:
                downloads = int(rec.get(k))
                break
            except Exception:
                pass
    accesses = None
    for k in ("accesses", "access_count", "visits", "views"):
        if k in rec:
            try:
                accesses = int(rec.get(k))
                break
            except Exception:
                pass
    schema = bool(rec.get("schema") or rec.get("has_schema") or rec.get("fields"))

    return Resource(
        id=rec.get("id") or rec.get("resource_id") or rec.get("identifier"),
        title=title,
        description=description,
        license=license,
        contact=contact,
        format=fmt,
        publisher=publisher,
        category=category,
        size_bytes=size_bytes,
        created_at=created_at,
        updated_at=updated_at,
        downloads=downloads,
        accesses=accesses,
        schema=schema,
    )
