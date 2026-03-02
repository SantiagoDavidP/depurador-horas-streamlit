from __future__ import annotations

from typing import Dict, Optional

from fastapi import Depends, HTTPException
from fastapi.responses import Response

from api.presentation.dependencies import auth_provider, file_store


def download(file_id: str, user: Optional[Dict[str, object]] = Depends(auth_provider.require_user)) -> Response:
    stored = file_store.get_file(file_id)
    if not stored:
        raise HTTPException(status_code=404, detail="File not found")
    headers = {"Content-Disposition": f"attachment; filename={stored.filename}"}
    return Response(content=stored.data, media_type=stored.content_type, headers=headers)


__all__ = ["download"]
