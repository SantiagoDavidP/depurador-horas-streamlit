from __future__ import annotations

import logging
import time
from queue import Empty, Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

from backend.excel_parser import ParsedSheet, load_sheet_with_header
from backend.processor import ColumnMapping, ProcessorResult, TimeSheetProcessor

logger = logging.getLogger(__name__)

BatchProgress = Callable[[int, int, str], None]


@dataclass
class BatchFileRequest:
    file_name: str
    file_bytes: bytes
    mapping: ColumnMapping
    client_id: Optional[str] = None
    sheet_name: Optional[str] = None
    header_row: Optional[int] = None
    header_keywords: Optional[List[str]] = None
    profile_settings: Dict[str, object] = field(default_factory=dict)
    processor_kwargs: Dict[str, object] = field(default_factory=dict)
    parsed_sheet: Optional[ParsedSheet] = None


@dataclass
class BatchFileResult:
    file_name: str
    success: bool
    result: Optional[ProcessorResult] = None
    error: Optional[str] = None
    sheet_name: Optional[str] = None
    client_id: Optional[str] = None
    header_row: Optional[int] = None
    metadata: Dict[str, object] = field(default_factory=dict)


class BatchProcessor:
    """Ejecuta el TimeSheetProcessor secuencialmente para varios archivos."""

    def __init__(self, processor: TimeSheetProcessor) -> None:
        self.processor = processor

    def process_batch(
        self,
        files: Sequence[BatchFileRequest],
        *,
        progress_callback: Optional[BatchProgress] = None,
        max_workers: int = 4,
    ) -> List[BatchFileResult]:
        """
        Procesa archivos en paralelo usando ThreadPoolExecutor.
        
        Args:
            files: Archivos a procesar
            progress_callback: Callback para actualizar progreso
            max_workers: Número máximo de threads paralelos (default 4)
        """
        results: List[BatchFileResult] = []
        total = len(files)
        progress_queue: Queue[str] = Queue()
        if progress_callback:
            progress_callback(0, total, "[stage:init] ⏳ Preparando procesamiento...")
        
        # 🟢 PARALLELISM: Usar ThreadPoolExecutor para procesar múltiples archivos simultáneamente
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Mapear futures a file_request para mantener el orden
            future_to_file = {
                executor.submit(
                    self._process_single_file, file_request, progress_queue
                ): (index, file_request)
                for index, file_request in enumerate(files)
            }
            
            pending = set(future_to_file.keys())
            # Procesar completados mientras enviamos actualizaciones de progreso
            while pending:
                try:
                    message = progress_queue.get(timeout=0.2)
                    if progress_callback:
                        progress_callback(len(results), total, message)
                except Empty:
                    pass

                done = {future for future in pending if future.done()}
                for future in done:
                    index, file_request = future_to_file[future]
                    try:
                        result = future.result()
                        results.append((index, result))
                        if progress_callback:
                            progress_callback(len(results), total, f"✅ Procesado {file_request.file_name}")
                    except Exception as exc:
                        logger.exception("Error procesando archivo %s: %s", file_request.file_name, exc)
                        results.append(
                            (index, BatchFileResult(
                                file_name=file_request.file_name,
                                success=False,
                                error=str(exc),
                                sheet_name=file_request.sheet_name,
                                client_id=file_request.client_id,
                            ))
                        )
                        if progress_callback:
                            progress_callback(len(results), total, f"❌ Error en {file_request.file_name}")
                    pending.remove(future)
        
        # Ordenar resultados por índice original para mantener consistencia
        results.sort(key=lambda x: x[0])
        return [result for _, result in results]

    def _process_single_file(
        self,
        file_request: BatchFileRequest,
        progress_queue: Optional[Queue[str]] = None,
    ) -> BatchFileResult:
        """Procesa un archivo individual. Separado para usar con ThreadPoolExecutor."""
        file_start = time.perf_counter()
        parsed_sheet: Optional[ParsedSheet] = None
        
        try:
            if progress_queue:
                progress_queue.put(f"[stage:read] 📄 Leyendo {file_request.file_name}...")
            t0 = time.perf_counter()
            parsed_sheet = file_request.parsed_sheet
            if parsed_sheet is None:
                parsed_sheet = load_sheet_with_header(
                    file_request.file_bytes,
                    sheet_name=file_request.sheet_name,
                    header_row=file_request.header_row,
                    header_keywords=file_request.header_keywords,
                )
            logger.info("⏱️ [%s] Parsed sheet en %.2fs", file_request.file_name, time.perf_counter() - t0)
            
            if progress_queue:
                progress_queue.put(f"[stage:map] 🧭 Mapeando columnas: {file_request.file_name}")
            t1 = time.perf_counter()
            adjusted_mapping = self._align_mapping_with_dataframe(
                parsed_sheet, file_request.mapping
            )
            logger.info("⏱️ [%s] Aligned mapping en %.2fs", file_request.file_name, time.perf_counter() - t1)
            
            if progress_queue:
                progress_queue.put(f"[stage:process] ⚙️ Procesando: {file_request.file_name}")
            t2 = time.perf_counter()
            processor_result = self.processor.process_parsed_sheet(
                parsed_sheet=parsed_sheet,
                mapping=adjusted_mapping,
                source_name=file_request.file_name,
                **file_request.processor_kwargs,
                client_profile_id=file_request.client_id,
                client_profile_settings=file_request.profile_settings,
            )
            logger.info("⏱️ [%s] Processor completed en %.2fs", file_request.file_name, time.perf_counter() - t2)
            logger.info("⏱️ [%s] ARCHIVO TOTAL en %.2fs", file_request.file_name, time.perf_counter() - file_start)
            
            return BatchFileResult(
                file_name=file_request.file_name,
                success=True,
                result=processor_result,
                sheet_name=parsed_sheet.sheet_name,
                client_id=file_request.client_id,
                header_row=parsed_sheet.header_row,
                metadata=getattr(parsed_sheet, "metadata", {}),
            )
        except Exception as exc:
            logger.exception("Error procesando archivo %s: %s", file_request.file_name, exc)
            return BatchFileResult(
                file_name=file_request.file_name,
                success=False,
                error=str(exc),
                sheet_name=parsed_sheet.sheet_name if parsed_sheet else file_request.sheet_name,
                client_id=file_request.client_id,
                header_row=parsed_sheet.header_row if parsed_sheet else file_request.header_row,
                metadata=getattr(parsed_sheet, "metadata", {}),
            )

    def _align_mapping_with_dataframe(
        self, parsed_sheet: ParsedSheet, mapping: ColumnMapping
    ) -> ColumnMapping:
        columns = [str(col) for col in parsed_sheet.dataframe.columns]
        lookup = {col.lower().strip(): col for col in columns}

        def resolve(column_name: Optional[str]) -> Optional[str]:
            if column_name is None:
                return None
            normalized = column_name.lower().strip()
            return lookup.get(normalized, column_name)

        resolved_mapping = ColumnMapping(
            date=resolve(mapping.date),
            hours=resolve(mapping.hours),
            description=resolve(mapping.description),
            project=resolve(mapping.project),
        )
        missing = [
            field
            for field, value in {
                "date": resolved_mapping.date,
                "hours": resolved_mapping.hours,
                "description": resolved_mapping.description,
            }.items()
            if value not in columns
        ]
        if missing:
            raise ValueError(
                f"El archivo {parsed_sheet.sheet_name} no contiene las columnas requeridas: {', '.join(missing)}"
            )
        if resolved_mapping.project and resolved_mapping.project not in columns:
            logger.warning(
                "Columna de proyecto %s no encontrada. Se omitir� para este archivo.",
                resolved_mapping.project,
            )
            resolved_mapping = ColumnMapping(
                date=resolved_mapping.date,
                hours=resolved_mapping.hours,
                description=resolved_mapping.description,
                project=None,
            )
        return resolved_mapping
