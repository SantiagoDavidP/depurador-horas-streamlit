# Import Migration Guide

Guia de migracion de imports despues del refactor a Clean Architecture.
Alcance: solo `backend/**` y `api/**`.

## 1) Old import -> New import

| Old import | New import | Simbolo principal |
|---|---|---|
| `backend.models` | `backend.domain.models` | `ColumnMapping` |
| `backend.client_profiles` | `backend.domain.profiles.client_profiles` | `ClientProfile`, `ClientProfileManager` |
| `backend.collaborator_rates` | `backend.domain.rates.collaborator_rates` | `get_collaborator_rates_manager` |
| `backend.holiday_detector` | `backend.domain.calendar.holiday_detector` | `HolidayDetector` |
| `backend.role_validator` | `backend.domain.roles.role_validator` | `RoleActivityValidator` |
| `backend.detectors` | `backend.domain.profiles.detectors` | `auto_detect_profile`, `resolve_employee` |
| `backend.validators` | `backend.domain.validation.validators` | `run_all_validations`, `ValidationIssue` |
| `backend.excel_parser` | `backend.domain.parsing.excel_parser` | `load_sheet_with_header`, `load_multiple_sheets`, `infer_column_mapping`, `ParsedSheet` |
| `backend.profile_validations` | `backend.domain.profiles.profile_validations` | `run_profile_validations` |
| `backend.batch_processor` | `backend.application.batch.batch_processor` | `BatchProcessor`, `BatchFileRequest`, `BatchFileResult` |
| `backend.consolidator_integration` | `backend.application.consolidation.consolidator_integration` | `generate_consolidated_from_batch_results`, `generate_individual_business_it_excel` |
| `backend.data_cleaner` | `backend.application.processing.data_cleaner` | `detect_and_remove_metadata_rows` |
| `backend.baninter_processor` | `backend.application.processing.baninter_processor` | `prepare_baninter_dataframe` |
| `backend.processor` | `backend.application.processing.service` | `TimeSheetProcessor` |
| `backend.consolidator` | `backend.application.consolidation.service` | `TimeSheetConsolidator` |
| `backend.perf` | `backend.infrastructure.observability.perf` | `PerfCollector`, `time_block` |
| `backend.health` | `backend.infrastructure.health.health` | `HealthChecker`, `get_health_checker` |
| `backend.ai_insights` | `backend.infrastructure.ai.ai_insights` | `generate_ai_summary`, `generate_ai_summary_sync` |
| `backend.azure_ad_auth` | `backend.infrastructure.auth.azure_ad_auth` | `AzureADAuthenticator`, `require_authentication` |
| `backend.azure_storage` | `backend.infrastructure.storage.azure_storage` | `upload_bytes_to_blob`, `download_blob_to_bytes` |
| `backend.llm_corrector` | `backend.infrastructure.ai.llm_corrector` | `LLMCorrector`, `CorrectionResult` |
| `backend.llm_cache` | `backend.infrastructure.ai.llm_cache` | `SimpleLLMCache`, `get_llm_cache` |
| `api.main` | `api.main` (estable; reexporta) | `app` |

Nota: hoy `backend/` root ya no expone esos modulos legacy (excepto `backend/__init__.py`).

## 2) Before/after examples

```python
# Before
from backend.processor import TimeSheetProcessor
from backend.batch_processor import BatchProcessor
from backend.excel_parser import load_sheet_with_header

# After
from backend.application.processing.service import TimeSheetProcessor
from backend.application.batch.batch_processor import BatchProcessor
from backend.domain.parsing.excel_parser import load_sheet_with_header
```

```python
# Before
from backend.consolidator_integration import generate_consolidated_from_batch_results
from backend.llm_corrector import LLMCorrector

# After
from backend.application.consolidation.consolidator_integration import generate_consolidated_from_batch_results
from backend.infrastructure.ai.llm_corrector import LLMCorrector
```

## 3) Donde esta cada cosa ahora (cheat sheet)

### Domain
- Parseo Excel: `backend/domain/parsing/excel_parser.py` -> `load_sheet_with_header`, `load_multiple_sheets`, `infer_column_mapping`.
- Validaciones generales: `backend/domain/validation/validators.py` -> `run_all_validations`.
- Validaciones por perfil: `backend/domain/profiles/profile_validations.py` -> `run_profile_validations`.
- Perfil/cliente: `backend/domain/profiles/client_profiles.py` -> `ClientProfileManager`.
- Deteccion de perfil: `backend/domain/profiles/detectors.py` -> `auto_detect_profile`.
- Calendario/feriados: `backend/domain/calendar/holiday_detector.py` -> `HolidayDetector`.
- Roles: `backend/domain/roles/role_validator.py` -> `RoleActivityValidator`.
- Modelos de dominio: `backend/domain/models.py` -> `ColumnMapping`.
- Tarifas: `backend/domain/rates/collaborator_rates.py` -> `get_collaborator_rates_manager`.

### Application
- Proceso individual/orquestacion: `backend/application/processing/service.py` -> `TimeSheetProcessor.process_parsed_sheet`.
- Pipeline interno: `backend/application/processing/pipeline.py` -> `process_parsed_sheet_impl`.
- Summary/scoring: `backend/application/processing/summary.py` -> `_create_summary`.
- Export Excel individual: `backend/application/processing/excel_export.py` -> `_export_workbook`.
- Batch: `backend/application/batch/batch_processor.py` -> `BatchProcessor.process_batch`.
- Consolidacion: `backend/application/consolidation/service.py` -> `TimeSheetConsolidator`.
- Integracion batch->consolidado: `backend/application/consolidation/consolidator_integration.py`.

### Infrastructure
- Auth Azure AD (backend): `backend/infrastructure/auth/azure_ad_auth.py`.
- Blob storage: `backend/infrastructure/storage/azure_storage.py` + adapter `azure_blob_storage_adapter.py`.
- LLM: `backend/infrastructure/ai/llm_corrector.py` + `llm_cache.py` + `llm_corrector_adapter.py`.
- Health: `backend/infrastructure/health/health.py`.
- Observabilidad/perf: `backend/infrastructure/observability/perf.py`.

### API (Presentation + adapters)
- App FastAPI: `api/presentation/app.py`.
- Rutas: `api/presentation/routes/*.py`.
- Handlers: `api/presentation/handlers_*.py`.
- Parsing de payload/form: `api/presentation/parsing.py`.
- Dependencias: `api/presentation/dependencies.py`.
- Auth adapter API: `api/infrastructure/auth/azure_ad_user_auth_adapter.py` (delegacion a `api/auth.py`).
- File store adapter API: `api/infrastructure/storage/in_memory_file_store_adapter.py` (delegacion a `api/storage.py`).

## 4) Entrypoints estables

- API: `uvicorn api.main:app`
- FastAPI app object: `api.main:app` (reexport de `api.presentation.app`).
- Processor principal: `backend.application.processing.service.TimeSheetProcessor`.
- Consolidator principal: `backend.application.consolidation.service.TimeSheetConsolidator`.
- Batch principal: `backend.application.batch.batch_processor.BatchProcessor`.

## 5) Referencias legacy detectadas (para migrar)

Busqueda estatica (`rg`) encontro imports legacy en:
- `frontend/app.py`
- `frontend/app_consolidado_snippet.py`
- `scripts/benchmark_timings.py`
- `verify_improvements.py`
- `test_consolidador.py`

Tambien hay ejemplos legacy en docs:
- `CONSOLIDADO_README.md`
- `SECURITY_IMPROVEMENTS.md`

Estos archivos deben actualizar imports segun la tabla de esta guia.
