from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from backend.excel_parser import load_sheet_with_header, infer_column_mapping
from backend.detectors import auto_detect_profile
from backend.infrastructure.config.client_profile_repository import get_client_profile_repository
from backend.infrastructure.composition.processing_factory import build_timesheet_processor


def _resolve_mapping(parsed, profile_manager):
    metadata = parsed.metadata or {}
    profiles = list(profile_manager.list_profiles())
    auto_profile_id = auto_detect_profile("benchmark.xlsx", metadata, profiles)
    profile_mapping = {}
    if auto_profile_id:
        detected = next((p for p in profiles if p.client_id == auto_profile_id), None)
        if detected:
            profile_mapping = detected.mapping or {}
    mapping = infer_column_mapping(parsed.dataframe, profile_mapping)
    if mapping is None:
        raise ValueError("No se pudo inferir mapeo para benchmark.")
    return mapping, auto_profile_id


def process_file(path: Path) -> None:
    processor = build_timesheet_processor()
    profile_manager = get_client_profile_repository().load_manager()

    file_bytes = path.read_bytes()
    parsed = load_sheet_with_header(file_bytes)
    mapping, auto_profile_id = _resolve_mapping(parsed, profile_manager)

    start = time.perf_counter()
    processor.process_parsed_sheet(
        parsed_sheet=parsed,
        mapping=mapping,
        source_name=path.name,
        correct_spelling=False,
        upload_to_blob=False,
        role="Consultor",
        project_name=mapping.project or "No especificado",
        duplicate_similarity_threshold=90,
        duplicate_min_occurrences=3,
        hours_tolerance_factor=1.5,
        client_profile_id=auto_profile_id,
        client_profile_settings={},
        batch_fast_mode=True,
        enable_debug_exports=False,
    )
    total = time.perf_counter() - start
    print(f"TOTAL {path.name}: {total:.2f}s")


def main() -> int:
    logging.basicConfig(level=logging.INFO)

    args = [Path(p) for p in sys.argv[1:]]
    if not args:
        args = [
            Path("FileReference/NOVA/CD/Reporte_Horas_Galo_Robayo_Septiembre_2025.xlsx"),
            Path("FileReference/NOVA/CD/Actividades_Victor_Jaramillo_septiembre_2025_01.xlsx"),
        ]

    for path in args:
        if not path.exists():
            print(f"Archivo no encontrado: {path}")
            continue
        process_file(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
