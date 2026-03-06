from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from backend.application.consolidation.models import ConsolidatedReport
from backend.application.ports.collaborator_rates_port import CollaboratorRatesPort
from backend.application.ports.timesheet_reporting_port import TimesheetReportingPort
from backend.application.tabular.table_data import TableData
from backend.infrastructure.reporting.consolidation.service import TimeSheetConsolidator
from backend.shared.tabular.pandas_mapper import to_pandas_table


class ExcelTimesheetReportingAdapter(TimesheetReportingPort):
    def generate_consolidated_report(
        self,
        *,
        cliente: str,
        consultores_data: List[Tuple[TableData, Dict[str, object]]],
        output_filename: Optional[str] = None,
        collaborator_rates: Optional[CollaboratorRatesPort] = None,
    ) -> ConsolidatedReport:
        consolidator = TimeSheetConsolidator(
            cliente=cliente,
            collaborator_rates=collaborator_rates,
        )
        return consolidator.generate_consolidated_report(
            consultores_data=[
                (to_pandas_table(dataframe), metadata)
                for dataframe, metadata in consultores_data
            ],
            output_filename=output_filename,
        )

    def generate_single_consultant_report(
        self,
        *,
        cliente: str,
        dataframe: TableData,
        metadata: Dict[str, object],
        output_filename: Optional[str] = None,
        collaborator_rates: Optional[CollaboratorRatesPort] = None,
    ) -> bytes:
        consolidator = TimeSheetConsolidator(
            cliente=cliente,
            collaborator_rates=collaborator_rates,
        )
        return consolidator.generate_single_consultant_report(
            dataframe=to_pandas_table(dataframe),
            metadata=metadata,
            output_filename=output_filename,
        )
