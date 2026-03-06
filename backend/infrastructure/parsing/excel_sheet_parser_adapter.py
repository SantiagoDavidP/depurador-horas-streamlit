from __future__ import annotations

from typing import List, Optional

from backend.application.parsing.models import ParsedSheet
from backend.application.ports.sheet_parser_port import SheetParserPort
from backend.infrastructure.parsing.excel_sheet_parser import load_sheet_with_header


class ExcelSheetParserAdapter(SheetParserPort):
    def load_sheet_with_header(
        self,
        excel_bytes: bytes,
        *,
        sheet_name: Optional[str] = None,
        header_row: Optional[int] = None,
        header_keywords: Optional[List[str]] = None,
        auto_correct_period: bool = True,
    ) -> ParsedSheet:
        return load_sheet_with_header(
            excel_bytes,
            sheet_name=sheet_name,
            header_row=header_row,
            header_keywords=header_keywords,
            auto_correct_period=auto_correct_period,
        )
