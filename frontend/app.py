from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================================
# PATH SETUP
# ============================================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ============================================================================
# IMPORTS - Backend modules
# ============================================================================

from backend.batch_processor import (  # noqa: E402
    BatchFileRequest,
    BatchFileResult,
    BatchProcessor,
)
from backend.client_profiles import ClientProfileManager  # noqa: E402
from backend.detectors import auto_detect_profile, resolve_employee  # noqa: E402
from backend.consolidator_integration import (  # noqa: E402
    generate_consolidated_from_batch_results,
    validate_batch_results_for_consolidation,
)
from backend.excel_parser import ParsedSheet, load_sheet_with_header  # noqa: E402
from backend.holiday_detector import HolidayDetector  # noqa: E402
from backend.processor import ColumnMapping, TimeSheetProcessor  # noqa: E402
from config.settings import get_settings  # noqa: E402

# Import custom theme module
from streamlit_ui_theme import (  # noqa: E402
    apply_theme,
    render_theme_toggle,
    render_header,
    render_section_header,
    render_divider,
    render_empty_state,
    render_status_card,
    render_info_grid,
    get_theme,
)

import logging  # noqa: E402

# ============================================================================
# INITIALIZATION
# ============================================================================

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

processor = TimeSheetProcessor()
batch_processor = BatchProcessor(processor)
profile_manager = ClientProfileManager()
holiday_detector = HolidayDetector()

# ============================================================================
# PAGE CONFIG - Must be first Streamlit command
# ============================================================================

