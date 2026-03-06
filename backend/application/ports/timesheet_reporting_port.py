from __future__ import annotations

from typing import Dict, List, Optional, Protocol, Tuple

from backend.application.consolidation.models import ConsolidatedReport
from backend.application.ports.collaborator_rates_port import CollaboratorRatesPort
from backend.application.tabular.table_data import TableData


class TimesheetReportingPort(Protocol):
    def generate_consolidated_report(
        self,
        *,
        cliente: str,
        consultores_data: List[Tuple[TableData, Dict[str, object]]],
        output_filename: Optional[str] = None,
        collaborator_rates: Optional[CollaboratorRatesPort] = None,
    ) -> ConsolidatedReport:
        ...

    def generate_single_consultant_report(
        self,
        *,
        cliente: str,
        dataframe: TableData,
        metadata: Dict[str, object],
        output_filename: Optional[str] = None,
        collaborator_rates: Optional[CollaboratorRatesPort] = None,
    ) -> bytes:
        ...
