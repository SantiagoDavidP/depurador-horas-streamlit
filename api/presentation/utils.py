from __future__ import annotations

from typing import Dict, List, Optional

from backend.batch_processor import BatchFileResult
from backend.consolidator_integration import generate_individual_business_it_excel
from api.services import is_baninter_result


def _build_baninter_zip(batch_results: List[BatchFileResult]) -> Optional[bytes]:
    import zipfile
    from io import BytesIO

    buffer = BytesIO()
    written = 0
    used_names = set()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, res in enumerate(batch_results):
            if not (res.success and res.result):
                continue
            if not is_baninter_result(res.file_name, res.metadata, res.client_id):
                continue
            business_bytes, business_name = generate_individual_business_it_excel(
                res, cliente="BANINTER"
            )
            safe_name = business_name or f"BANINTER_{idx + 1}.xlsx"
            if safe_name in used_names:
                stem, ext = safe_name.rsplit(".", 1) if "." in safe_name else (safe_name, "xlsx")
                safe_name = f"{stem}_{idx + 1}.{ext}"
            used_names.add(safe_name)
            zf.writestr(safe_name, business_bytes)
            written += 1
    if written == 0:
        return None
    buffer.seek(0)
    return buffer.getvalue()

def _infer_client_id_for_file(
    file_name: str,
    metadata: Optional[Dict[str, object]],
    fallback_client_id: Optional[str],
) -> Optional[str]:
    if fallback_client_id == "cliente_talent":
        return fallback_client_id

