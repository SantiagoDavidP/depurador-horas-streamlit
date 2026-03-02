from __future__ import annotations

from typing import Dict, List, Optional, Sequence
import re
import numbers

import pandas as pd
from fuzzywuzzy import fuzz

from backend.validators import ValidationIssue


def _resolve_column(df: pd.DataFrame, candidates: Sequence[str]) -> Optional[str]:
    normalized = {col.lower().strip(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower().strip() in normalized:
            return normalized[candidate.lower().strip()]
    for col in df.columns:
        normalized_name = col.lower().strip()
        for candidate in candidates:
            if candidate.lower().strip() in normalized_name:
                return col
    return None


def validate_bit_nova(
    df: pd.DataFrame,
    metadata: Dict[str, object],
    row_numbers: Optional[Sequence[int]],
) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    tecnico_col = _resolve_column(df, ["técnico", "tecnico"])
    fecha_col = _resolve_column(df, ["fecha", "date"])
    ticket_col = _resolve_column(df, ["ticket"])
    tipo_hora_col = _resolve_column(df, ["tipo hora"])

    # Validar empleado único
    if tecnico_col and not df.empty:
        tecnicos = df[tecnico_col].dropna().astype(str).str.strip()
        unique_tecnicos = tecnicos.unique().tolist()
        if len(unique_tecnicos) > 1:
            issues.append(
                ValidationIssue(
                    fila=row_numbers[0] if row_numbers else 1,
                    fecha="",
                    tipo_error="multiples_empleados",
                    descripcion=f"Se encontraron múltiples técnicos en el archivo: {unique_tecnicos}",
                    valor_original=", ".join(unique_tecnicos),
                    valor_corregido="",
                )
            )
        elif unique_tecnicos:
            metadata_employee = str(metadata.get("employee") or metadata.get("empleado") or "")
            if metadata_employee:
                similarity = fuzz.ratio(metadata_employee.lower(), unique_tecnicos[0].lower())
                if similarity < 80:
                    issues.append(
                        ValidationIssue(
                            fila=row_numbers[0] if row_numbers else 1,
                            fecha="",
                            tipo_error="inconsistencia_empleado",
                            descripcion=(
                                f"El empleado en metadata ('{metadata_employee}') no coincide con el "
                                f"técnico detectado ('{unique_tecnicos[0]}')."
                            ),
                            valor_original=metadata_employee,
                            valor_corregido=unique_tecnicos[0],
                        )
                    )

    # Validar fechas dentro del periodo
    if fecha_col and metadata.get("period_start") and metadata.get("period_end"):
        period_start = pd.to_datetime(metadata["period_start"], errors="coerce")
        period_end = pd.to_datetime(metadata["period_end"], errors="coerce")
        if period_start is not None and period_end is not None:
            parsed_dates = pd.to_datetime(df[fecha_col], errors="coerce")
            out_of_range = df[
                (parsed_dates < period_start) | (parsed_dates > period_end)
            ]
            if not out_of_range.empty:
                for idx in out_of_range.index:
                    row_number = row_numbers[idx] if row_numbers and idx < len(row_numbers) else idx + 2
                    issues.append(
                        ValidationIssue(
                            fila=row_number,
                            fecha=str(df.at[idx, fecha_col]),
                            tipo_error="fecha_fuera_periodo",
                            descripcion="La fecha está fuera del periodo declarado en la metadata.",
                            valor_original=str(df.at[idx, fecha_col]),
                            valor_corregido="",
                        )
                    )

    # Validar tipos de hora
    tipos_validos = metadata.get("tipos_hora_validos")
    if tipo_hora_col and tipos_validos:
        invalid_types = df[~df[tipo_hora_col].isin(tipos_validos)][tipo_hora_col].dropna().unique().tolist()
        if invalid_types:
            issues.append(
                ValidationIssue(
                    fila=row_numbers[0] if row_numbers else 1,
                    fecha="",
                    tipo_error="tipo_hora_invalido",
                    descripcion=f"Tipos de hora no reconocidos: {invalid_types}",
                    valor_original=", ".join(invalid_types),
                    valor_corregido=", ".join(tipos_validos),
                )
            )

    # Validar tickets alfanumericos (sin espacios)
    if ticket_col:
        tickets = df[ticket_col].fillna("")
        for idx, value in tickets.items():
            if pd.isna(value):
                continue
            if isinstance(value, numbers.Real):
                continue
            raw_value = str(value).strip()
            if not raw_value:
                continue
            normalized = "".join(raw_value.split())
            normalized_token = re.sub(r"[^A-Za-z0-9]", "", normalized).upper()
            if not normalized.isalnum():
                row_number = row_numbers[idx] if row_numbers and idx < len(row_numbers) else idx + 2
                issues.append(
                    ValidationIssue(
                        fila=row_number,
                        fecha=str(df.at[idx, fecha_col]) if fecha_col else "",
                        tipo_error="ticket_invalido",
                        descripcion="El ticket debe ser alfanumerico. Evite caracteres especiales.",
                        valor_original=str(df.at[idx, ticket_col]),
                        valor_corregido="",
                    )
                )
    return issues


def run_profile_validations(
    profile_id: Optional[str],
    df: pd.DataFrame,
    metadata: Dict[str, object],
    row_numbers: Optional[Sequence[int]],
    profile_settings: Optional[Dict[str, object]] = None,
) -> List[ValidationIssue]:
    if not profile_id:
        return []
    enriched_metadata = {**metadata}
    if profile_settings:
        enriched_metadata.update(profile_settings)
    if profile_id == "cliente_bit":
        return validate_bit_nova(df, enriched_metadata, row_numbers)
    return []
