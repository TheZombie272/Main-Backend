from fastapi import APIRouter, Query, HTTPException
from typing import List
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from .fetch import _fetch_records_from_source
from .normalize import _normalize_record, Resource
from .filtering import _filter_by_type

router = APIRouter()


@router.get("/metadata-quality")
async def metadata_quality(type: str = Query(..., description="Filtrar por type (obligatorio)")):
    """Calcula métricas de calidad de metadatos sobre el Asset Inventory filtrado por `type`."""
    print(f"[metrics.handlers] /metadata-quality called with type={type!r}")
    records = await _fetch_records_from_source()
    print(f"[metrics.handlers] /metadata-quality fetched records={len(records)} (first_keys={list(records[0].keys())[:10] if records else None})")
    records = _filter_by_type(records, type)
    print(f"[metrics.handlers] /metadata-quality after _filter_by_type filtered_count={len(records)}")
    if records:
        sample = {k: records[0].get(k) for k in list(records[0].keys())[:10]}
        print(f"[metrics.handlers] /metadata-quality sample_record_keys_values={sample}")
    resources = [_normalize_record(r) for r in records]

    total = len(resources)
    if total == 0:
        # provide available type values to help the caller
        available_types = sorted({str(r.get('type')) for r in await _fetch_records_from_source() if r.get('type')})
        return {
            "total_resources": 0,
            "available_types_sample": available_types[:50],
            "note": "No records matched the requested type. Use one of the available type values shown.",
        }

    def has_field(r, attr):
        v = getattr(r, attr)
        return v is not None and (not isinstance(v, str) or v.strip() != "")

    title_count = sum(1 for r in resources if has_field(r, "title"))
    desc_count = sum(1 for r in resources if has_field(r, "description"))
    license_count = sum(1 for r in resources if has_field(r, "license"))
    contact_count = sum(1 for r in resources if has_field(r, "contact"))
    schema_count = sum(1 for r in resources if r.schema)

    formats = Counter((r.format or "unknown").lower() for r in resources)

    return {
        "total_resources": total,
        "percent_with_title": round(100 * title_count / total, 2),
        "percent_with_description": round(100 * desc_count / total, 2),
        "percent_with_license": round(100 * license_count / total, 2),
        "percent_with_contact": round(100 * contact_count / total, 2),
        "percent_with_schema": round(100 * schema_count / total, 2),
        "formats_distribution": dict(formats),
    }


@router.get("/content-coverage")
async def content_coverage(type: str = Query(..., description="Filtrar por type (obligatorio)")):
    records = await _fetch_records_from_source()
    records = _filter_by_type(records, type)
    resources = [_normalize_record(r) for r in records]

    total = len(resources)
    by_year = Counter()
    by_publisher = Counter()
    by_category = Counter()
    sizes = []

    for r in resources:
        if r.created_at:
            by_year[r.created_at.year] += 1
        if r.publisher:
            by_publisher[r.publisher] += 1
        if r.category:
            by_category[r.category] += 1
        if r.size_bytes is not None:
            sizes.append(r.size_bytes)

    size_stats = None
    if sizes:
        size_stats = {
            "count": len(sizes),
            "total_bytes": sum(sizes),
            "avg_bytes": int(sum(sizes) / len(sizes)),
            "min_bytes": min(sizes),
            "max_bytes": max(sizes),
        }

    return {
        "total_resources": total,
        "resources_by_year": dict(by_year),
        "top_publishers": by_publisher.most_common(10),
        "top_categories": by_category.most_common(10),
        "size_stats": size_stats,
    }


@router.get("/maintenance-activity")
async def maintenance_activity(type: str = Query(..., description="Filtrar por type (obligatorio)"),
                               obsolete_months: int = Query(12, description="Meses para considerar obsoleto")):
    records = await _fetch_records_from_source()
    records = _filter_by_type(records, type)
    resources = [_normalize_record(r) for r in records]

    total = len(resources)
    now = datetime.utcnow()
    update_intervals = []
    obsolete = []

    for r in resources:
        if r.created_at and r.updated_at:
            interval = (r.updated_at - r.created_at).days
            update_intervals.append(interval)
        if r.updated_at:
            if (now - r.updated_at) > timedelta(days=obsolete_months * 30):
                obsolete.append(r.id or r.title)

    avg_update_days = None
    if update_intervals:
        avg_update_days = sum(update_intervals) / len(update_intervals)

    return {
        "total_resources": total,
        "avg_update_days": avg_update_days,
        "obsolete_count": len(obsolete),
        "obsolete_examples": obsolete[:10],
    }


@router.get("/usage-engagement")
async def usage_engagement(type: str = Query(..., description="Filtrar por type (obligatorio)")):
    records = await _fetch_records_from_source()
    records = _filter_by_type(records, type)
    resources = [_normalize_record(r) for r in records]

    total = len(resources)
    downloads = []
    accesses = []

    for r in resources:
        if r.downloads is not None:
            downloads.append((r.id or r.title, r.downloads))
        if r.accesses is not None:
            accesses.append((r.id or r.title, r.accesses))

    downloads.sort(key=lambda x: x[1], reverse=True)
    accesses.sort(key=lambda x: x[1], reverse=True)

    total_downloads = sum(d for _, d in downloads)
    total_accesses = sum(a for _, a in accesses)

    return {
        "total_resources": total,
        "total_downloads": total_downloads,
        "total_accesses": total_accesses,
        "top_downloaded": downloads[:10],
        "top_accessed": accesses[:10],
    }


@router.get("/operational-kpis")
async def operational_kpis(type: str = Query(..., description="Filtrar por type (obligatorio)")):
    records = await _fetch_records_from_source()
    records = _filter_by_type(records, type)
    resources = [_normalize_record(r) for r in records]

    total = len(resources)
    open_license_count = sum(1 for r in resources if r.license and "open" in r.license.lower())
    schema_compliance = sum(1 for r in resources if r.schema)

    return {
        "total_resources": total,
        "percent_open_license": round(100 * open_license_count / total, 2) if total else None,
        "percent_schema_compliance": round(100 * schema_compliance / total, 2) if total else None,
    }


@router.get("/advanced-analytics")
async def advanced_analytics(type: str = Query(..., description="Filtrar por type (obligatorio)")):
    records = await _fetch_records_from_source()
    records = _filter_by_type(records, type)
    resources = [_normalize_record(r) for r in records]

    # Ejemplo simple: clasificación ABC por downloads (si disponible)
    scored = []
    for r in resources:
        score = r.downloads or r.accesses or 0
        scored.append((r.id or r.title or "unknown", score))
    scored.sort(key=lambda x: x[1], reverse=True)

    n = len(scored)
    a_cut = max(1, int(n * 0.2))
    b_cut = max(1, int(n * 0.5))

    abc = {"A": scored[:a_cut], "B": scored[a_cut:b_cut], "C": scored[b_cut:]}

    # tendencia mensual simple (creaciones por mes)
    monthly = defaultdict(int)
    for r in resources:
        if r.created_at:
            key = r.created_at.strftime("%Y-%m")
            monthly[key] += 1

    return {
        "abc_classification_top_counts": {k: len(v) for k, v in abc.items()},
        "abc_examples": {k: v[:5] for k, v in abc.items()},
        "monthly_creations": dict(monthly),
    }
