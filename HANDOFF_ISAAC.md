# HANDOFF ISAAC

## Overview
- Sistema para depurar timesheets en Excel, aplicar validaciones de calidad y generar reportes individuales + consolidados.
- Soporta dos experiencias de usuario:
  - `frontend/app.py` (Streamlit, ejecución directa del backend).
  - `react-frontend` (React/Vite, consume FastAPI).
- El núcleo de negocio vive en `backend/` y la exposición API en `api/`.

## Arquitectura
- `api/`:
  - `main.py`: endpoints de análisis/proceso/consolidación/descarga.
  - `auth.py`: autenticación vía Azure AD (bearer token + Microsoft Graph).
  - `services.py`: detección de perfil/cliente/mapeo.
  - `serializers.py`: serialización segura + orden de errores.
  - `storage.py`: almacenamiento en memoria de archivos/batches (no persistente).
- `backend/`:
  - `excel_parser.py`: parseo robusto de Excel y metadata.
  - `processor.py`: orquestador de validaciones, correcciones y export individual.
  - `validators.py`: reglas de formato, negocio, deduplicación y completitud.
  - `batch_processor.py`: paralelismo para lotes.
  - `consolidator.py`: generación de consolidado y hojas individuales.
  - `consolidator_integration.py`: puente Batch -> Consolidado.
  - `llm_corrector.py`, `role_validator.py`: IA de corrección y coherencia rol-actividad.
- `config/`:
  - `settings.py`: entorno/config Azure.
  - `client_profiles.json`, `collaborator_rates.json`, `role_taxonomy.json`.
- `frontend/` y `react-frontend/`: capas UI.

## Flujo E2E
1. Carga de archivo(s) Excel desde Streamlit o React.
2. Detección de perfil de cliente + mapping de columnas.
3. Parseo de hoja(s): header row, metadata, limpieza de ruido.
4. Validaciones:
  - Calendario/fechas/feriados/fines de semana.
  - Horas diarias y razonabilidad por tarea.
  - Calidad de descripción, tickets, campos vacíos.
  - Duplicados exactos/similares y repetición por días.
  - Reglas por perfil cliente.
5. Correcciones:
  - Correcciones seguras en dataframe.
  - LLM opcional en descripciones.
6. Salidas:
  - Excel individual depurado por consultor.
  - Consolidado Excel (resumen + hojas por consultor).
  - Descarga vía UI/API (`/api/download/{file_id}`).

## Componentes core
- `backend/processor.py` (`TimeSheetProcessor.process_parsed_sheet`): pipeline principal.
- `backend/validators.py` (`run_all_validations`): todas las validaciones de calidad.
- `backend/batch_processor.py` (`BatchProcessor.process_batch`): ejecución paralela por archivo.
- `backend/consolidator.py` (`TimeSheetConsolidator.generate_consolidated_report`): consolidado final.
- `backend/consolidator_integration.py` (`generate_consolidated_from_batch_results`): integración de resultados batch.
- `api/main.py`: endpoints de proceso individual, batch y consolidación.

## Reportes
- **Individual depurado**:
  - Generado en `processor._export_workbook`.
  - Hojas: `Resumen Ejecutivo`, `Datos Corregidos`, `Reporte de Errores` (+ debug opcional).
- **Consolidado**:
  - Generado en `consolidator.generate_consolidated_report`.
  - Hoja `Resumen` + hojas por consultor.
- **Formato BANINTER/Business IT**:
  - Generado por `generate_individual_business_it_excel` -> `generate_single_consultant_report`.
  - Puede descargarse individual o en ZIP (`/api/batch/baninter-zip`).

## Validaciones/IA
- Validaciones de formato:
  - `validate_mapping`, `validate_calendar_constraints`, `validate_daily_hours`, `validate_ticket_format`, `validate_missing_fields`.
- Reglas de negocio:
  - `validate_working_days_completeness`, `validate_reasonable_hours_per_task`, `validate_project_consistency`, validaciones por perfil (`profile_validations.py`).
- Deduplicación/coherencia:
  - `detect_copy_paste_patterns`, `validate_duplicate_entries`, `RoleActivityValidator`.
- IA:
  - `LLMCorrector` corrige descripciones con prompts estructurados, batching, timeout y fallback.
  - `ai_insights.py` existe para resumen ejecutivo IA, pero está desactivado en el pipeline actual.
- Scoring:
  - En `processor._create_summary`, genera `quality_score`, `errores_criticos`, `errores_advertencia`.

## Cómo correr local
### Backend + Streamlit
1. Crear venv e instalar deps:
   - `python -m venv .venv`
   - `.\.venv\Scripts\activate`
   - `pip install -r requirements.txt`
2. Configurar variables:
   - Copiar `.env.example` a `.env` y completar credenciales necesarias.
3. Ejecutar Streamlit:
   - `streamlit run frontend/app.py`

### API FastAPI
1. Mismo entorno Python y `.env`.
2. Ejecutar API:
   - `uvicorn api.main:app --reload --host 0.0.0.0 --port 8000`

### React frontend
1. Ir a `react-frontend`.
2. Instalar deps: `npm install`
3. Configurar env: copiar `.env.example` a `.env`
4. Ejecutar: `npm run dev`

## Cómo desplegar
- Dockerfile actual levanta Streamlit por defecto (`frontend/app.py`).
- Para producción recomendada:
  1. Separar API y frontend en servicios distintos.
  2. API con Uvicorn/Gunicorn, workers, storage persistente.
  3. Frontend React como estático (Nginx/CDN) apuntando a API.
  4. Configurar secretos en plataforma (no en repo).
  5. Añadir observabilidad (logs estructurados, métricas, alertas).

## Pendientes
- Definir frontend oficial de producción (React vs Streamlit).
- Persistencia durable para batches/descargas (hoy en memoria de proceso).
- Activar/descartar formalmente `ai_insights`.
- Unificar y parametrizar reglas por cliente para evitar hardcode distribuido.
- Endurecer seguridad API (CORS, auth obligatoria, rate limit, RBAC).
- Completar estrategia asíncrona para lotes grandes (job queue + estados).

## Riesgos
- Pérdida de artefactos tras reinicio de API (`api/storage.py`).
- Duplicación funcional entre Streamlit y React/API (mantenimiento doble).
- Módulos muy grandes (`api/main.py`, `backend/processor.py`, `backend/consolidator.py`) elevan riesgo de regresión.
- Dependencia de formato Excel variable por cliente/plantilla (fragilidad de parseo).
- Dependencia de configuración Azure/LLM para funciones avanzadas.

## Próximos pasos
1. Estabilizar contrato API v1 y consolidar React como frontend principal.
2. Introducir almacenamiento persistente para resultados y descargas.
3. Implementar procesamiento asíncrono con cola para cargas pesadas.
4. Refactor por dominios (parse, validation, scoring, reporting, client rules).
5. Agregar pruebas E2E de contrato y datasets reales por cliente.
6. Endurecer seguridad y observabilidad para operación productiva.