st.set_page_config(
    page_title="Depurador de Horas | Nova-TI",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom theme immediately after page config
apply_theme()

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "processor_result" not in st.session_state:
    st.session_state["processor_result"] = None
if "last_mapping" not in st.session_state:
    st.session_state["last_mapping"] = None
if "batch_results" not in st.session_state:
    st.session_state["batch_results"] = []
if "batch_mapping" not in st.session_state:
    st.session_state["batch_mapping"] = None
if "current_metadata" not in st.session_state:
    st.session_state["current_metadata"] = None

for key, default in {
    "batch_selected_profile": "__manual__",
    "batch_map_date": "",
    "batch_map_hours": "",
    "batch_map_description": "",
    "batch_map_project": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_plotly_theme() -> dict:
    """Get Plotly theme colors based on current theme."""
    is_dark = get_theme() == "dark"
    if is_dark:
        return {
            "bg": "rgba(0,0,0,0)",
            "paper_bg": "rgba(0,0,0,0)",
            "font_color": "#a1a1aa",
            "grid_color": "#27272a",
        }
    else:
        return {
            "bg": "rgba(0,0,0,0)",
            "paper_bg": "rgba(0,0,0,0)",
            "font_color": "#475569",
            "grid_color": "#e2e8f0",
        }


def render_validation_settings() -> tuple[int, int, float, bool]:
    """Render validation settings in an expander."""
    with st.expander("⚙️ Configuración Avanzada", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔍 Detección de Duplicados**")
            similarity_threshold = st.slider(
                "Umbral de similitud",
                min_value=70,
                max_value=100,
                value=90,
                format="%d%%",
                help="Porcentaje de similitud para considerar duplicados",
            )
            min_duplicates = st.number_input(
                "Mínimo de repeticiones",
                min_value=2,
                max_value=10,
                value=3,
                help="Número mínimo de veces que debe repetirse",
            )
            
        with col2:
            st.markdown("**⏰ Validación de Horas**")
            tolerance_factor = st.slider(
                "Factor de tolerancia",
                min_value=1.0,
                max_value=3.0,
                value=1.5,
                step=0.1,
                help="Multiplicador para rangos permitidos",
            )
            show_time_suggestions = st.checkbox(
                "Mostrar referencias de tiempo",
                value=True,
                help="Mostrar rangos típicos por actividad",
            )
            
    return (
        int(similarity_threshold),
        int(min_duplicates),
        float(tolerance_factor),
        bool(show_time_suggestions),
    )


def render_holiday_block(
    dataframe: pd.DataFrame,
    date_column: Optional[str],
    *,
    title: str = "📅 Feriados del mes",
    metadata: Optional[Dict[str, object]] = None,
) -> None:
    """Render holiday information block."""
    info = None
    if metadata and metadata.get("period_start") and metadata.get("period_end"):
        info = holiday_detector.detect_period_holidays(
            metadata.get("period_start"),
            metadata.get("period_end"),
        )
    elif date_column and date_column in dataframe.columns and not dataframe.empty:
        try:
            info = holiday_detector.detect_month_holidays(dataframe, date_column)
        except Exception as exc:
            logger.warning("No se pudieron detectar feriados: %s", exc)
            info = None
            
    if info is None:
        return
        
    with st.expander(title, expanded=False):
        if info.month is None or info.year is None:
            st.info("No se detectaron fechas válidas.")
            return
            
        st.markdown(f"**Mes:** {info.month_name or info.month} {info.year}")
        
        if not info.holidays:
            st.caption("Sin feriados registrados para este mes.")
            return
            
        for holiday in info.holidays:
            st.markdown(f"🗓️ **{holiday['date']}** — {holiday['name']}")


def get_profile_catalog() -> Dict[str, object]:
    """Get available client profiles."""
    return {profile.client_id: profile for profile in profile_manager.list_profiles()}


def render_single_file_mapping(
    columns: List[str],
    auto_profile_id: Optional[str] = None,
) -> tuple[ColumnMapping, Optional[str], Dict[str, object]]:
    """Render column mapping UI for single file processing."""
    profiles = get_profile_catalog()
    manual_option = "__manual_single__"
    options = [manual_option] + sorted(profiles.keys())

    def _format(option: str) -> str:
        if option == manual_option:
            return "📝 Mapeo manual"
        profile = profiles.get(option)
        return f"🏢 {profile.name}" if profile else option

    default_profile = auto_profile_id or st.session_state.get("selected_profile_for_single", manual_option)
    if default_profile not in options:
        default_profile = manual_option
        
    selected_profile = st.selectbox(
        "Perfil de cliente",
        options,
        format_func=_format,
        index=options.index(default_profile),
        help="Selecciona un perfil o configura manualmente",
    )
    st.session_state["selected_profile_for_single"] = selected_profile

    if selected_profile != manual_option:
        profile = profiles.get(selected_profile)
        if profile is None:
            st.warning("El perfil seleccionado no existe.")
        else:
            mapping = profile.to_column_mapping()
            if mapping:
                st.success(f"✅ Mapeo aplicado: {profile.name}")
                
                items = [(k.capitalize(), v) for k, v in profile.mapping.items() if v]
                render_info_grid(items)
                        
                return mapping, selected_profile, profile.settings
            st.warning("El perfil no tiene columnas obligatorias.")

    st.markdown("**Mapeo de columnas:**")
    col1, col2 = st.columns(2)
    
    with col1:
        column_date = st.selectbox("📅 Fecha", columns)
        column_hours = st.selectbox("⏱️ Horas", columns, index=min(1, len(columns) - 1))
        
    with col2:
        column_description = st.selectbox("📝 Descripción", columns)
        column_project = st.selectbox(
            "🏷️ Proyecto (opcional)",
            ["— Ninguna —"] + columns,
        )

    mapping = ColumnMapping(
        date=column_date,
        hours=column_hours,
        description=column_description,
        project=None if column_project == "— Ninguna —" else column_project,
    )
    return mapping, None, {}


def render_batch_sidebar() -> Dict[str, object]:
    """Render batch processing sidebar."""
    st.sidebar.markdown("**📁 Archivos**")
    uploaded_files = st.sidebar.file_uploader(
        "Cargar archivos",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        key="batch_files",
        label_visibility="collapsed",
    )
    
    if uploaded_files:
        st.sidebar.success(f"✓ {len(uploaded_files)} archivo(s)")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🏢 Cliente**")
    
    profiles = get_profile_catalog()
    manual_option = "__manual__"
    options = [manual_option] + sorted(profiles.keys())

    def _format_profile(option: str) -> str:
        if option == manual_option:
            return "📝 Mapeo manual"
        profile = profiles.get(option)
        return f"🏢 {profile.name}" if profile else option

    selected_profile = st.sidebar.selectbox(
        "Cliente",
        options=options,
        format_func=_format_profile,
        index=options.index(st.session_state.get("batch_selected_profile", manual_option))
        if st.session_state.get("batch_selected_profile") in options
        else 0,
        label_visibility="collapsed",
    )
    st.session_state["batch_selected_profile"] = selected_profile

    profile_obj = profiles.get(selected_profile)
    
    if selected_profile != manual_option and profile_obj:
        st.sidebar.caption("Mapeo detectado:")
        for logical_name, column in profile_obj.mapping.items():
            st.sidebar.markdown(f"• **{logical_name}:** {column}")
            
        mapping_values = {
            "date": profile_obj.mapping.get("date", ""),
            "hours": profile_obj.mapping.get("hours", ""),
            "description": profile_obj.mapping.get("description", ""),
            "project": profile_obj.mapping.get("project", ""),
        }
    else:
        st.sidebar.caption("Define el mapeo:")
        mapping_values = {
            "date": st.sidebar.text_input("📅 Fecha", key="batch_map_date", placeholder="Columna"),
            "hours": st.sidebar.text_input("⏱️ Horas", key="batch_map_hours", placeholder="Columna"),
            "description": st.sidebar.text_input("📝 Descripción", key="batch_map_description", placeholder="Columna"),
            "project": st.sidebar.text_input("🏷️ Proyecto", key="batch_map_project", placeholder="Opcional"),
        }

    return {
        "files": uploaded_files or [],
        "profile_id": None if selected_profile == manual_option else selected_profile,
        "mapping_values": mapping_values,
        "profile_settings": profile_obj.settings if profile_obj else {},
    }


def auto_detect_profile_from_files(files: List) -> tuple[Optional[str], Optional[Dict[str, object]]]:
    """Auto-detect client profile from uploaded files."""
    profiles = list(get_profile_catalog().values())
    if not files:
        return None, None
    sample = files[0]
    sample_bytes = sample.getvalue()
    parsed = load_sheet_with_header(sample_bytes)
    metadata = getattr(parsed, "metadata", {}) or {}
    profile_id = auto_detect_profile(sample.name, metadata, profiles)
    return profile_id, metadata


def render_metadata_summary(
    metadata: Optional[Dict[str, object]],
    *,
    employee_info: Optional[Dict[str, Optional[str]]] = None,
    title: str = "📄 Metadata",
) -> None:
    """Render metadata summary."""
    if not metadata:
        return
        
    details = []
    if employee_info:
        if employee_info.get("metadata"):
            details.append(("👤 Empleado", employee_info["metadata"]))
        elif employee_info.get("final"):
            details.append(("👤 Empleado", employee_info["final"]))
    elif metadata.get("employee"):
        details.append(("👤 Empleado", metadata.get("employee")))
        
    if metadata.get("company"):
        details.append(("🏢 Empresa", metadata.get("company")))
    if metadata.get("period_start") and metadata.get("period_end"):
        details.append(("📅 Periodo", f"{metadata['period_start']} → {metadata['period_end']}"))
    if metadata.get("month_name"):
        details.append(("📆 Mes", metadata.get("month_name")))
        
    if not details:
        return
        
    with st.expander(title, expanded=False):
        render_info_grid(details)


def render_batch_consolidated_report(results: List[BatchFileResult]) -> None:
    """Render consolidated batch report."""
    valid = [item for item in results if item.success and item.result is not None]
    if len(valid) <= 1:
        return

    rows = []
    for item in valid:
        processor_result = item.result
        metadata = processor_result.metadata or {}
        employee_name = (
            metadata.get("employee")
            or metadata.get("empleado")
            or Path(item.file_name).stem
        )
        summary = processor_result.summary
        rows.append({
            "Empleado": employee_name,
            "Horas": summary.horas_totales,
            "Registros": summary.total_registros,
            "Score": summary.quality_score,
            "Errores": summary.total_errores,
        })

    df_summary = pd.DataFrame(rows)
    
    render_divider()
    render_section_header("Reporte consolidado", icon="📊", description="Resumen del equipo")

    cols = st.columns(4)
    cols[0].metric("👥 Empleados", len(df_summary))
    cols[1].metric("⏰ Horas", f"{df_summary['Horas'].sum():.1f} h")
    cols[2].metric("📈 Score promedio", f"{df_summary['Score'].mean():.0f}%")
    cols[3].metric("📝 Registros", int(df_summary["Registros"].sum()))

    df_summary["Estado"] = df_summary["Score"].apply(
        lambda score: "✅ Excelente" if score >= 90
        else "🟢 Bueno" if score >= 80
        else "🟡 Revisar" if score >= 60
        else "🔴 Crítico"
    )

    st.dataframe(
        df_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Empleado": st.column_config.TextColumn("Empleado", width="medium"),
            "Horas": st.column_config.NumberColumn("Horas", format="%.1f"),
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
        }
    )

    # Chart
    theme_colors = get_plotly_theme()
    fig = px.bar(
        df_summary,
        x="Empleado",
        y="Horas",
        color="Score",
        color_continuous_scale="RdYlGn",
        title="Horas por empleado",
    )
    fig.update_layout(
        plot_bgcolor=theme_colors["bg"],
        paper_bgcolor=theme_colors["paper_bg"],
        font=dict(family="Inter, sans-serif", color=theme_colors["font_color"]),
        title_font_size=16,
        margin=dict(t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Excel Generation
    render_divider()
    render_section_header("Generar consolidado Excel", icon="📄")

    is_valid, warnings = validate_batch_results_for_consolidation(results)

    if warnings:
        with st.expander("⚠️ Advertencias", expanded=False):
            for warning in warnings:
                st.warning(warning)

    detected_client_name = None
    profiles_catalog = get_profile_catalog()
    for r in results:
        if not r.success:
            continue
        if r.client_id and r.client_id in profiles_catalog:
            detected_client_name = profiles_catalog[r.client_id].name
            break
        company = (r.metadata or {}).get("company")
        if company:
            detected_client_name = str(company)
            break
    default_client_name = detected_client_name or "NOVA - TI"

    col1, col2 = st.columns([2, 1])

    with col1:
        cliente_nombre = st.text_input("Nombre del cliente", value=default_client_name)

    with col2:
        first_valid = next((r for r in results if r.success and r.metadata), None)
        if first_valid:
            mes = first_valid.metadata.get("month_name", "Unknown")
            year = first_valid.metadata.get("year", "2025")
            default_filename = f"Consolidado_{default_client_name.replace(' ', '_')}_{mes}_{year}.xlsx"
        else:
            default_filename = "Consolidado.xlsx"

        output_filename = st.text_input("Nombre archivo", value=default_filename)

    if st.button("🚀 Generar Consolidado", type="primary", disabled=not is_valid, use_container_width=True):
        with st.spinner("Generando..."):
            try:
                consolidated = generate_consolidated_from_batch_results(
                    batch_results=results,
                    cliente=cliente_nombre,
                    output_filename=output_filename,
                )

                st.success("✅ Consolidado generado")

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Consultores", consolidated.consultores_incluidos)
                col_b.metric("Total facturar", f"${consolidated.total_facturar:,.2f}")
                col_c.metric("Horas", f"{consolidated.total_horas:.1f} h")

                st.download_button(
                    label="⬇️ Descargar Excel",
                    data=consolidated.workbook_bytes,
                    file_name=consolidated.output_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            except Exception as exc:
                st.error(f"Error: {exc}")
                logger.exception("Error generando consolidado: %s", exc)


def build_mapping_from_values(values: Dict[str, str]) -> Optional[ColumnMapping]:
    """Build column mapping from user input values."""
    date_col = values.get("date", "").strip()
    hours_col = values.get("hours", "").strip()
    description_col = values.get("description", "").strip()
    project_col = values.get("project", "").strip()
    
    if not date_col or not hours_col or not description_col:
        return None
        
    return ColumnMapping(
        date=date_col,
        hours=hours_col,
        description=description_col,
        project=project_col or None,
    )


def run_batch_mode(
    *,
    batch_state: Dict[str, object],
    correct_spelling: bool,
    employee_role: str,
) -> None:
    """Run batch processing mode."""
    render_section_header("Procesamiento por lotes", icon="📦", description="Procesa múltiples archivos")
    
    similarity_threshold, min_duplicates, tolerance_factor, show_time_suggestions = render_validation_settings()

    uploaded_files: List = batch_state.get("files") or []
    
    if not uploaded_files:
        render_empty_state(
            "📁",
            "Selecciona archivos para comenzar",
            "Usa la barra lateral para cargar uno o más archivos Excel"
        )
        
        if show_time_suggestions:
            st.caption("📌 Referencias: Daily ~0.25h · Reuniones 0.25-3h · Desarrollo 1-8h · Code review 0.25-2h")
        return

    profiles_catalog = get_profile_catalog()
    profile_id = batch_state.get("profile_id")
    profile_obj = profiles_catalog.get(profile_id) if profile_id else None
    preview_metadata: Optional[Dict[str, object]] = None

    if profile_obj is None:
        detected_profile_id, preview_metadata = auto_detect_profile_from_files(uploaded_files)
        if detected_profile_id and detected_profile_id in profiles_catalog:
            profile_obj = profiles_catalog[detected_profile_id]
            profile_id = detected_profile_id
            st.session_state["batch_selected_profile"] = detected_profile_id
            st.success(f"🎯 Cliente detectado: **{profile_obj.name}**")
        elif preview_metadata:
            employee_info = resolve_employee(preview_metadata, uploaded_files[0].name)
            render_metadata_summary(preview_metadata, employee_info=employee_info)

    if profile_obj is None:
        mapping = build_mapping_from_values(batch_state.get("mapping_values", {}))
        if mapping is None:
            st.warning("⚠️ Define columnas de Fecha, Horas y Descripción.")
            return
        profile_settings = batch_state.get("profile_settings") or {}
        header_keywords = [
            value.strip()
            for value in (batch_state.get("mapping_values") or {}).values()
            if value and value.strip()
        ]
    else:
        mapping = profile_obj.to_column_mapping()
        if mapping is None:
            st.error("El perfil no tiene columnas obligatorias.")
            return
        profile_settings = profile_obj.settings
        header_keywords = [value for value in profile_obj.mapping.values() if value]
        if preview_metadata is None and uploaded_files:
            _, preview_metadata = auto_detect_profile_from_files(uploaded_files)
        if preview_metadata:
            employee_info = resolve_employee(preview_metadata, uploaded_files[0].name)
            render_metadata_summary(preview_metadata, employee_info=employee_info)

    duplicate_threshold = int(profile_settings.get("duplicate_similarity_threshold", similarity_threshold))
    min_duplicates_setting = int(profile_settings.get("duplicate_min_occurrences", min_duplicates))
    hours_tolerance = float(profile_settings.get("hours_tolerance_factor", tolerance_factor))
    role_to_use = str(profile_settings.get("rol_default") or profile_settings.get("role") or employee_role)
    spelling_flag = bool(profile_settings.get("correct_spelling", correct_spelling))

    requests: List[BatchFileRequest] = []
    for file_obj in uploaded_files:
        file_name = file_obj.name or "reporte.xlsx"
        requests.append(
            BatchFileRequest(
                file_name=file_name,
                file_bytes=file_obj.getvalue(),
                mapping=mapping,
                client_id=profile_id,
                header_keywords=header_keywords,
                profile_settings=profile_settings,
                processor_kwargs={
                    "correct_spelling": spelling_flag,
                    "role": role_to_use,
                    "project_name": mapping.project or "No especificado",
                    "duplicate_similarity_threshold": duplicate_threshold,
                    "duplicate_min_occurrences": min_duplicates_setting,
                    "hours_tolerance_factor": hours_tolerance,
                },
            )
        )

    if st.button(f"▶️ Procesar {len(requests)} archivo(s)", type="primary", use_container_width=True):
        progress_placeholder = st.empty()
        progress_bar = st.progress(0)

        def update_progress(current: int, total: int, message: str) -> None:
            percent = 0 if total == 0 else int((current / total) * 100)
            progress_placeholder.info(f"🔄 {message} ({current}/{total})")
            progress_bar.progress(min(percent, 100))

        results = batch_processor.process_batch(requests, progress_callback=update_progress)
        progress_placeholder.success("✅ Procesamiento completado")
        progress_bar.empty()
        st.session_state["batch_results"] = results
        st.session_state["batch_mapping"] = mapping

    batch_results: List[BatchFileResult] = st.session_state.get("batch_results", [])
    mapping_for_display: Optional[ColumnMapping] = st.session_state.get("batch_mapping") or mapping
    
    if not batch_results:
        st.info("📋 Presiona el botón para iniciar.")
        return

    success_count = sum(1 for result in batch_results if result.success)
    
    render_divider()
    render_section_header(f"Resultados ({success_count}/{len(batch_results)})", icon="📋")

    for result in batch_results:
        if result.success and result.result:
            summary = result.result.summary
            metadata = result.result.metadata or {}
            
            st.success(f"✅ {result.file_name}")
            
            employee_info = resolve_employee(metadata, result.file_name)
            render_metadata_summary(metadata, employee_info=employee_info, title=f"📄 {result.file_name}")
            
            metrics = st.columns(4)
            metrics[0].metric("📝 Registros", summary.total_registros)
            metrics[1].metric("⏰ Horas", f"{summary.horas_totales:.1f}")
            metrics[2].metric("🚨 Errores", summary.errores_criticos)
            metrics[3].metric("📈 Score", f"{summary.quality_score:.0f}%")

            col1, col2 = st.columns(2)
            col1.download_button(
                label="⬇️ Excel",
                data=result.result.workbook_bytes,
                file_name=result.result.output_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            summary_json = json.dumps({
                "calidad": summary.quality_score,
                "registros": summary.total_registros,
            }, indent=2)
            col2.download_button(
                label="⬇️ JSON",
                data=summary_json,
                file_name=f"{Path(result.result.output_filename).stem}.json",
                mime="application/json",
            )

            errors_df = result.result.errors_dataframe
            with st.expander("Errores detectados", expanded=False):
                if errors_df.empty:
                    st.success("Sin errores reportados.")
                else:
                    st.dataframe(
                        errors_df,
                        use_container_width=True,
                        hide_index=True,
                    )

            if mapping_for_display:
                render_holiday_block(
                    result.result.corrected_dataframe,
                    mapping_for_display.date,
                    title=f"📅 Feriados",
                    metadata=metadata,
                )
        else:
            st.error(f"❌ {result.file_name}")
            if result.error:
                st.write(result.error)

        st.markdown("---")

    render_batch_consolidated_report(batch_results)


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("### 🎨 Apariencia")
    render_theme_toggle()
    
    st.markdown("---")
    st.markdown("### ⚙️ Configuración")
    
    processing_mode = st.radio(
        "Modo",
        ["Individual", "Por lotes"],
        horizontal=True,
    )
    
    correct_spelling = st.checkbox(
        "🤖 Corrección ortográfica",
        value=True,
    )
    
    employee_role = st.selectbox(
        "👤 Rol del empleado",
        ["Desconocido", "Developer", "QA", "DevOps", "Project Manager", "Otro"],
    )

use_blob = False
blob_original = ""
blob_corregido = ""
batch_sidebar_state: Optional[Dict[str, object]] = None

if processing_mode == "Individual":
    with st.sidebar:
        st.markdown("---")
        st.markdown("### ☁️ Azure Blob")
        use_blob = st.checkbox("Usar Azure Blob Storage", value=False)
        
        if use_blob:
            blob_original = st.text_input("Blob original")
            blob_corregido = st.text_input("Blob corregido")
else:
    with st.sidebar:
        st.markdown("---")
        batch_sidebar_state = render_batch_sidebar()


# ============================================================================
# MAIN CONTENT
# ============================================================================

render_header("Depurador de Horas", "Valida y depura registros de timesheet automáticamente")

# Batch mode
if processing_mode == "Por lotes":
    if batch_sidebar_state is None:
        st.error("Error de configuración.")
    else:
        run_batch_mode(
            batch_state=batch_sidebar_state,
            correct_spelling=correct_spelling,
            employee_role=employee_role,
        )
    st.stop()


# ============================================================================
# INDIVIDUAL FILE PROCESSING
# ============================================================================

render_section_header("Cargar archivo", icon="📤")

uploaded_file = st.file_uploader(
    "Excel",
    type=["xlsx", "xls"],
    label_visibility="collapsed",
)

if not uploaded_file:
    render_empty_state(
        "📊",
        "Arrastra tu archivo Excel aquí",
        "O haz clic para seleccionar un archivo .xlsx o .xls"
    )
    st.stop()

source_bytes = uploaded_file.getvalue()
source_name = uploaded_file.name or "reporte.xlsx"


@st.cache_data(show_spinner=False)
def cache_parsed_sheet_auto(file_bytes: bytes) -> ParsedSheet:
    return load_sheet_with_header(file_bytes)


with st.spinner("Analizando archivo..."):
    parsed_sheet = cache_parsed_sheet_auto(source_bytes)
    
dataframe = parsed_sheet.dataframe.copy()
columns = [str(col) for col in dataframe.columns]

if not columns:
    st.error("No se detectaron columnas.")
    st.stop()

st.success(f"✅ Hoja: **{parsed_sheet.sheet_name}** (fila {parsed_sheet.header_row + 1})")

render_section_header("Vista previa", icon="👁️")
st.dataframe(dataframe.head(15), use_container_width=True, hide_index=True)

metadata = getattr(parsed_sheet, "metadata", {}) or {}
st.session_state["current_metadata"] = metadata
employee_context = resolve_employee(metadata, source_name)
render_metadata_summary(metadata, employee_info=employee_context)

profiles_catalog = list(get_profile_catalog().values())
auto_profile_id = auto_detect_profile(source_name, metadata, profiles_catalog)

if auto_profile_id:
    profile_obj = next((p for p in profiles_catalog if p.client_id == auto_profile_id), None)
    if profile_obj:
        st.info(f"🎯 Cliente detectado: **{profile_obj.name}**")

render_divider()
render_section_header("Configuración", icon="🔗")

mapping, selected_profile_id, profile_settings = render_single_file_mapping(columns, auto_profile_id)
st.session_state["last_mapping"] = mapping

similarity_threshold, min_duplicates, tolerance_factor, show_time_suggestions = render_validation_settings()

duplicate_threshold = int(profile_settings.get("duplicate_similarity_threshold", similarity_threshold))
min_duplicates_effective = int(profile_settings.get("duplicate_min_occurrences", min_duplicates))
hours_tolerance_effective = float(profile_settings.get("hours_tolerance_factor", tolerance_factor))
effective_role = str(profile_settings.get("rol_default") or profile_settings.get("role") or employee_role)
effective_spelling = bool(profile_settings.get("correct_spelling", correct_spelling))

st.write("")
if st.button("✅ Validar y Depurar", type="primary", use_container_width=True):
    st.session_state["processor_result"] = None
    progress_text = st.empty()
    progress_bar = st.progress(0)

    def announce(text: str, value: float) -> None:
        progress_text.info(text)
        progress_bar.progress(int(value * 100))
        time.sleep(0.1)

    announce("🔍 Analizando estructura...", 0.15)
    announce("🧹 Limpiando metadata...", 0.35)
    announce("📅 Validando fechas y horas...", 0.55)
    announce("🤖 Aplicando correcciones...", 0.75)

    try:
        result = processor.process_parsed_sheet(
            parsed_sheet=parsed_sheet,
            mapping=mapping,
            source_name=source_name,
            original_excel_bytes=source_bytes if use_blob else None,
            correct_spelling=effective_spelling,
            upload_to_blob=use_blob,
            blob_name_original=blob_original or None,
            blob_name_corrected=blob_corregido or None,
            role=effective_role,
            project_name=mapping.project or "No especificado",
            duplicate_similarity_threshold=int(duplicate_threshold),
            duplicate_min_occurrences=int(min_duplicates_effective),
            hours_tolerance_factor=float(hours_tolerance_effective),
            client_profile_id=selected_profile_id or auto_profile_id,
            client_profile_settings=profile_settings,
        )
    except Exception as exc:
        progress_bar.empty()
        progress_text.empty()
        logger.exception("Error: %s", exc)
        st.error(f"Error: {exc}")
        st.stop()
    else:
        announce("✅ Finalizando...", 1.0)
        progress_text.success("🎉 ¡Completado!")
        progress_bar.empty()
        st.session_state["processor_result"] = result

result = st.session_state.get("processor_result")
if result is None:
    st.stop()


# ============================================================================
# RESULTS
# ============================================================================

render_divider()
render_section_header("Resultados", icon="📊")

errors = result.validation_errors
errors_df = result.errors_dataframe
corrected_df = result.corrected_dataframe
summary = result.summary

critical_errors = [
    err for err in errors 
    if err["tipo_error"] in {"horas_incorrectas", "fin_semana", "feriado", "horas_excesivas", "horas_muy_bajas", "fecha_invalida"}
]
warnings = [
    err for err in errors 
    if err["tipo_error"] not in {"horas_incorrectas", "fin_semana", "feriado", "horas_excesivas", "horas_muy_bajas", "fecha_invalida"}
]

total_records = summary.total_registros
removed_count = summary.metadata_removidas
total_hours = summary.horas_totales
quality_score = summary.quality_score

# Gauge and Metrics
gauge_col, metrics_col = st.columns([1.2, 2])

with gauge_col:
    theme = get_plotly_theme()
    
    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=quality_score,
            delta={"reference": 80, "increasing": {"color": "#22c55e"}, "decreasing": {"color": "#ef4444"}},
            title={"text": "Score de Calidad", "font": {"size": 16, "color": theme["font_color"]}},
            number={"font": {"size": 42, "color": theme["font_color"]}, "suffix": "%"},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": theme["font_color"]},
                "bar": {"color": "#3b82f6"},
                "steps": [
                    {"range": [0, 50], "color": "rgba(239, 68, 68, 0.2)"},
                    {"range": [50, 80], "color": "rgba(245, 158, 11, 0.2)"},
                    {"range": [80, 100], "color": "rgba(34, 197, 94, 0.2)"},
                ],
                "threshold": {"value": 80, "line": {"color": "#ef4444", "width": 3}},
            },
        )
    )
    fig_gauge.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

with metrics_col:
    cols = st.columns(2)
    
    with cols[0]:
        st.metric("📈 Score vs 80%", f"{quality_score:.0f}%", f"{quality_score - 80:+.0f} pts")
        st.metric("📝 Registros", total_records, f"{removed_count} metadata" if removed_count else "Sin metadata")
        
    with cols[1]:
        st.metric("⏰ Horas", f"{total_hours:.1f} h", f"≈ {total_hours / 8:.1f} días")
        st.metric("🚨 Críticos", len(critical_errors), "Bloquean" if critical_errors else "✓ OK")

result_metadata = result.metadata or st.session_state.get("current_metadata")
employee_details = resolve_employee(result_metadata or {}, source_name)
render_metadata_summary(result_metadata, employee_info=employee_details)

active_mapping = st.session_state.get("last_mapping")
if active_mapping:
    render_holiday_block(corrected_df, active_mapping.date, metadata=result_metadata)

if show_time_suggestions:
    st.caption("📌 Referencias: Daily ≈0.25h · Reuniones 0.25-3h · Desarrollo 1-8h · Code review 0.25-2h")

render_divider()
render_section_header("Detalle de Validaciones", icon="🔍")

tab1, tab2, tab3, tab4 = st.tabs([
    f"🚨 Críticos ({len(critical_errors)})",
    f"⚠️ Advertencias ({len(warnings)})",
    "✅ Correcciones",
    "📊 Análisis",
])

with tab1:
    if critical_errors:
        st.error("⛔ Errores que bloquean la aprobación")
        
        critical_by_type: Dict[str, list] = {}
        for err in critical_errors:
            critical_by_type.setdefault(err["tipo_error"], []).append(err)
            
        for tipo, error_list in critical_by_type.items():
            with st.expander(f"🔴 {tipo.replace('_', ' ').title()} ({len(error_list)})", expanded=True):
                df_err = pd.DataFrame(error_list)
                st.dataframe(df_err[["fila", "fecha", "descripcion", "valor_original"]], use_container_width=True, hide_index=True)
    else:
        st.success("✅ Sin errores críticos")

with tab2:
    if warnings:
        st.warning(f"💡 {len(warnings)} sugerencias")
        df_warnings = pd.DataFrame(warnings)
        st.dataframe(df_warnings[["fila", "fecha", "tipo_error", "descripcion"]], use_container_width=True, hide_index=True)
    else:
        st.success("✅ Sin advertencias")

with tab3:
    if result.corrections_log:
        st.info(f"🤖 {len(result.corrections_log)} correcciones aplicadas")
        
        for correction in result.corrections_log[:5]:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**❌ Original:**")
                st.code(correction.original_text, language=None)
            with col_b:
                st.markdown("**✅ Corregido:**")
                st.code(correction.corrected_text, language=None)
            st.divider()
            
        if len(result.corrections_log) > 5:
            st.caption(f"+ {len(result.corrections_log) - 5} más")
    else:
        st.success("✅ Sin correcciones necesarias")

with tab4:
    if errors_df.empty:
        st.success("🎉 Timesheet perfecto")
    else:
        error_counts = errors_df["tipo_error"].value_counts().reset_index()
        error_counts.columns = ["tipo", "cantidad"]
        
        theme_colors = get_plotly_theme()
        fig = px.bar(
            error_counts,
            x="cantidad",
            y="tipo",
            orientation="h",
            title="Errores por tipo",
            color="cantidad",
            color_continuous_scale=["#22c55e", "#eab308", "#ef4444"],
        )
        fig.update_layout(
            showlegend=False,
            height=350,
            plot_bgcolor=theme_colors["bg"],
            paper_bgcolor=theme_colors["paper_bg"],
            font=dict(family="Inter, sans-serif", color=theme_colors["font_color"]),
        )
        st.plotly_chart(fig, use_container_width=True)

# Executive Summary
render_divider()
render_section_header("Resumen Ejecutivo", icon="🤖")

if summary.ai_summary:
    acciones = summary.ai_summary.get("acciones") or []
    
    st.markdown(f"**Diagnóstico:** {summary.ai_summary.get('diagnostico', 'N/A')}")
    
    if acciones:
        st.markdown("**Recomendaciones:**")
        for accion in acciones:
            st.markdown(f"• {accion}")
    
    st.markdown(f"**Tiempo estimado:** {summary.ai_summary.get('tiempo_estimado', 'N/A')}")
else:
    st.warning("No se generó resumen automático")

# Final Status
if not critical_errors:
    render_status_card("success", "TIMESHEET APROBABLE", "No se detectan bloqueadores")
else:
    render_status_card("error", "REQUIERE CORRECCIONES", f"{len(critical_errors)} error(es) crítico(s)")

# Downloads
render_divider()
render_section_header("Descargar", icon="💾")

col_d1, col_d2 = st.columns(2)

with col_d1:
    st.download_button(
        label="📥 Excel completo",
        data=result.workbook_bytes,
        file_name=result.output_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

with col_d2:
    json_data = {
        "calidad": quality_score,
        "registros": total_records,
        "criticos": len(critical_errors),
        "advertencias": len(warnings),
        "aprobable": len(critical_errors) == 0,
    }
    st.download_button(
        label="🔗 JSON",
        data=json.dumps(json_data, indent=2),
        file_name=f"{Path(result.output_filename).stem}.json",
        mime="application/json",
        use_container_width=True,
    )

if use_blob:
    if result.uploaded_blob_original:
        st.success(f"☁️ Original: `{result.uploaded_blob_original}`")
    if result.uploaded_blob_corrected:
        st.success(f"☁️ Corregido: `{result.uploaded_blob_corrected}`")

# Footer
st.markdown("---")
st.caption("Depurador de Horas v2.0 · Nova-TI")


# from __future__ import annotations

# import json
# import sys
# import time
# from pathlib import Path
# from typing import Dict, List, Optional

# import pandas as pd
# import plotly.express as px
# import plotly.graph_objects as go
# import streamlit as st



# ROOT_DIR = Path(__file__).resolve().parent.parent
# if str(ROOT_DIR) not in sys.path:
#     sys.path.insert(0, str(ROOT_DIR))

# from backend.batch_processor import (  # noqa: E402
#     BatchFileRequest,
#     BatchFileResult,
#     BatchProcessor,
# )
# from backend.client_profiles import ClientProfileManager  # noqa: E402
# from backend.detectors import auto_detect_profile, resolve_employee  # noqa: E402
# from backend.consolidator_integration import (  # noqa: E402
#     generate_consolidated_from_batch_results,
#     validate_batch_results_for_consolidation,
# )
# from backend.excel_parser import ParsedSheet, load_sheet_with_header  # noqa: E402
# from backend.holiday_detector import HolidayDetector  # noqa: E402
# from backend.processor import ColumnMapping, TimeSheetProcessor  # noqa: E402
# from config.settings import get_settings  # noqa: E402

# import logging  # noqa: E402

# settings = get_settings()
# logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
# logger = logging.getLogger(__name__)

# processor = TimeSheetProcessor()
# batch_processor = BatchProcessor(processor)
# profile_manager = ClientProfileManager()
# holiday_detector = HolidayDetector()

# st.set_page_config(page_title="Depurador de Horas", layout="wide")
# st.title("Depurador Automático de Registros de Horas")

# if "processor_result" not in st.session_state:
#     st.session_state["processor_result"] = None
# if "last_mapping" not in st.session_state:
#     st.session_state["last_mapping"] = None
# if "batch_results" not in st.session_state:
#     st.session_state["batch_results"] = []
# if "batch_mapping" not in st.session_state:
#     st.session_state["batch_mapping"] = None
# if "current_metadata" not in st.session_state:
#     st.session_state["current_metadata"] = None
# for key, default in {
#     "batch_selected_profile": "__manual__",
#     "batch_map_date": "",
#     "batch_map_hours": "",
#     "batch_map_description": "",
#     "batch_map_project": "",
# }.items():
#     if key not in st.session_state:
#         st.session_state[key] = default


# def render_validation_settings() -> tuple[int, int, float, bool]:
#     with st.expander("⚙️ Configuración Avanzada de Validaciones"):
#         adv_col1, adv_col2 = st.columns(2)
#         with adv_col1:
#             st.markdown("**Detección de Duplicados**")
#             similarity_threshold = st.slider(
#                 "Umbral de similitud (%)",
#                 min_value=70,
#                 max_value=100,
#                 value=90,
#                 help="Porcentaje de similitud para considerar duplicados",
#             )
#             min_duplicates = st.number_input(
#                 "Mínimo de repeticiones",
#                 min_value=2,
#                 max_value=10,
#                 value=3,
#                 help="Número mínimo de veces que debe repetirse para alertar",
#             )
#         with adv_col2:
#             st.markdown("**Validación de Horas**")
#             tolerance_factor = st.slider(
#                 "Factor de tolerancia",
#                 min_value=1.0,
#                 max_value=3.0,
#                 value=1.5,
#                 step=0.1,
#                 help="Multiplicador para rangos de horas permitidos",
#             )
#             show_time_suggestions = st.checkbox(
#                 "Mostrar sugerencias de tiempo",
#                 value=True,
#                 help="Recordatorios de rangos típicos por actividad",
#             )
#     return (
#         int(similarity_threshold),
#         int(min_duplicates),
#         float(tolerance_factor),
#         bool(show_time_suggestions),
#     )


# def render_holiday_block(
#     dataframe: pd.DataFrame,
#     date_column: Optional[str],
#     *,
#     title: str = "📅 Feriados del mes",
#     metadata: Optional[Dict[str, object]] = None,
# ) -> None:
#     info = None
#     if metadata and metadata.get("period_start") and metadata.get("period_end"):
#         info = holiday_detector.detect_period_holidays(
#             metadata.get("period_start"),
#             metadata.get("period_end"),
#         )
#     elif date_column and date_column in dataframe.columns and not dataframe.empty:
#         try:
#             info = holiday_detector.detect_month_holidays(dataframe, date_column)
#         except Exception as exc:
#             logger.warning("No se pudieron detectar feriados: %s", exc)
#             info = None
#     if info is None:
#         st.warning("No se pudieron detectar los feriados del mes.")
#         return
#     with st.expander(title):
#         if info.month is None or info.year is None:
#             st.info("No se detectaron fechas válidas en este reporte.")
#             return
#         st.write(f"**Mes detectado:** {info.month_name or info.month} {info.year}")
#         if not info.holidays:
#             st.caption("Sin feriados registrados para el mes identificado.")
#             return
#         for holiday in info.holidays:
#             st.info(f"🗓️ {holiday['date']} - {holiday['name']}")

# def get_profile_catalog() -> Dict[str, object]:
#     return {profile.client_id: profile for profile in profile_manager.list_profiles()}


# def render_single_file_mapping(
#     columns: List[str],
#     auto_profile_id: Optional[str] = None,
# ) -> tuple[ColumnMapping, Optional[str], Dict[str, object]]:
#     profiles = get_profile_catalog()
#     manual_option = "__manual_single__"
#     options = [manual_option] + sorted(profiles.keys())

#     def _format(option: str) -> str:
#         if option == manual_option:
#             return "Mapeo manual"
#         profile = profiles.get(option)
#         return profile.name if profile else option

#     default_profile = auto_profile_id or st.session_state.get("selected_profile_for_single", manual_option)
#     if default_profile not in options:
#         default_profile = manual_option
#     selected_profile = st.selectbox(
#         "Perfil de cliente (opcional)",
#         options,
#         format_func=_format,
#         index=options.index(default_profile),
#     )
#     st.session_state["selected_profile_for_single"] = selected_profile

#     if selected_profile != manual_option:
#         profile = profiles.get(selected_profile)
#         if profile is None:
#             st.warning("El perfil seleccionado no existe. Completa el mapeo manualmente.")
#         else:
#             mapping = profile.to_column_mapping()
#             if mapping:
#                 st.markdown("#### Mapeo aplicado desde perfil")
#                 for logical_name, column in profile.mapping.items():
#                     st.caption(f"- {logical_name}: {column}")
#                 return mapping, selected_profile, profile.settings
#             st.warning("El perfil no tiene columnas obligatorias. Completa el mapeo manualmente.")

#     st.markdown("#### Mapeo manual de columnas")
#     col1, col2 = st.columns(2)
#     with col1:
#         column_date = st.selectbox("📅 Columna de FECHA", columns)
#         column_hours = st.selectbox("⏱ Columna de HORAS", columns, index=min(1, len(columns) - 1))
#     with col2:
#         column_description = st.selectbox("📝 Columna de DESCRIPCIÓN", columns)
#         column_project = st.selectbox(
#             "🏷 Columna de PROYECTO (opcional)",
#             ["-- Ninguna --"] + columns,
#         )

#     mapping = ColumnMapping(
#         date=column_date,
#         hours=column_hours,
#         description=column_description,
#         project=None if column_project == "-- Ninguna --" else column_project,
#     )
#     return mapping, None, {}


# def render_batch_sidebar() -> Dict[str, object]:
#     uploaded_files = st.sidebar.file_uploader(
#         "Cargar multiples archivos",
#         type=["xlsx", "xls"],
#         accept_multiple_files=True,
#         key="batch_files",
#         help="Todos los archivos deben compartir la misma estructura de columnas.",
#     )
#     profiles = get_profile_catalog()
#     manual_option = "__manual__"
#     options = [manual_option] + sorted(profiles.keys())

#     def _format_profile(option: str) -> str:
#         if option == manual_option:
#             return "Definir mapeo manual"
#         profile = profiles.get(option)
#         return profile.name if profile else option

#     selected_profile = st.sidebar.selectbox(
#         "Cliente",
#         options=options,
#         format_func=_format_profile,
#         index=options.index(st.session_state.get("batch_selected_profile", manual_option))
#         if st.session_state.get("batch_selected_profile") in options
#         else 0,
#     )
#     st.session_state["batch_selected_profile"] = selected_profile

#     profile_obj = profiles.get(selected_profile)
#     if selected_profile != manual_option and profile_obj:
#         st.sidebar.markdown("**Mapeo detectado**")
#         for logical_name, column in profile_obj.mapping.items():
#             st.sidebar.caption(f"- {logical_name}: {column}")
#         mapping_values = {
#             "date": profile_obj.mapping.get("date", ""),
#             "hours": profile_obj.mapping.get("hours", ""),
#             "description": profile_obj.mapping.get("description", ""),
#             "project": profile_obj.mapping.get("project", ""),
#         }
#     else:
#         st.sidebar.markdown("**Define el mapeo para este lote**")
#         st.sidebar.caption("Los nombres deben coincidir exactamente con las columnas del Excel.")
#         mapping_values = {
#             "date": st.sidebar.text_input("Columna FECHA", key="batch_map_date"),
#             "hours": st.sidebar.text_input("Columna HORAS", key="batch_map_hours"),
#             "description": st.sidebar.text_input("Columna DESCRIPCIÓN", key="batch_map_description"),
#             "project": st.sidebar.text_input(
#                 "Columna PROYECTO (opcional)", key="batch_map_project"
#             ),
#         }

#     return {
#         "files": uploaded_files or [],
#         "profile_id": None if selected_profile == manual_option else selected_profile,
#         "mapping_values": mapping_values,
#         "profile_settings": profile_obj.settings if profile_obj else {},
#     }


# def auto_detect_profile_from_files(
#     files: List,
# ) -> tuple[Optional[str], Optional[Dict[str, object]]]:
#     profiles = list(get_profile_catalog().values())
#     if not files:
#         return None, None
#     sample = files[0]
#     sample_bytes = sample.getvalue()
#     parsed = load_sheet_with_header(sample_bytes)
#     metadata = getattr(parsed, "metadata", {}) or {}
#     profile_id = auto_detect_profile(sample.name, metadata, profiles)
#     return profile_id, metadata


# def render_metadata_summary(
#     metadata: Optional[Dict[str, object]],
#     *,
#     employee_info: Optional[Dict[str, Optional[str]]] = None,
#     title: str = "📄 Metadata detectada",
# ) -> None:
#     if not metadata:
#         return
#     details = []
#     if employee_info:
#         if employee_info.get("metadata"):
#             details.append(("Empleado", employee_info["metadata"]))
#         elif employee_info.get("final"):
#             details.append(("Empleado", employee_info["final"]))
#     elif metadata.get("employee"):
#         details.append(("Empleado", metadata.get("employee")))
#     if metadata.get("company"):
#         details.append(("Empresa", metadata.get("company")))
#     if metadata.get("period_start") and metadata.get("period_end"):
#         details.append(
#             (
#                 "Periodo",
#                 f"{metadata['period_start']} → {metadata['period_end']}",
#             )
#         )
#     if metadata.get("month_name"):
#         details.append(("Mes", metadata.get("month_name")))
#     if metadata.get("report_date"):
#         details.append(("Fecha del informe", metadata.get("report_date")))
#     if not details:
#         return
#     with st.expander(title, expanded=False):
#         for label, value in details:
#             st.markdown(f"**{label}:** {value}")


# def render_batch_consolidated_report(results: List[BatchFileResult]) -> None:
#     """
#     Renderiza el reporte consolidado del batch con dashboard y opción de generar Excel.

#     Esta función ahora incluye:
#     1. Dashboard visual con métricas (como antes)
#     2. Botón para generar Excel consolidado profesional
#     """
#     valid = [item for item in results if item.success and item.result is not None]
#     if len(valid) <= 1:
#         return

#     # ============================================================
#     # PARTE 1: Dashboard visual (código original mantenido)
#     # ============================================================
#     rows = []
#     for item in valid:
#         processor_result = item.result
#         metadata = processor_result.metadata or {}
#         employee_name = (
#             metadata.get("employee")
#             or metadata.get("empleado")
#             or Path(item.file_name).stem
#         )
#         summary = processor_result.summary
#         rows.append(
#             {
#                 "Empleado": employee_name,
#                 "Horas": summary.horas_totales,
#                 "Registros": summary.total_registros,
#                 "Score": summary.quality_score,
#                 "Errores": summary.total_errores,
#             }
#         )

#     df_summary = pd.DataFrame(rows)
#     st.markdown("## 📊 Reporte consolidado del equipo")

#     cols = st.columns(4)
#     cols[0].metric("Empleados", len(df_summary))
#     cols[1].metric("Horas totales", f"{df_summary['Horas'].sum():.1f} h")
#     cols[2].metric("Score promedio", f"{df_summary['Score'].mean():.0f}/100")
#     cols[3].metric("Registros", int(df_summary["Registros"].sum()))

#     df_summary["Estado"] = df_summary["Score"].apply(
#         lambda score: "✅ Excelente"
#         if score >= 90
#         else "🟢 Bueno"
#         if score >= 80
#         else "🟡 Revisar"
#         if score >= 60
#         else "🔴 Crítico"
#     )

#     st.dataframe(df_summary, use_container_width=True, hide_index=True)

#     fig = px.bar(
#         df_summary,
#         x="Empleado",
#         y="Horas",
#         color="Score",
#         color_continuous_scale="RdYlGn",
#         title="Horas por empleado",
#         labels={"Horas": "Horas registradas"},
#     )
#     st.plotly_chart(fig, use_container_width=True)

#     # ============================================================
#     # PARTE 2: Generación de Excel Consolidado (NUEVO)
#     # ============================================================
#     st.markdown("---")
#     st.markdown("### 📄 Generar Informe Consolidado Excel")

#     # Validar que los resultados sean aptos para consolidación
#     is_valid, warnings = validate_batch_results_for_consolidation(results)

#     # Mostrar warnings si existen
#     if warnings:
#         with st.expander("⚠️ Advertencias detectadas", expanded=False):
#             for warning in warnings:
#                 st.warning(warning)

#     # Determinar cliente detectado para usar como valor por defecto
#     detected_client_name = None
#     profiles_catalog = get_profile_catalog()
#     for r in results:
#         if not r.success:
#             continue
#         if r.client_id and r.client_id in profiles_catalog:
#             detected_client_name = profiles_catalog[r.client_id].name
#             break
#         company = (r.metadata or {}).get("company")
#         if company:
#             detected_client_name = str(company)
#             break
#     default_client_name = detected_client_name or "NOVA - TI"

#     # Configuración del consolidado
#     col1, col2 = st.columns([2, 1])

#     with col1:
#         cliente_nombre = st.text_input(
#             "Nombre del cliente",
#             value=default_client_name,
#             help="Nombre que aparecerá en el encabezado del consolidado",
#         )

#     with col2:
#         # Auto-generar nombre de archivo basado en el periodo
#         first_valid = next((r for r in results if r.success and r.metadata), None)
#         if first_valid:
#             mes = first_valid.metadata.get("month_name", "Unknown")
#             year = first_valid.metadata.get("year", "2025")
#             default_filename = f"Informe_TI_{default_client_name.replace(' ', '_')}_{mes}_{year}_Consolidado.xlsx"
#         else:
#             default_filename = "Informe_Consolidado.xlsx"

#         output_filename = st.text_input(
#             "Nombre del archivo",
#             value=default_filename,
#             help="Nombre del archivo Excel a generar",
#         )

#     # Botón para generar el consolidado
#     if st.button(
#         "🚀 Generar Consolidado Excel",
#         type="primary",
#         disabled=not is_valid,
#         use_container_width=True,
#     ):
#         with st.spinner("Generando reporte consolidado profesional..."):
#             try:
#                 # Generar el consolidado
#                 consolidated = generate_consolidated_from_batch_results(
#                     batch_results=results,
#                     cliente=cliente_nombre,
#                     output_filename=output_filename,
#                 )

#                 # Mostrar resumen del consolidado generado
#                 st.success("✅ Consolidado generado exitosamente")

#                 col_a, col_b, col_c = st.columns(3)
#                 col_a.metric("Consultores incluidos", consolidated.consultores_incluidos)
#                 col_b.metric(
#                     "Total a facturar", f"${consolidated.total_facturar:,.2f}"
#                 )
#                 col_c.metric("Total horas", f"{consolidated.total_horas:.1f} h")

#                 st.info(
#                     f"📅 **Periodo:** {consolidated.periodo} · "
#                     f"**Días laborables:** {consolidated.dias_laborables}"
#                 )

#                 # Botón de descarga
#                 st.download_button(
#                     label="⬇️ Descargar Consolidado Excel",
#                     data=consolidated.workbook_bytes,
#                     file_name=consolidated.output_filename,
#                     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#                     use_container_width=True,
#                 )

#                 # Mostrar preview del contenido
#                 with st.expander("📋 Vista previa del contenido", expanded=False):
#                     st.markdown("**Estructura del archivo generado:**")
#                     st.markdown(
#                         f"""
#                         - **Hoja 1: Resumen** - Tabla con {consolidated.consultores_incluidos} consultores
#                         - **Hojas 2-{consolidated.consultores_incluidos + 1}:** Reportes individuales por consultor

#                         **Información incluida en la hoja Resumen:**
#                         - Cliente: {cliente_nombre}
#                         - Periodo: {consolidated.periodo}
#                         - Días laborables: {consolidated.dias_laborables}
#                         - Total a facturar: ${consolidated.total_facturar:,.2f}

#                         **Cálculos realizados por consultor:**
#                         - Días laborados (fechas únicas con actividades)
#                         - Total horas normales (HN)
#                         - Total horas extras
#                         - Valor tarifa según cargo (Senior/Semisenior/Junior)
#                         - Cálculos de facturación
#                         """
#                     )

#             except ValueError as ve:
#                 st.error(f"❌ Error de validación: {ve}")
#             except Exception as exc:
#                 st.error(f"❌ Error generando consolidado: {exc}")
#                 logger.exception("Error generando consolidado: %s", exc)
                
# def build_mapping_from_values(values: Dict[str, str]) -> Optional[ColumnMapping]:
#     date_col = values.get("date", "").strip()
#     hours_col = values.get("hours", "").strip()
#     description_col = values.get("description", "").strip()
#     project_col = values.get("project", "").strip()
#     if not date_col or not hours_col or not description_col:
#         return None
#     return ColumnMapping(
#         date=date_col,
#         hours=hours_col,
#         description=description_col,
#         project=project_col or None,
#     )




# def run_batch_mode(
#     *,
#     batch_state: Dict[str, object],
#     correct_spelling: bool,
#     employee_role: str,
# ) -> None:
#     st.subheader("Procesamiento por lotes")
#     similarity_threshold, min_duplicates, tolerance_factor, show_time_suggestions = render_validation_settings()

#     uploaded_files: List = batch_state.get("files") or []
#     if not uploaded_files:
#         st.info("Selecciona uno o más archivos en la barra lateral para comenzar.")
#         if show_time_suggestions:
#             st.caption(
#                 "Referencias: Daily ~0.25h · Reuniones 0.25-3h · Desarrollo 1-8h · Code review 0.25-2h."
#             )
#         return

#     profiles_catalog = get_profile_catalog()
#     profile_id = batch_state.get("profile_id")
#     profile_obj = profiles_catalog.get(profile_id) if profile_id else None
#     preview_metadata: Optional[Dict[str, object]] = None

#     if profile_obj is None:
#         detected_profile_id, preview_metadata = auto_detect_profile_from_files(uploaded_files)
#         if detected_profile_id and detected_profile_id in profiles_catalog:
#             profile_obj = profiles_catalog[detected_profile_id]
#             profile_id = detected_profile_id
#             st.session_state["batch_selected_profile"] = detected_profile_id
#             st.success(f"Cliente detectado automáticamente: {profile_obj.name}")
#         elif preview_metadata:
#             employee_info = resolve_employee(preview_metadata, uploaded_files[0].name)
#             render_metadata_summary(preview_metadata, employee_info=employee_info, title="📄 Metadata del primer archivo")

#     if profile_obj is None:
#         mapping = build_mapping_from_values(batch_state.get("mapping_values", {}))
#         if mapping is None:
#             st.warning("Define columnas de Fecha, Horas y Descripción antes de procesar el lote.")
#             return
#         profile_settings = batch_state.get("profile_settings") or {}
#         header_keywords = [
#             value.strip()
#             for value in (batch_state.get("mapping_values") or {}).values()
#             if value and value.strip()
#         ]
#     else:
#         mapping = profile_obj.to_column_mapping()
#         if mapping is None:
#             st.error("El perfil seleccionado no tiene columnas obligatorias definidas.")
#             return
#         profile_settings = profile_obj.settings
#         header_keywords = [value for value in profile_obj.mapping.values() if value]
#         if preview_metadata is None and uploaded_files:
#             _, preview_metadata = auto_detect_profile_from_files(uploaded_files)
#         if preview_metadata:
#             employee_info = resolve_employee(preview_metadata, uploaded_files[0].name)
#             render_metadata_summary(preview_metadata, employee_info=employee_info, title="📄 Metadata del primer archivo")

#     duplicate_threshold = int(
#         profile_settings.get("duplicate_similarity_threshold", similarity_threshold)
#     )
#     min_duplicates_setting = int(
#         profile_settings.get("duplicate_min_occurrences", min_duplicates)
#     )
#     hours_tolerance = float(
#         profile_settings.get("hours_tolerance_factor", tolerance_factor)
#     )
#     role_to_use = str(profile_settings.get("rol_default") or profile_settings.get("role") or employee_role)
#     spelling_flag = bool(profile_settings.get("correct_spelling", correct_spelling))

#     requests: List[BatchFileRequest] = []
#     for file_obj in uploaded_files:
#         file_name = file_obj.name or "reporte.xlsx"
#         requests.append(
#             BatchFileRequest(
#                 file_name=file_name,
#                 file_bytes=file_obj.getvalue(),
#                 mapping=mapping,
#                 client_id=profile_id,
#                 header_keywords=header_keywords,
#                 profile_settings=profile_settings,
#                 processor_kwargs={
#                     "correct_spelling": spelling_flag,
#                     "role": role_to_use,
#                     "project_name": mapping.project or "No especificado",
#                     "duplicate_similarity_threshold": duplicate_threshold,
#                     "duplicate_min_occurrences": min_duplicates_setting,
#                     "hours_tolerance_factor": hours_tolerance,
#                 },
#             )
#         )

#     process_clicked = st.button("Procesar lote completo", type="primary")
#     if process_clicked:
#         progress_placeholder = st.empty()
#         progress_bar = st.progress(0)

#         def update_progress(current: int, total: int, message: str) -> None:
#             percent = 0 if total == 0 else int((current / total) * 100)
#             progress_placeholder.info(f"{message} ({current}/{total})")
#             progress_bar.progress(min(percent, 100))

#         results = batch_processor.process_batch(
#             requests,
#             progress_callback=update_progress,
#         )
#         progress_placeholder.success("Procesamiento por lotes finalizado.")
#         progress_bar.empty()
#         st.session_state["batch_results"] = results
#         st.session_state["batch_mapping"] = mapping

#     batch_results: List[BatchFileResult] = st.session_state.get("batch_results", [])
#     mapping_for_display: Optional[ColumnMapping] = st.session_state.get("batch_mapping") or mapping
#     if not batch_results:
#         st.info("Aún no hay resultados procesados. Presiona el botón para iniciar el lote.")
#         return

#     success_count = sum(1 for result in batch_results if result.success)
#     st.markdown(
#         f"### Resultados del lote ({success_count}/{len(batch_results)} completados)"
#     )

#     for result in batch_results:
#         container = st.container()
#         if result.success and result.result:
#             summary = result.result.summary
#             metadata = result.result.metadata or {}
#             container.success(
#                 f"{result.file_name} procesado (hoja: {result.sheet_name or 'auto'})"
#             )
#             container.caption(
#                 f"Header detectado en fila {result.header_row + 1 if result.header_row is not None else 'auto'}"
#             )
#             employee_info = resolve_employee(metadata, result.file_name)
#             render_metadata_summary(metadata, employee_info=employee_info, title=f"📄 Metadata - {result.file_name}")
#             metrics = container.columns(4)
#             metrics[0].metric("Registros", summary.total_registros)
#             metrics[1].metric("Horas totales", f"{summary.horas_totales:.1f} h")
#             metrics[2].metric("Errores críticos", summary.errores_criticos)
#             metrics[3].metric("Score calidad", f"{summary.quality_score:.0f}%")

#             download_cols = container.columns(2)
#             download_cols[0].download_button(
#                 label="⬇️ Excel corregido",
#                 data=result.result.workbook_bytes,
#                 file_name=result.result.output_filename,
#                 mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#             )
#             summary_json = json.dumps(
#                 {
#                     "calidad": summary.quality_score,
#                     "registros": summary.total_registros,
#                     "metadata_removida": summary.metadata_removidas,
#                     "criticos": summary.errores_criticos,
#                     "advertencias": summary.errores_advertencia,
#                 },
#                 indent=2,
#             )
#             download_cols[1].download_button(
#                 label="⬇️ JSON resumen",
#                 data=summary_json,
#                 file_name=f"{Path(result.result.output_filename).stem}.json",
#                 mime="application/json",
#             )

#             with container.expander("Errores detectados"):
#                 errors_df = result.result.errors_dataframe
#                 if errors_df.empty:
#                     st.success("Sin errores reportados.")
#                 else:
#                     st.dataframe(
#                         errors_df,
#                         use_container_width=True,
#                         hide_index=True,
#                     )

#             if mapping_for_display:
#                 render_holiday_block(
#                     result.result.corrected_dataframe,
#                     mapping_for_display.date,
#                     title=f"📅 Feriados - {result.file_name}",
#                     metadata=metadata,
#                 )
#         else:
#             container.error(f"No se pudo procesar {result.file_name}")
#             if result.error:
#                 container.write(result.error)

#     render_batch_consolidated_report(batch_results)

#     if show_time_suggestions:
#         st.caption(
#             "Referencias: Daily ~0.25h · Reuniones 0.25-3h · Desarrollo 1-8h · Code review 0.25-2h."
#         )


# st.sidebar.header("⚙️ Configuración")
# processing_mode = st.sidebar.radio(
#     "Modo de procesamiento",
#     ["Individual", "Por lotes"],
#     index=0,
# )
# correct_spelling = st.sidebar.checkbox(
#     "Aplicar corrección ortográfica (LLM)", value=True
# )
# employee_role = st.sidebar.selectbox(
#     "Rol del empleado para validación",
#     ["Desconocido", "Developer", "QA", "DevOps", "Project Manager", "Otro"],
# )

# use_blob = False
# blob_original = ""
# blob_corregido = ""
# batch_sidebar_state: Optional[Dict[str, object]] = None

# if processing_mode == "Individual":
#     st.sidebar.header("Opciones de almacenamiento (Azure Blob)")
#     use_blob = st.sidebar.checkbox("Usar Azure Blob Storage", value=False)
#     blob_original = st.sidebar.text_input(
#         "Nombre blob (original)",
#         help="Opcional: guarda una copia del archivo original.",
#     )
#     blob_corregido = st.sidebar.text_input(
#         "Nombre blob (corregido)",
#         help="Nombre con el que se subirá el archivo depurado.",
#     )
# else:
#     st.sidebar.header("Perfiles y mapeo")
#     batch_sidebar_state = render_batch_sidebar()
#     st.sidebar.caption("Personaliza el mapeo por cliente antes de procesar el lote.")

# if processing_mode == "Por lotes":
#     if batch_sidebar_state is None:
#         st.error("No se pudo cargar la configuración del modo por lotes.")
#     else:
#         run_batch_mode(
#             batch_state=batch_sidebar_state,
#             correct_spelling=correct_spelling,
#             employee_role=employee_role,
#         )
#     st.stop()


# uploaded_file = st.file_uploader("Sube tu Excel de registro", type=["xlsx", "xls"])
# if not uploaded_file:
#     st.info("Carga un archivo Excel para comenzar.")
#     st.stop()

# source_bytes = uploaded_file.getvalue()
# source_name = uploaded_file.name or "reporte.xlsx"


# @st.cache_data(show_spinner=False)
# def cache_parsed_sheet_auto(file_bytes: bytes) -> ParsedSheet:
#     return load_sheet_with_header(file_bytes)


# parsed_sheet = cache_parsed_sheet_auto(source_bytes)
# dataframe = parsed_sheet.dataframe.copy()
# columns = [str(col) for col in dataframe.columns]
# if not columns:
#     st.error("No se detectaron columnas en la hoja auto-detectada.")
#     st.stop()

# st.success(f"Hoja auto-detectada: '{parsed_sheet.sheet_name}'")
# st.caption(f"Encabezado detectado en la fila {parsed_sheet.header_row + 1}")
# st.markdown("#### Vista previa de la hoja (primeras 15 filas)")
# st.dataframe(dataframe.head(15))

# metadata = getattr(parsed_sheet, "metadata", {}) or {}
# st.session_state["current_metadata"] = metadata
# employee_context = resolve_employee(metadata, source_name)
# render_metadata_summary(metadata, employee_info=employee_context)
# profiles_catalog = list(get_profile_catalog().values())
# auto_profile_id = auto_detect_profile(source_name, metadata, profiles_catalog)
# if auto_profile_id:
#     profile_obj = next((p for p in profiles_catalog if p.client_id == auto_profile_id), None)
#     if profile_obj:
#         st.info(f"Cliente detectado automáticamente: {profile_obj.name}")

# mapping, selected_profile_id, profile_settings = render_single_file_mapping(columns, auto_profile_id)
# st.session_state["last_mapping"] = mapping

# (
#     similarity_threshold,
#     min_duplicates,
#     tolerance_factor,
#     show_time_suggestions,
# ) = render_validation_settings()

# duplicate_threshold = int(
#     profile_settings.get("duplicate_similarity_threshold", similarity_threshold)
# )
# min_duplicates_effective = int(
#     profile_settings.get("duplicate_min_occurrences", min_duplicates)
# )
# hours_tolerance_effective = float(
#     profile_settings.get("hours_tolerance_factor", tolerance_factor)
# )
# effective_role = str(
#     profile_settings.get("rol_default") or profile_settings.get("role") or employee_role
# )
# effective_spelling = bool(profile_settings.get("correct_spelling", correct_spelling))

# st.write("")
# process_clicked = st.button("✅ Validar y Depurar", type="primary")

# if process_clicked:
#     st.session_state["processor_result"] = None
#     progress_text = st.empty()
#     progress_bar = st.progress(0)

#     def announce(text: str, value: float) -> None:
#         progress_text.info(text)
#         progress_bar.progress(int(value * 100))
#         time.sleep(0.1)

#     announce("🔍 Analizando estructura del archivo...", 0.15)
#     announce("🧹 Limpiando metadata y columnas extras...", 0.35)
#     announce("📅 Validando fechas, feriados y horas...", 0.55)
#     announce("🤖 Preparando correcciones con IA...", 0.75)

#     try:
#         result = processor.process_parsed_sheet(
#             parsed_sheet=parsed_sheet,
#             mapping=mapping,
#             source_name=source_name,
#             original_excel_bytes=source_bytes if use_blob else None,
#             correct_spelling=effective_spelling,
#             upload_to_blob=use_blob,
#             blob_name_original=blob_original or None,
#             blob_name_corrected=blob_corregido or None,
#             role=effective_role,
#             project_name=mapping.project or "No especificado",
#             duplicate_similarity_threshold=int(duplicate_threshold),
#             duplicate_min_occurrences=int(min_duplicates_effective),
#             hours_tolerance_factor=float(hours_tolerance_effective),
#             client_profile_id=selected_profile_id or auto_profile_id,
#             client_profile_settings=profile_settings,
#         )
#     except Exception as exc:
#         progress_bar.empty()
#         progress_text.empty()
#         logger.exception("Error inesperado durante el procesamiento: %s", exc)
#         st.error(f"Ocurrió un error durante el procesamiento: {exc}")
#         st.stop()
#     else:
#         announce("✅ Finalizando y generando reportes...", 1.0)
#         progress_text.success("🎉 ¡Procesamiento completado!")
#         progress_bar.empty()
#         st.session_state["processor_result"] = result

# result = st.session_state.get("processor_result")
# if result is None:
#     st.stop()

# st.markdown("---")
# st.markdown("# 📊 Resultados de Validación")

# errors = result.validation_errors
# errors_df = result.errors_dataframe
# corrected_df = result.corrected_dataframe
# summary = result.summary

# critical_errors = [
#     err for err in errors if err["tipo_error"] in {"horas_incorrectas", "fin_semana", "feriado", "horas_excesivas", "horas_muy_bajas", "fecha_invalida"}
# ]
# warnings = [err for err in errors if err["tipo_error"] not in {"horas_incorrectas", "fin_semana", "feriado", "horas_excesivas", "horas_muy_bajas", "fecha_invalida"}]

# total_records = summary.total_registros
# removed_count = summary.metadata_removidas
# total_hours = summary.horas_totales
# quality_score = summary.quality_score

# with st.container():
#     gauge_col, metrics_col = st.columns([1.1, 2])
#     with gauge_col:
#         fig_gauge = go.Figure(
#             go.Indicator(
#                 mode="gauge+number+delta",
#                 value=quality_score,
#                 delta={"reference": 80},
#                 title={"text": "Score de Calidad", "font": {"size": 20}},
#                 gauge={
#                     "axis": {"range": [0, 100]},
#                     "bar": {"color": "#2563eb"},
#                     "steps": [
#                         {"range": [0, 50], "color": "#fecaca"},
#                         {"range": [50, 80], "color": "#fde68a"},
#                         {"range": [80, 100], "color": "#bbf7d0"},
#                     ],
#                     "threshold": {"value": 80, "line": {"color": "#ef4444", "width": 4}},
#                 },
#             )
#         )
#         fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20))
#         st.plotly_chart(fig_gauge, use_container_width=True)

#     with metrics_col:
#         cols = st.columns(4)
#         cols[0].metric(
#             "📈 Score (Δ vs 80%)",
#             f"{quality_score:.0f}%",
#             f"{quality_score - 80:+.0f} pts",
#             delta_color="inverse" if quality_score < 80 else "normal",
#         )
#         cols[1].metric(
#             "📝 Registros procesados",
#             total_records,
#             f"{removed_count} metadata removida" if removed_count else "Sin metadata",
#         )
#         cols[2].metric(
#             "⏰ Horas totales",
#             f"{total_hours:.1f} h",
#             f"{total_hours / 8:.1f} días laborales",
#         )
#         cols[3].metric(
#             "🚨 Errores críticos",
#             len(critical_errors),
#             "Bloquean aprobación" if critical_errors else "Ninguno",
#             delta_color="inverse",
#         )
#         if summary.role_coherence_score is not None:
#             st.caption(
#                 f"🎯 Coherencia de rol: **{summary.role_coherence_score:.1f}%** "
#                 "de las actividades son coherentes con el rol declarado."
#             )

# result_metadata = result.metadata or st.session_state.get("current_metadata")
# employee_details = resolve_employee(result_metadata or {}, source_name)
# render_metadata_summary(
#     result_metadata,
#     employee_info=employee_details,
#     title="📄 Metadata del archivo procesado",
# )

# active_mapping = st.session_state.get("last_mapping")
# if active_mapping:
#     render_holiday_block(
#         corrected_df,
#         active_mapping.date,
#         metadata=result_metadata,
#     )

# if show_time_suggestions:
#     st.caption(
#         "Referencias: Daily ≈0.25h · Reuniones 0.25-3h · Desarrollo 1-8h · Code review 0.25-2h."
#     )

# st.markdown("---")
# st.markdown("## 🔍 Detalle de Validaciones")

# tab1, tab2, tab3, tab4, tab5 = st.tabs([
#     f"🚨 Críticos ({len(critical_errors)})",
#     f"⚠️ Advertencias ({len(warnings)})",
#     "✅ Correcciones aplicadas",
#     "📊 Análisis visual",
#     "🎯 Análisis de Rol",
# ])

# with tab1:
#     if critical_errors:
#         st.error("⛔ Errores que BLOQUEAN la aprobación del timesheet.")
#         critical_by_type: Dict[str, List[ValidationIssue]] = {}
#         for err in critical_errors:
#             critical_by_type.setdefault(err["tipo_error"], []).append(err)
#         for tipo, error_list in critical_by_type.items():
#             with st.expander(f"🔴 {tipo.replace('_', ' ').title()} - {len(error_list)} casos", expanded=True):
#                 df_err = pd.DataFrame(error_list)
#                 st.dataframe(
#                     df_err[["fila", "fecha", "descripcion", "valor_original"]],
#                     use_container_width=True,
#                     hide_index=True,
#                 )
#     else:
#         st.success("✅ No hay errores críticos. El timesheet cumple con los requisitos obligatorios.")

# with tab2:
#     if warnings:
#         st.warning(f"💡 {len(warnings)} sugerencias de mejora detectadas.")
#         df_warnings = pd.DataFrame(warnings)
#         st.dataframe(
#             df_warnings[["fila", "fecha", "tipo_error", "descripcion"]],
#             use_container_width=True,
#             hide_index=True,
#         )
#     else:
#         st.success("✅ No hay advertencias.")

# with tab3:
#     if result.corrections_log:
#         st.info(f"🤖 {len(result.corrections_log)} correcciones ortográficas aplicadas automáticamente.")
#         st.markdown("**Ejemplos:**")
#         for correction in result.corrections_log[:5]:
#             col_a, col_b = st.columns(2)
#             with col_a:
#                 st.text("❌ Original:")
#                 st.code(correction.original_text)
#             with col_b:
#                 st.text("✅ Corregido:")
#                 st.code(correction.corrected_text)
#             st.divider()
#         if len(result.corrections_log) > 5:
#             st.caption(f"+ {len(result.corrections_log) - 5} correcciones adicionales (ver Excel descargado).")
#     else:
#         st.success("✅ No se requirieron correcciones.")

# with tab4:
#     if errors_df.empty:
#         st.success("🎉 Timesheet perfecto. No se detectaron errores.")
#     else:
#         error_counts = errors_df["tipo_error"].value_counts().reset_index()
#         error_counts.columns = ["tipo", "cantidad"]
#         fig = px.bar(
#             error_counts,
#             x="cantidad",
#             y="tipo",
#             orientation="h",
#             title="Errores por tipo",
#             color="cantidad",
#             color_continuous_scale=["#22c55e", "#eab308", "#ef4444"],
#         )
#         fig.update_layout(showlegend=False, height=400)
#         st.plotly_chart(fig, use_container_width=True)

#         errors_df["fecha_dt"] = pd.to_datetime(
#             errors_df["fecha"], errors="coerce", dayfirst=True, format="%Y-%m-%d"
#         )
#         timeline = errors_df.dropna(subset=["fecha_dt"]).groupby("fecha_dt").size().reset_index(name="cantidad")
#         if not timeline.empty:
#             fig_line = px.line(
#                 timeline,
#                 x="fecha_dt",
#                 y="cantidad",
#                 title="Errores por día",
#                 markers=True,
#                 labels={"fecha_dt": "Fecha", "cantidad": "Errores"},
#             )
#             st.plotly_chart(fig_line, use_container_width=True)

# with tab5:
#     if summary.role_coherence_score is None:
#         st.info("No se evaluó el rol (selecciona un rol válido en la barra lateral).")
#     else:
#         st.metric("Coherencia general", f"{summary.role_coherence_score:.1f}%")
#         role_details = summary.role_validation_details
#         if role_details:
#             st.dataframe(
#                 pd.DataFrame(role_details),
#                 use_container_width=True,
#                 hide_index=True,
#             )
#         else:
#             st.success("Todas las actividades evaluadas son coherentes con el rol declarado.")

# st.markdown("---")
# st.markdown("## 🤖 Resumen Ejecutivo")

# if summary.ai_summary:
#     acciones = summary.ai_summary.get("acciones") or []
#     acciones_md = "\n".join(f"- {accion}" for accion in acciones)
#     st.info(
#         f"{summary.ai_summary.get('diagnostico', '')}\n\n"
#         f"✅ **Recomendaciones:**\n{acciones_md}\n\n"
#         f"⏱️ **Tiempo estimado:** {summary.ai_summary.get('tiempo_estimado', 'No disponible')}"
#     )
# else:
#     st.warning("No se pudo generar el resumen inteligente. Revise el reporte manualmente.")

# if not critical_errors:
#     st.success("✅ TIMESHEET APROBABLE - No se detectan bloqueadores.")
# else:
#     st.error(f"🚫 REQUIERE CORRECCIONES - {len(critical_errors)} errores críticos deben resolverse.")

# st.markdown("---")
# st.markdown("## 💾 Descargar Resultados")

# col_d1, col_d2 = st.columns(2)
# col_d1.download_button(
#     label="📥 Descargar Excel completo",
#     data=result.workbook_bytes,
#     file_name=result.output_filename,
#     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#     help="Incluye: Resumen Ejecutivo, Datos corregidos y Reporte de Errores.",
# )

# json_data = {
#     "calidad": quality_score,
#     "registros": total_records,
#     "metadata_removida": removed_count,
#     "criticos": len(critical_errors),
#     "advertencias": len(warnings),
#     "aprobable": len(critical_errors) == 0,
# }
# col_d2.download_button(
#     label="🔗 Exportar JSON",
#     data=json.dumps(json_data, indent=2),
#     file_name=f"{Path(result.output_filename).stem}.json",
#     mime="application/json",
# )

# if use_blob:
#     if result.uploaded_blob_original:
#         st.success(f"Archivo original subido como `{result.uploaded_blob_original}`.")
#     if result.uploaded_blob_corrected:
#         st.success(f"Archivo corregido subido como `{result.uploaded_blob_corrected}`.")
#     if not result.uploaded_blob_corrected and blob_corregido:
#         st.warning("No se pudo subir el archivo corregido a Azure Blob Storage.")




