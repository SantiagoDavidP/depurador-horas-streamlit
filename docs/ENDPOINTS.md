# Endpoints Backend (FastAPI)

Documentacion operativa del contrato real del backend para integracion frontend.
Basado en OpenAPI actual (`/docs`) y en el comportamiento real de handlers.

## A) Overview

- El backend procesa timesheets Excel en 2 flujos:
  - Batch: analizar varios archivos, procesarlos, consolidarlos y descargar reportes.
  - Individual: analizar un archivo multihja, procesar por colaborador, consolidar y descargar.
- Entry point estable:
  - `uvicorn api.main:app --host 0.0.0.0 --port 8010`
- Base URL local:
  - `http://localhost:8010`

Notas importantes:
- El storage de `batch_id` y `download_id` es en memoria (`api/storage.py`): si reinicias API, se pierden IDs previos.
- `POST /api/batch/process` usa `multipart/form-data` y `payload` es **STRING JSON**.
- En `batch/process`, cuando no se usa un perfil valido, el mapping obligatorio va en `mappingValues`.
- Si envias `profile_mapping` (en lugar de `mappingValues`) o mapping vacio, responde `400 Missing required mapping`.
- OpenAPI actual expone `authorization` como **query param opcional** en casi todos los endpoints (excepto `/api/health`).

## B) Tabla de endpoints (resumen)

| Metodo + Path | Proposito | Content-Type request | Auth | Output keys principales |
|---|---|---|---|---|
| `GET /api/health` | Health check | N/A | No | `status` |
| `GET /api/profiles` | Lista catalogo de perfiles | N/A | Opcional (`authorization` query) | `profiles[]` |
| `GET /api/me` | Usuario autenticado actual | N/A | Opcional (`authorization` query) | `user` |
| `POST /api/batch/analyze` | Detectar perfil/mapping sugerido | `multipart/form-data` (`files[]`) | Opcional (`authorization` query) | `auto_profile_id`, `profile_mapping`, `profile_settings`, `metadata` |
| `POST /api/batch/process` | Procesar lotes de Excel | `multipart/form-data` (`files[]`, `payload` string JSON) | Opcional (`authorization` query) | `batch_id`, `results[]`, `is_baninter`, `default_client_name`, `auto_area` |
| `POST /api/batch/consolidate` | Consolidar batch ya procesado | `application/json` | Opcional (`authorization` query) | `download_id`, `filename`, `consultores`, `total_horas`, `warnings[]` |
| `POST /api/batch/baninter-zip` | ZIP con individuales BANINTER | `application/json` | Opcional (`authorization` query) | `download_id`, `filename` |
| `POST /api/individual/analyze` | Analizar archivo multihja | `multipart/form-data` (`file`) | Opcional (`authorization` query) | `sheets[]`, `auto_profile_id`, `is_nova`, `auto_area`, `employee_count` |
| `POST /api/individual/process` | Procesar multihja + consolidado | `multipart/form-data` (`file`, `payload` string JSON) | Opcional (`authorization` query) | `batch_id`, `results[]`, `consolidated`, `baninter_zip`, `skipped_sheets[]` |
| `GET /api/download/{file_id}` | Descargar artefacto generado | N/A | Opcional (`authorization` query) | bytes archivo (stream) |

## C) Detalle endpoint por endpoint

### 1) `GET /api/health`

1. Metodo y ruta:
- `GET /api/health`

2. Que hace:
- Verifica que API responde.

3. Request:
- Query/path: ninguno.
- Body: no aplica.
- Content-Type: no aplica.
- Ejemplo:
```bash
curl.exe "http://localhost:8010/api/health"
```

4. Response:
- `200`:
```json
{ "status": "ok" }
```

5. Errores comunes:
- Si no responde, API no esta levantada o puerto incorrecto.

### 2) `GET /api/profiles`

1. Metodo y ruta:
- `GET /api/profiles`

2. Que hace:
- Retorna catalogo de perfiles (mapping/settings/keywords/aliases).

