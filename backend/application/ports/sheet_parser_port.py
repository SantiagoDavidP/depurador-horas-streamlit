from __future__ import annotations

from typing import List, Optional, Protocol

from backend.application.parsing.models import ParsedSheet


class SheetParserPort(Protocol):
    def load_sheet_with_header(
        self,
        excel_bytes: bytes,
        *,
        sheet_name: Optional[str] = None,
        header_row: Optional[int] = None,
        header_keywords: Optional[List[str]] = None,
        auto_correct_period: bool = True,
    ) -> ParsedSheet:
        ...
