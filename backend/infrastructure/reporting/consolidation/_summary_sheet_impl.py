from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from backend.shared.tabular.pandas_mapper import to_pandas_table

from .styles import *

logger = logging.getLogger(__name__)



class SummarySheetImplMixin:
    def _create_summary_sheet(
        self,
        ws: Worksheet,
        periodo: str,
        dias_laborables: int,
        sorted_metrics: List["ConsultorMetrics"],
        sheet_names: Optional[List[str]] = None,
    ) -> None:
        """Crea la hoja de resumen con diseno corporativo NOVA-TI."""
        # Limpieza de merges previos para evitar conflictos con el nuevo layout
        for merged_range in list(ws.merged_cells.ranges):
            ws.unmerge_cells(str(merged_range))

        def px_to_points(px: float) -> float:
            """Convierte pixeles a puntos (Excel usa puntos en alturas)."""
            return round(px * 0.75, 2)

        total_columns = 14
        end_col = get_column_letter(total_columns)

        header_fill = PatternFill(start_color=COLOR_BLACK, end_color=COLOR_BLACK, fill_type='solid')
        accent_fill = PatternFill(start_color=COLOR_LIME, end_color=COLOR_LIME, fill_type='solid')

        # Logo en esquina superior izquierda
        # Logo principal Business IT (restaurado al tamaño visual anterior)
        self._add_logo(ws, anchor="A1", max_width=150, max_height=52)
        if self.client_logo_path:
            # Logo cliente en resumen
            client_stem = self.client_logo_path.stem.lower()
            if "nova" in client_stem:
                # Insercion temporal para obtener el tamano de referencia
                self._add_logo(ws, anchor=f"{end_col}1", logo_path=self.client_logo_path, max_width=150, max_height=52)
            elif "baninter" in client_stem:
                self._add_logo(ws, anchor="L1", logo_path=self.client_logo_path, max_width=150, max_height=52)
            else:
                self._add_logo(ws, anchor="L1", max_width=105, max_height=30, logo_path=self.client_logo_path)

        # ============================================================
        # HEADER (filas 1-3)
        # ============================================================
        ws.merge_cells(f"A1:{end_col}1")
        title_cell = ws['A1']
        title_cell.value = 'INFORME CONSOLIDADO DE ACTIVIDADES'
        title_cell.font = TITLE_FONT
        title_cell.alignment = CENTER_ALIGNMENT
        title_cell.fill = header_fill

        ws.merge_cells(f"A2:{end_col}2")
        subtitle_cell = ws['A2']
        subtitle_cell.value = self.cliente
        subtitle_cell.font = SUBTITLE_FONT
        subtitle_cell.alignment = CENTER_ALIGNMENT
        subtitle_cell.fill = header_fill

        ws.merge_cells(f"A3:{end_col}3")
        line_cell = ws['A3']
        line_cell.fill = accent_fill

        for row in [1, 2]:
            ws.row_dimensions[row].height = px_to_points(35)
            for col in range(1, total_columns + 1):
                ws.cell(row=row, column=col).fill = header_fill
        ws.row_dimensions[3].height = px_to_points(5)


        # ============================================================
        # INFO DEL CONTRATO (filas 5-9)
        # ============================================================
        info_start = 5
        contract_info = [
            ('Cliente:', self.cliente),
            ('Fecha inicio:', f"01/{periodo.split()[0][:3]}/{periodo.split()[1]}"),
            ('Fecha fin:', f"30/{periodo.split()[0][:3]}/{periodo.split()[1]}"),
            ('Mes:', periodo),
            ('Dias Laborables:', dias_laborables),
        ]

        label_col = 'B'
        value_start_col = 'C'
        value_end_col = 'G'
        value_border = Border(bottom=Side(style='medium', color=COLOR_LIME))

        for idx, (label, value) in enumerate(contract_info):
            row = info_start + idx

            label_cell = ws[f"{label_col}{row}"]
            label_cell.value = label
            label_cell.font = INFO_LABEL_FONT
            label_cell.alignment = RIGHT_ALIGNMENT

            value_cell = ws[f"{value_start_col}{row}"]
            value_cell.value = value
            value_cell.font = INFO_VALUE_FONT
            value_cell.alignment = LEFT_ALIGNMENT
            value_cell.fill = INFO_FILL
            value_cell.border = value_border
            ws.merge_cells(f"{value_start_col}{row}:{value_end_col}{row}")

            ws.row_dimensions[row].height = px_to_points(24)

        # ============================================================
        # TABLA DE DATOS
        # ============================================================
        header_row = info_start + len(contract_info) + 2
        headers = [
            'No.',
            'NOMBRE',
            'CARGO',
            'DIAS LABORADOS',
            'VALOR TARIFA',
            'VALOR DÍA',
            'TOTAL',
            'DIAS LABORADOS',
            'HN',
            'HORAS EXTRAS',
            'VALOR A FACTURAR',
            'Valor Horas Extras',
            'Total Horas Extras',
            'TOTAL GENERAL',
        ]

        header_border = Border(
            left=Side(style='thin', color=COLOR_DARK_GREEN),
            right=Side(style='thin', color=COLOR_DARK_GREEN),
            top=Side(style='thin', color=COLOR_DARK_GREEN),
            bottom=Side(style='thin', color=COLOR_DARK_GREEN),
        )

        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=header_row, column=col_idx, value=header)
            if col_idx in {8, 9, 10, 11, 12, 13, 14}:
                cell.font = TABLE_HEADER_ORANGE_FONT
                cell.fill = TABLE_HEADER_ORANGE_FILL
            else:
                cell.font = TABLE_HEADER_FONT
                cell.fill = TABLE_HEADER_FILL
            cell.alignment = CENTER_ALIGNMENT
            cell.border = header_border

        ws.row_dimensions[header_row].height = px_to_points(35)

        data_row_height = px_to_points(28)

        for idx, metrics in enumerate(sorted_metrics, start=1):
            row = header_row + idx
            cargo_norm = str(metrics.cargo or "").lower().strip()
            if "semi" in cargo_norm:
                row_fill = SEMISENIOR_ROW_FILL
            elif "senior" in cargo_norm:
                row_fill = SENIOR_ROW_FILL
            elif "junior" in cargo_norm:
                row_fill = JUNIOR_ROW_FILL
            else:
                row_fill = None
            horas_normales_formula = None
            horas_extras_formula = None
            if sheet_names and idx - 1 < len(sheet_names):
                sheet_name = sheet_names[idx - 1]
                dataframe = to_pandas_table(metrics.dataframe)
                last_detail_row = 9 + len(dataframe)
                has_hour_col = False
                for col in list(dataframe.columns):
                    header = str(col).strip().lower()
                    if "hora" in header and "tipo" not in header:
                        has_hour_col = True
                        break
                total_row = (last_detail_row + 1) if has_hour_col else None
                last_data_row = total_row or last_detail_row
                start_row = max(last_data_row + 2, 41)
                r_total_1 = start_row
                r_total_2 = start_row + 1
                r_total_3 = start_row + 2
                horas_normales_formula = f"='{sheet_name}'!L{r_total_1}"
                horas_extras_formula = f"='{sheet_name}'!L{r_total_2}+'{sheet_name}'!L{r_total_3}"
            values = [
                idx,
                metrics.nombre,
                metrics.cargo,
                None,  # DIAS LABORADOS (formula desde header)
                round(metrics.valor_tarifa, 2),
                None,  # VALOR DÍA (formula)
                None,  # TOTAL (formula)
                None,  # DIAS LABORADOS REALES (formula desde HN)
                horas_normales_formula or round(metrics.total_horas_normales, 2),  # HN
                horas_extras_formula or round(metrics.total_horas_extras, 2),
                None,  # VALOR A FACTURAR (formula)
                round(metrics.valor_hora_extra, 2),
                None,  # Total Horas Extras (formula)
                None,  # TOTAL GENERAL (formula)
            ]

            for col_idx, value in enumerate(values, start=1):
                cell = ws.cell(row=row, column=col_idx, value=value)
                cell.font = DATA_FONT
                cell.border = THIN_BORDER

                if col_idx == 1:
                    cell.alignment = CENTER_ALIGNMENT
                elif col_idx in [2, 3]:
                    cell.alignment = LEFT_ALIGNMENT
                else:
                    cell.alignment = RIGHT_ALIGNMENT

                if col_idx in [5, 6, 7, 11, 12, 13, 14]:
                    cell.number_format = '$#,##0.00'
                elif col_idx in [4, 8]:
                    cell.number_format = '0'
                elif col_idx in [9, 10]:
                    cell.number_format = '0.0'

                # Formularios por fila
                if col_idx == 4:  # DIAS LABORADOS = valor del header
                    cell.value = f"=$C$9"
                if col_idx == 6:  # VALOR DÍA = VALOR TARIFA / DIAS LABORADOS (col 4)
                    cell.value = f"=E{row}/D{row}"
                elif col_idx == 7:  # TOTAL = DIAS LABORADOS (col 4) * VALOR DÍA
                    cell.value = f"=D{row}*F{row}"
                elif col_idx == 8:  # DIAS LABORADOS = HN (col 9) / 8
                    cell.value = f"=I{row}/8"
                elif col_idx == 11:  # VALOR A FACTURAR = DIAS LABORADOS (col 8) * VALOR DÍA
                    cell.value = f"=H{row}*F{row}"
                elif col_idx == 13:  # Total Horas Extras = Valor Horas Extras * Horas Extras
                    cell.value = f"=L{row}*J{row}"
                elif col_idx == 14:  # TOTAL GENERAL solo se calcula en la fila TOTAL
                    cell.value = None

                if row_fill:
                    cell.fill = row_fill
                elif idx % 2 == 0:
                    cell.fill = ALTERNATE_ROW_FILL

            ws.row_dimensions[row].height = data_row_height

        # ============================================================
        # FILA TOTALES
        # ============================================================
        total_row = header_row + len(sorted_metrics) + 1
        ws.merge_cells(f"A{total_row}:C{total_row}")

        for col_idx in range(1, 4):
            total_cell = ws.cell(row=total_row, column=col_idx)
            if col_idx == 1:
                total_cell.value = 'TOTAL'
            total_cell.font = TOTAL_ROW_FONT
            total_cell.fill = TOTAL_ROW_FILL
            total_cell.alignment = CENTER_ALIGNMENT
            total_cell.border = THICK_TOP_BORDER

        totals = {
            4: f"=C9",
            5: round(sum(m.valor_tarifa for m in self.consultores_metrics), 2),
            6: '',
            7: f"=SUM(G{header_row + 1}:G{total_row - 1})",
            8: f"=SUM(H{header_row + 1}:H{total_row - 1})",
            9: f"=SUM(I{header_row + 1}:I{total_row - 1})",
            10: f"=SUM(J{header_row + 1}:J{total_row - 1})",
            11: f"=SUM(K{header_row + 1}:K{total_row - 1})",
            12: '',
            13: f"=SUM(M{header_row + 1}:M{total_row - 1})",
            14: f"=K{total_row}+M{total_row}",
        }

        highlight_total_cols = {9, 11, 13}
        for col_idx, total_value in totals.items():
            cell = ws.cell(row=total_row, column=col_idx, value=total_value)
            cell.font = TOTAL_ROW_FONT
            if col_idx == 14:
                cell.fill = TOTAL_ROW_GRAND_FILL
            elif col_idx in highlight_total_cols:
                cell.fill = TOTAL_ROW_HIGHLIGHT_FILL
            else:
                cell.fill = TOTAL_ROW_FILL
            cell.border = THICK_TOP_BORDER
            cell.alignment = RIGHT_ALIGNMENT

            if col_idx in [5, 7, 11, 12, 13, 14] and total_value not in ('', None):
                cell.number_format = '$#,##0.00'
            elif col_idx in [4, 8] and total_value not in ('', None):
                cell.number_format = '0'
            elif col_idx in [9, 10] and total_value not in ('', None):
                cell.number_format = '0.0'

        ws.row_dimensions[total_row].height = px_to_points(32)

        # ============================================================
        # AJUSTES FINALES
        # ============================================================
        column_widths = {
            'A': 6,
            'B': 30,
            'C': 16,
            'D': 12,
            'E': 14,
            'F': 14,
            'G': 14,
            'H': 12,
            'I': 10,
            'J': 12,
            'K': 16,
            'L': 12,
            'M': 14,
            'N': 16,
        }

        for col_letter, width in column_widths.items():
            ws.column_dimensions[col_letter].width = width

        ws.freeze_panes = f"A{header_row + 1}"

        footer_row = total_row + 2
        ws.merge_cells(f"A{footer_row}:{end_col}{footer_row}")
        ws[f"A{footer_row}"] = f"Informe generado automaticamente | {self.cliente} (c) {datetime.now().year}"
        ws[f"A{footer_row}"].font = Font(name='Calibri', size=9, italic=True, color='7F8C8D')
        ws[f"A{footer_row}"].alignment = CENTER_ALIGNMENT

        logger.info('Hoja de resumen creada con diseno corporativo')