3. Request:
- Query opcional: `authorization` (string, formato esperado: `Bearer <token>`).
- Body: no aplica.
- Content-Type: no aplica.
- Ejemplo:
```bash
curl.exe "http://localhost:8010/api/profiles"
```

4. Response:
- `200`:
```json
{
  "profiles": [
    {
      "client_id": "cliente_bit",
      "name": "BIT Nova",
      "mapping": { "date": "Fecha", "hours": "Horas", "description": "Descripcion", "project": "Proyecto" },
      "settings": { "correct_spelling": true },
      "keywords": ["nova", "bit"],
      "company_aliases": ["NOVA", "BIT"]
    }
  ]
}
```
- `422`: validacion FastAPI de parametros.

5. Errores comunes:
- Con auth habilitada y token invalido: `401`/`403`.

### 3) `GET /api/me`

1. Metodo y ruta:
- `GET /api/me`

2. Que hace:
- Devuelve usuario autenticado o `null`.

3. Request:
- Query opcional: `authorization`.
- Body: no aplica.
- Content-Type: no aplica.
- Ejemplo:
```bash
curl.exe "http://localhost:8010/api/me"
```

4. Response:
- `200`:
```json
{ "user": null }
```

5. Errores comunes:
- Con auth habilitada y token ausente/invalido: `401`.

### 4) `POST /api/batch/analyze`

1. Metodo y ruta:
- `POST /api/batch/analyze`

2. Que hace:
- Analiza 1er archivo del lote para auto-detectar perfil y mapping sugerido.

3. Request:
- Query opcional: `authorization`.
- Body (`multipart/form-data`):
  - `files` (array de archivos, requerido por OpenAPI)
- Ejemplo:
```bash
curl.exe -X POST "http://localhost:8010/api/batch/analyze" \
  -F "files=@C:/fixtures/reporte.xlsx"
```

4. Response:
- `200`:
```json
{
  "auto_profile_id": "cliente_bit",
  "profile_mapping": { "date": "Fecha", "hours": "Horas", "description": "Descripcion", "project": "Proyecto" },
  "profile_settings": { "correct_spelling": true },
  "metadata": { "company": "NOVA", "employee": "Juan", "month_name": "Enero", "year": 2026 }
}
```
- `400`: `No files provided`.
- `422`: falta campo `files` o form invalido.

5. Errores comunes:
- Enviar `file` en vez de `files`.

### 5) `POST /api/batch/process`

1. Metodo y ruta:
- `POST /api/batch/process`

2. Que hace:
- Procesa todos los archivos del lote, ejecuta pipeline, genera reportes individuales y devuelve `batch_id`.

3. Request:
- Query opcional: `authorization`.
- Body (`multipart/form-data`):
  - `files` (array archivos, requerido)
  - `payload` (string JSON, opcional en OpenAPI pero necesario para varios casos)
- `payload` esperado (campos):
  - `profileId`: string o `null`
  - `mappingValues`: objeto mapping (`date`, `hours`, `description`, `project`) cuando no hay perfil utilizable
  - `settings`: objeto opcional
  - `maxWorkers`: entero opcional

Ejemplo minimo (sin profile):
```json
{
  "profileId": null,
  "mappingValues": {
    "date": "Fecha",
    "hours": "Horas",
    "description": "Descripcion",
    "project": "Proyecto"
  }
}
```

Ejemplo completo:
```json
{
  "profileId": "cliente_bit",
  "mappingValues": {
    "date": "Fecha",
    "hours": "Horas",
    "description": "Descripcion",
    "project": "Proyecto"
  },
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

Ejemplo request:
```bash
curl.exe -X POST "http://localhost:8010/api/batch/process" \
  -F "files=@C:/fixtures/reporte.xlsx" \
  -F "payload={\"profileId\":null,\"mappingValues\":{\"date\":\"Fecha\",\"hours\":\"Horas\",\"description\":\"Descripcion\",\"project\":\"Proyecto\"},\"settings\":{\"correctSpelling\":true},\"maxWorkers\":4}"
