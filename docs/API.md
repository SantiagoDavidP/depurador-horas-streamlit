# API Usage Guide (Current Contract)

Guia rapida de uso de la API actual para integraciones (React/scripts/Postman/curl).

## Base y entrypoint
- Base URL local: `http://localhost:8010`
- Entrypoint: `uvicorn api.main:app`

## Endpoints

| Endpoint | Metodo | Tipo de request | Respuesta clave |
|---|---|---|---|
| `/api/health` | GET | JSON | estado de salud |
| `/api/me` | GET | Header auth opcional segun config | usuario o null |
| `/api/profiles` | GET | JSON | catalogo de perfiles |
| `/api/batch/analyze` | POST | `multipart/form-data` con `files[]` | `auto_profile_id`, `profile_mapping`, `profile_settings`, `metadata` |
| `/api/batch/process` | POST | `multipart/form-data` con `files[]` + `payload` (string JSON) | `batch_id`, `results`, `is_baninter`, `default_client_name`, `auto_area` |
| `/api/batch/consolidate` | POST | JSON (`batchId`, opcional `clientName`, `outputFilename`) | `download_id`, `filename`, `consultores`, `total_horas`, `warnings` |
| `/api/batch/baninter-zip` | POST | JSON (`batchId`) | `download_id`, `filename` |
| `/api/individual/analyze` | POST | `multipart/form-data` con `file` | metadata y mapeo por hoja |
| `/api/individual/process` | POST | `multipart/form-data` con `file` + `payload` (string JSON) | `batch_id`, `results`, `consolidated`, `baninter_zip` |
| `/api/download/{file_id}` | GET | path param | bytes + header `Content-Disposition` |

## Contrato real de /api/batch/process (critico)

`/api/batch/process` recibe `multipart/form-data`:
- `files`: uno o mas archivos Excel (`files[]` en la mayoria de clientes).
- `payload`: STRING JSON.

### Payload minimo valido (sin profileId)
Debes enviar `mappingValues`; si no, retorna `400 Missing required mapping`.

```json
{
  "profileId": null,
  "mappingValues": {
    "date": "Fecha",
    "hours": "Horas",
    "description": "Descripcion",
    "project": "Proyecto"
  },
  "settings": {
    "correctSpelling": true
  }
}
```

### Payload valido usando profileId
Si `profileId` existe en catalogo, `mappingValues` puede omitirse.

```json
{
  "profileId": "cliente_nova_ti",
  "settings": {
    "correctSpelling": true,
    "duplicateSimilarityThreshold": 90,
    "duplicateMinOccurrences": 3,
    "hoursToleranceFactor": 1.5,
    "role": "Consultor"
  },
  "maxWorkers": 4
}
```

## Flujo recomendado: analyze -> process -> consolidate -> download

### 1) Analyze
```bash
curl -X POST "http://localhost:8010/api/batch/analyze" \
  -F "files=@C:/ruta/reporte.xlsx"
```

Tomar de respuesta:
- `auto_profile_id`
- `profile_mapping`

### 2) Process (con mappingValues construido)
```bash
curl -X POST "http://localhost:8010/api/batch/process" \
  -F "files=@C:/ruta/reporte.xlsx" \
  -F "payload={\"profileId\":null,\"mappingValues\":{\"date\":\"Fecha\",\"hours\":\"Horas\",\"description\":\"Descripcion\",\"project\":\"Proyecto\"},\"settings\":{\"correctSpelling\":true},\"maxWorkers\":4}"
```

Validar en respuesta:
- `batch_id`
- `results` (array)
- por resultado: `summary.quality_score`, `errores_criticos`, `errores_advertencia`

### 3) Consolidate
```bash
curl -X POST "http://localhost:8010/api/batch/consolidate" \
  -H "Content-Type: application/json" \
  -d "{\"batchId\":\"<BATCH_ID>\"}"
```

Tomar:
- `download_id`
- `filename`

### 4) Download
```bash
curl -L "http://localhost:8010/api/download/<DOWNLOAD_ID>" -o Consolidado.xlsx
```

## Errores comunes y como evitarlos

- `400 Missing required mapping`
  - Causa: `profileId` nulo y `mappingValues` ausente o incompleto.
  - Solucion: enviar `mappingValues.date`, `mappingValues.hours`, `mappingValues.description`.

- `400 Invalid JSON payload: ...`
  - Causa: `payload` no es JSON valido (recordar que es string dentro de multipart).
  - Solucion: serializar JSON correctamente y escapar comillas en curl.

- `404 Batch not found` en consolidate
  - Causa: `batchId` invalido o perdido por reinicio del proceso.
  - Solucion: usar el `batch_id` recien devuelto por `/api/batch/process`.

- `404 File not found` en download
  - Causa: `download_id` invalido o store en memoria reiniciado.
  - Solucion: descargar inmediatamente despues de generar.
