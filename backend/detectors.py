from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from backend.client_profiles import ClientProfile

_INVALID_NAME_TOKENS = {
    "actividades",
    "informe",
    "bit",
    "nova",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
    "proyecto",
    "reporte",
    "timesheet",
    "2024",
    "2025",
    "2026",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _extract_tokens_from_filename(filename: str) -> List[str]:
    stem = Path(filename).stem
    parts = re.split(r"[_\-\s]+", stem)
    camel = re.findall(r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+", stem)
    tokens = parts + camel
    cleaned = []
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        cleaned.append(token)
    return cleaned


def extract_employee_from_filename(filename: str) -> Optional[str]:
    tokens = _extract_tokens_from_filename(filename)
    candidates: List[str] = []
    for idx in range(len(tokens) - 1):
        first = tokens[idx]
        second = tokens[idx + 1]
        if (
            first
            and second
            and first[0].isalpha()
            and second[0].isalpha()
            and first.lower() not in _INVALID_NAME_TOKENS
            and second.lower() not in _INVALID_NAME_TOKENS
        ):
            candidates.append(f"{first} {second}")
    return candidates[0] if candidates else None


def detect_client_from_filename(filename: str, profile: ClientProfile) -> bool:
    normalized = _normalize(Path(filename).stem)
    keywords = profile.keywords or []
    if not keywords:
        return False
    return any(keyword in normalized for keyword in keywords)


def detect_client_from_metadata(metadata: Dict[str, object], profile: ClientProfile) -> bool:
    company = metadata.get("company") or metadata.get("empresa")
    if not company:
        return False
    normalized_company = _normalize(str(company))
    aliases = profile.company_aliases or []
    return any(alias in normalized_company for alias in aliases)


def auto_detect_profile(
    filename: str,
    metadata: Dict[str, object],
    profiles: Sequence[ClientProfile],
) -> Optional[str]:
    for profile in profiles:
        if detect_client_from_filename(filename, profile):
            return profile.client_id
    for profile in profiles:
        if detect_client_from_metadata(metadata, profile):
            return profile.client_id
    return None


def resolve_employee(metadata: Dict[str, object], filename: str) -> Dict[str, Optional[str]]:
    employee_metadata = metadata.get("employee") or metadata.get("empleado")
    employee_from_filename = extract_employee_from_filename(filename)
    return {
        "metadata": employee_metadata,
        "filename": employee_from_filename,
        "final": employee_metadata or employee_from_filename,
    }