```

4. Response:
- `200` (keys principales):
```json
{
  "batch_id": "f2e7...",
  "results": [
    {
      "file_name": "reporte.xlsx",
      "sheet_name": "Hoja1",
      "success": true,
      "client_id": "cliente_bit",
      "metadata": { "employee": "Juan" },
      "summary": {
        "quality_score": 92.5,
        "errores_criticos": 1,
        "errores_advertencia": 2
      },
      "errors": [],
      "download_id": "8af1...",
      "output_filename": "reporte_CORREGIDO.xlsx"
    }
  ],
  "is_baninter": false,
  "default_client_name": "NOVA - TI",
  "auto_area": "TI"
}
```
- `400`: `Missing required mapping`, `Invalid JSON payload: ...`, `Profile missing required mapping`.
- `422`: falta `files`.

5. Errores comunes y solucion:
- `400 Missing required mapping`:
  - Causa: `profileId` nulo/invalido y sin `mappingValues` util.
  - Solucion: enviar `mappingValues.date`, `mappingValues.hours`, `mappingValues.description`.
- `400 Invalid JSON payload`:
  - Causa: `payload` no parsea como JSON.
  - Solucion: enviar `payload` como string JSON valido.

### 6) `POST /api/batch/consolidate`

1. Metodo y ruta:
- `POST /api/batch/consolidate`

2. Que hace:
- Genera consolidado Excel desde un `batch_id` previamente procesado.

3. Request:
- Query opcional: `authorization`.
- Body (`application/json`):
  - `batchId` (requerido)
  - `clientName` (opcional)
  - `outputFilename` (opcional)
- Ejemplo:
```json
{
  "batchId": "f2e7...",
  "clientName": "NOVA - TI",
  "outputFilename": "Consolidado_Enero_2026.xlsx"
}
```

4. Response:
- `200`:
```json
{
  "download_id": "a9c1...",
  "filename": "Consolidado_Enero_2026.xlsx",
  "consultores": 3,
  "total_horas": 504.0,
  "warnings": []
}
```
- `400`: `batchId required`, `Batch results not valid for consolidation`.
- `404`: `Batch not found`.
- `422`: body invalido.

5. Errores comunes:
- Enviar `batch_id` en vez de `batchId`.

### 7) `POST /api/batch/baninter-zip`

1. Metodo y ruta:
- `POST /api/batch/baninter-zip`

2. Que hace:
- Genera ZIP con reportes individuales en formato BANINTER.

3. Request:
- Query opcional: `authorization`.
- Body (`application/json`):
```json
{ "batchId": "f2e7..." }
```

4. Response:
- `200`:
```json
{
  "download_id": "z91d...",
  "filename": "BANINTER_Individuales_BusinessIT.zip"
}
```
- `400`: `batchId required` o `No BANINTER results available`.
- `404`: `Batch not found`.
- `422`: body invalido.

5. Errores comunes:
- Intentar generar ZIP en lote sin resultados BANINTER.

### 8) `POST /api/individual/analyze`

1. Metodo y ruta:
- `POST /api/individual/analyze`

2. Que hace:
- Analiza archivo multihja, detecta hojas validas, perfil y area sugerida.

3. Request:
- Query opcional: `authorization`.
- Body (`multipart/form-data`):
  - `file` (archivo unico)
- Ejemplo:
```bash
curl.exe -X POST "http://localhost:8010/api/individual/analyze" \
  -F "file=@C:/fixtures/multihoja.xlsx"
