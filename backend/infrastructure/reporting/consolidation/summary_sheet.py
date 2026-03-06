from __future__ import annotations

from ._report_generation import ReportGenerationMixin
from ._summary_sheet_impl import SummarySheetImplMixin


class SummarySheetMixin(ReportGenerationMixin, SummarySheetImplMixin):
    pass


__all__ = ["SummarySheetMixin"]
