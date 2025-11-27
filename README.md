# Main-Backend

Plantilla base para un backend en Python usando FastAPI.

Requisitos:
- Python 3.10+

Instalación y ejecución rápida:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints:
- `GET /api/v1/health` — estado del servicio
- `GET /api/v1/items` — listar items (demo)
- `POST /api/v1/items` — crear item (demo)

**API Endpoints**

- **Health**
	- `GET /api/v1/health` — Estado del servicio.

- **Metrics (Asset Inventory)**
	- `GET /api/v1/metrics/metadata-quality?type=<type>` — Métricas de calidad de metadatos filtradas por `type` (parámetro `type` obligatorio).
	- `GET /api/v1/metrics/content-coverage?type=<type>` — Cobertura de contenido (por año, por editor, por categoría, tamaños) filtrada por `type`.
	- `GET /api/v1/metrics/maintenance-activity?type=<type>&obsolete_months=<n>` — Métricas de mantenimiento y obsolescencia (parámetro `type` obligatorio, `obsolete_months` opcional, por defecto 12).
	- `GET /api/v1/metrics/usage-engagement?type=<type>` — Métricas de uso (descargas, accesos) filtradas por `type`.
	- `GET /api/v1/metrics/operational-kpis?type=<type>` — KPIs operacionales (porcentaje de licencias abiertas, cumplimiento de esquema) filtradas por `type`.
	- `GET /api/v1/metrics/advanced-analytics?type=<type>` — Análisis avanzado (clasificación ABC por descargas/accesos, tendencia mensual) filtrado por `type`.

Notes:

- All metric endpoints require a `type` query parameter. The service reads the asset inventory from the local files `asset_inventory.json` / `asset_inventory.csv` placed in the project root; it will not fetch the dataset from the network.
- The metrics endpoints pre-filter records so that only entries with `approval_status == 'approved'` and `audience == 'public'` are considered.

**Response Examples**

- `GET /api/v1/health`
	- Response: 200 OK
```json
{ "status": "ok" }
```

- `GET /api/v1/metrics/metadata-quality?type=<type>`
	- Description: calcula porcentajes de campos de metadatos y distribución de formatos.
	- Response: 200 OK
```json
{
	"total_resources": 123,
	"percent_with_title": 95.12,
	"percent_with_description": 89.43,
	"percent_with_license": 70.73,
	"percent_with_contact": 45.53,
	"percent_with_schema": 12.2,
	"formats_distribution": { "csv": 50, "json": 30, "unknown": 43 }
}
```

- `GET /api/v1/metrics/content-coverage?type=<type>`
	- Description: agregados por año/editor/categoría y estadísticas de tamaño.
	- Response: 200 OK
```json
{
	"total_resources": 123,
	"resources_by_year": { "2024": 40, "2025": 83 },
	"top_publishers": [["Gobernacion X", 12], ["Ministerio Y", 8]],
	"top_categories": [["Salud", 20], ["Educacion", 15]],
	"size_stats": { "count": 40, "total_bytes": 12345678, "avg_bytes": 308641, "min_bytes": 1024, "max_bytes": 2048000 }
}
```

- `GET /api/v1/metrics/maintenance-activity?type=<type>&obsolete_months=<n>`
	- Description: calcula intervalo promedio de actualización y recursos obsoletos.
	- Response: 200 OK
```json
{
	"total_resources": 123,
	"avg_update_days": 180.5,
	"obsolete_count": 5,
	"obsolete_examples": ["dataset-a", "dataset-b"]
}
```

- `GET /api/v1/metrics/usage-engagement?type=<type>`
	- Description: suma descargas y accesos, y lista top recursos.
	- Response: 200 OK
```json
{
	"total_resources": 123,
	"total_downloads": 10234,
	"total_accesses": 52345,
	"top_downloaded": [["id1", 1200], ["id2", 800]],
	"top_accessed": [["id3", 4000], ["id4", 3500]]
}
```

- `GET /api/v1/metrics/operational-kpis?type=<type>`
	- Description: KPIs operacionales (licencias abiertas y cumplimiento de esquema).
	- Response: 200 OK
```json
{
	"total_resources": 123,
	"percent_open_license": 42.28,
	"percent_schema_compliance": 12.2
}
```

- `GET /api/v1/metrics/advanced-analytics?type=<type>`
	- Description: clasificación ABC por descargas/accesos y series mensuales de creación.
	- Response: 200 OK
```json
{
	"abc_classification_top_counts": { "A": 10, "B": 30, "C": 83 },
	"abc_examples": { "A": [["id1", 1200]], "B": [["id2", 800]], "C": [["id100", 2]] },
	"monthly_creations": { "2025-05": 12, "2025-06": 8 }
}
```

Ejecutar tests:

```bash
pytest -q
```