```

4. Response:
- `200`:
```json
{
  "sheets": [
    {
      "sheet_name": "Juan",
      "metadata": { "employee": "Juan", "company": "NOVA" },
      "columns": ["Fecha", "Horas", "Descripcion"],
      "row_count": 42,
      "header_row": 5
    }
  ],
  "skipped_sheets": ["Hoja1"],
  "auto_profile_id": "cliente_bit",
  "is_nova": true,
  "auto_area": "TI",
  "company": "NOVA",
  "employee_count": 1
}
```
- `422`: falta `file`.

5. Errores comunes:
- Enviar campo `files` en vez de `file`.

### 9) `POST /api/individual/process`

1. Metodo y ruta:
- `POST /api/individual/process`

2. Que hace:
- Procesa multihja, genera resultados por colaborador y consolidado.

3. Request:
- Query opcional: `authorization`.
- Body (`multipart/form-data`):
  - `file` (archivo unico, requerido)
  - `payload` (string JSON, opcional)
- `payload` tipico:
```json
{
  "profileId": "cliente_bit",
  "areaSelection": "NOVA - TI (BIT Nova)",
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

4. Response:
- `200` (keys principales):
```json
{
  "batch_id": "9ab2...",
  "results": [
    {
      "file_name": "Juan.xlsx",
      "success": true,
      "summary": { "quality_score": 90.0 }
    }
  ],
  "skipped_sheets": [
    { "name": "Hoja1", "columns": ["A", "B"] }
  ],
  "consolidated": {
    "download_id": "d44f...",
    "filename": "Consolidado_NOVA_-_TI_2_Consultores.xlsx",
    "consultores": 2,
    "total_horas": 320.0
  },
  "baninter_zip": null
}
```
- `400`: `No valid sheets detected` o `No valid timesheet sheets detected`.
- `422`: falta `file` o form invalido.

5. Errores comunes:
- `payload` no JSON valido.
- Hojas sin metadata/empleado quedan en `skipped_sheets`.

### 10) `GET /api/download/{file_id}`

1. Metodo y ruta:
- `GET /api/download/{file_id}`

2. Que hace:
- Descarga bytes de un archivo generado (individual/consolidado/zip).

3. Request:
- Path requerido: `file_id`.
- Query opcional: `authorization`.
- Ejemplo:
```bash
curl.exe -L "http://localhost:8010/api/download/8af1..." -o salida.xlsx
```

4. Response:
- `200`: bytes archivo, con header `Content-Disposition`.
- `404`: `File not found`.
- `422`: `file_id` invalido.

5. Errores comunes:
- Reutilizar `download_id` viejo tras reiniciar API (store en memoria).

## D) Flujos E2E (paso a paso)

### 1) Flujo Batch

1. `POST /api/batch/analyze`
- Subir 1 Excel en `files`.
- Guardar: `auto_profile_id`, `profile_mapping`.

2. `POST /api/batch/process`
- Subir el/los Excel en `files`.
- Enviar `payload` string JSON con:
```json
{
  "profileId": "<auto_profile_id o null>",
  "mappingValues": {
    "date": "<col fecha>",
    "hours": "<col horas>",
    "description": "<col descripcion>",
    "project": "<col proyecto opcional>"
  }
}
```
- Guardar `batch_id` y `results[*].download_id`.

3. `POST /api/batch/consolidate`
- Enviar JSON con `batchId` (camelCase).
- Guardar `download_id` del consolidado.

4. `GET /api/download/{file_id}`
- Descargar usando `download_id` recibido.

### 2) Flujo Individual

1. `POST /api/individual/analyze`
- Subir `file` (multihja).
- Revisar `auto_profile_id`, `sheets`, `auto_area`.

2. `POST /api/individual/process`
- Subir mismo `file`.
- Enviar `payload` string JSON con `profileId`/`settings`.
- Obtener `results[]` y `consolidated.download_id`.

3. `GET /api/download/{file_id}`
- Descargar consolidado con `consolidated.download_id`.

## E) Ejemplos listos para copiar

### 1) curl (Windows)

`batch/analyze`:
```bash
curl.exe -X POST "http://localhost:8010/api/batch/analyze" -F "files=@C:/fixtures/reporte.xlsx"
```

`batch/process` (FormData + payload string JSON):
```bash
curl.exe -X POST "http://localhost:8010/api/batch/process" \
  -F "files=@C:/fixtures/reporte.xlsx" \
  -F "payload={\"profileId\":null,\"mappingValues\":{\"date\":\"Fecha\",\"hours\":\"Horas\",\"description\":\"Descripcion\",\"project\":\"Proyecto\"},\"settings\":{\"correctSpelling\":true},\"maxWorkers\":4}"
```

`batch/consolidate`:
```bash
curl.exe -X POST "http://localhost:8010/api/batch/consolidate" \
  -H "Content-Type: application/json" \
  -d '{"batchId":"<BATCH_ID>"}'
```

`download`:
```bash
curl.exe -L "http://localhost:8010/api/download/<DOWNLOAD_ID>" -o Consolidado.xlsx
```

### 2) React (snippets)

`batch/process` con `fetch` + FormData:
```ts
const baseUrl = "http://localhost:8010";

const payload = {
  profileId: autoProfileId ?? null,
  mappingValues: profileMapping, // <- obligatorio si profileId no resuelve
  settings: {
    correctSpelling: true,
    duplicateSimilarityThreshold: 90,
    duplicateMinOccurrences: 3,
    hoursToleranceFactor: 1.5,
    role: "Consultor",
  },
  maxWorkers: 4,
};

const form = new FormData();
selectedFiles.forEach((f) => form.append("files", f));
form.append("payload", JSON.stringify(payload));

const qs = token ? `?authorization=${encodeURIComponent(`Bearer ${token}`)}` : "";
const res = await fetch(`${baseUrl}/api/batch/process${qs}`, {
  method: "POST",
  body: form,
});

if (!res.ok) throw new Error(await res.text());
const data = await res.json();
console.log(data.batch_id, data.results);
```

`batch/process` con `axios`:
```ts
const form = new FormData();
files.forEach((f) => form.append("files", f));
form.append("payload", JSON.stringify(payload));

const qs = token ? `?authorization=${encodeURIComponent(`Bearer ${token}`)}` : "";
const { data } = await axios.post(`${baseUrl}/api/batch/process${qs}`, form, {
  headers: { "Content-Type": "multipart/form-data" },
});
```

Descarga con blob desde `/api/download/{file_id}`:
```ts
const qs = token ? `?authorization=${encodeURIComponent(`Bearer ${token}`)}` : "";
const r = await fetch(`${baseUrl}/api/download/${downloadId}${qs}`);
if (!r.ok) throw new Error(await r.text());

const blob = await r.blob();
const contentDisposition = r.headers.get("Content-Disposition") || "";
const match = /filename=([^;]+)/i.exec(contentDisposition);
const filename = match ? match[1].replace(/"/g, "") : "reporte.xlsx";

const url = URL.createObjectURL(blob);
const a = document.createElement("a");
a.href = url;
a.download = filename;
a.click();
URL.revokeObjectURL(url);
```

## F) Contrato clave de `/api/batch/process` (destacado)

- Content-Type: `multipart/form-data`
- Campo de archivos: `files` (array)
- Campo payload: `payload` (STRING JSON)
- Mapping requerido: `mappingValues`

Reglas practicas:
- Si `profileId` es `null` o no resuelve a perfil valido, debes enviar `mappingValues` con al menos:
  - `date`
  - `hours`
  - `description`
- Si envias `profile_mapping` en lugar de `mappingValues`, o `{}` vacio, devuelve:
  - `400 Missing required mapping`

Ejemplo minimo valido:
```json
{
  "profileId": null,
  "mappingValues": {
    "date": "Fecha",
    "hours": "Horas",
    "description": "Descripcion"
  }
}
```

Ejemplo completo valido:
```json
{
  "profileId": "cliente_bit",
  "mappingValues": {
    "date": "Fecha",
    "hours": "Horas",
    "description": "Descripcion",
    "project": "Proyecto"
  },
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
