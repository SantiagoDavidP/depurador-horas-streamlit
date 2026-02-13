from __future__ import annotations

# =============================================================================
# PATH SETUP (DEBE IR PRIMERO)
# =============================================================================
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# =============================================================================
# STANDARD LIB
# =============================================================================
import json
import logging
import time
import zipfile
from io import BytesIO
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

# =============================================================================
# THIRD-PARTY
# =============================================================================
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# =============================================================================
# BACKEND IMPORTS
# =============================================================================
from backend.excel_parser import (
    infer_column_mapping,
    load_sheet_with_header,
    load_multiple_sheets,
    ParsedSheet,
)
from backend.models import ColumnMapping
from backend.processor import TimeSheetProcessor
from backend.azure_ad_auth import require_authentication, render_user_info_sidebar
from backend.batch_processor import BatchFileRequest, BatchFileResult, BatchProcessor
from backend.client_profiles import ClientProfileManager
from backend.consolidator_integration import (
    generate_consolidated_from_batch_results,
    generate_individual_business_it_excel,
    validate_batch_results_for_consolidation,
)
from backend.collaborator_rates import get_collaborator_rates_manager
from backend.detectors import auto_detect_profile, resolve_employee
from backend.holiday_detector import HolidayDetector
from config.settings import get_settings

# =============================================================================
# FRONTEND THEME IMPORTS
# =============================================================================
from frontend.streamlit_ui_theme import (
    apply_theme,
    get_theme,
    render_divider,
    render_empty_state,
    render_header,
    render_info_grid,
    render_section_header,
    render_status_card,
    render_theme_toggle,
)

# =============================================================================
# INITIALIZATION
# =============================================================================
settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

processor = TimeSheetProcessor()
batch_processor = BatchProcessor(processor)
profile_manager = ClientProfileManager()
holiday_detector = HolidayDetector()

# =============================================================================
# STREAMLIT PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Depurador de Horas | Nova-TI",
    page_icon="⏱️",
    layout="centered",
    initial_sidebar_state="expanded",
)
apply_theme()

# =============================================================================
# AUTH CHECK
# =============================================================================
authenticated, user_info = require_authentication()
if not authenticated:
    st.stop()

# =============================================================================
# SESSION STATE DEFAULTS
# =============================================================================
def _init_state():
    defaults = {
        "processor_result": None,
        "last_mapping": None,
        "batch_results": [],
        "batch_mapping": None,
        "current_metadata": None,
        "consolidated_result": None,
        "batch_results_accumulator": None,
        "current_file_signature": None,
        "selected_profile_for_single": "__manual_single__",
        "batch_selected_profile": "__manual__",
        "batch_map_date": "",
        "batch_map_hours": "",
        "batch_map_description": "",
        "batch_map_project": "",
        "uploaded_files_cache": None,
        "batch_files_signature": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()

if "processing_mode" not in st.session_state:
    st.session_state["processing_mode"] = "Individual"


# =============================================================================
# HELPERS (SANITIZE + THEME)
# =============================================================================
def sanitize_filename(filename: str) -> str:
    import re

    if not filename:
        return "archivo.xlsx"

    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)
    safe_name = Path(safe_name).name

    if len(safe_name) > 200:
        parts = safe_name.rsplit(".", 1)
        safe_name = (parts[0][:190] + "." + parts[1]) if len(parts) == 2 else safe_name[:200]

    if not safe_name or safe_name == ".":
        safe_name = "archivo.xlsx"
    return safe_name


def sanitize_text_input(text: str, max_length: int = 100) -> str:
    if not text:
        return ""
    sanitized = " ".join(str(text).split())
    return sanitized[:max_length]


def get_plotly_theme() -> Dict[str, str]:
    is_dark = get_theme() == "dark"
    if is_dark:
        return {
            "bg": "rgba(0,0,0,0)",
            "paper_bg": "rgba(0,0,0,0)",
            "font_color": "#a1a1aa",
            "grid_color": "#27272a",
        }
    return {
        "bg": "rgba(0,0,0,0)",
        "paper_bg": "rgba(0,0,0,0)",
        "font_color": "#475569",
        "grid_color": "#e2e8f0",
    }


_ERROR_PRIORITY = [
    "completitud",
    "fecha_fuera_periodo",
    "fecha_invalida",
    "fin_semana",
    "feriado",
    "horas_faltantes",
    "horas_incorrectas",
    "horas_excesivas",
    "horas_muy_bajas",
    "duplicado_exacto",
    "duplicado_similar",
    "descripcion_repetida",
    "campo_vacio",
]
_ERROR_PRIORITY_INDEX = {t: i for i, t in enumerate(_ERROR_PRIORITY)}


def sort_errors_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    sorted_df = df.copy()
    sorted_df["__severity"] = sorted_df["tipo_error"].astype(str).apply(
        lambda t: _ERROR_PRIORITY_INDEX.get(t, len(_ERROR_PRIORITY))
    )
    sorted_df["__order"] = range(len(sorted_df))
    sorted_df = sorted_df.sort_values(["__severity", "__order"])
    return sorted_df.drop(columns=["__severity", "__order"])


def detect_area_from_names(names: List[str]) -> Optional[str]:
    try:
        manager = get_collaborator_rates_manager()
        cd_count = 0
        ti_count = 0
        for name in names:
            if not name:
                continue
            collab = manager.find_collaborator(str(name))
            if collab and collab.cargo:
                cd_count += 1
            else:
                ti_count += 1
        if cd_count or ti_count:
            return "CD" if cd_count > ti_count else "TI"
    except Exception:
        return None
    return None


def is_baninter_result(result: BatchFileResult) -> bool:
    if result.client_id == "cliente_talent":
        return True
    if result and result.result and getattr(result.result, "client_profile_id", None) == "cliente_talent":
        return True
    metadata = (result.metadata or {}) if result else {}
    if result and result.result and result.result.metadata:
        metadata = {**metadata, **(result.result.metadata or {})}
    company = str(metadata.get("company", "")).lower()
    if "baninter" in company or "banco internacional" in company:
        return True
    filename = str(getattr(result, "file_name", "") or "").lower()
    if "banco internacional" in filename:
        return True
    # Plantilla clásica BANINTER
    if "resumen actividades recursos" in filename:
        return True
    return False


# =============================================================================
# UI BLOCKS
# =============================================================================
def get_profile_catalog() -> Dict[str, object]:
    return {p.client_id: p for p in profile_manager.list_profiles()}


def render_metadata_summary(
    metadata: Optional[Dict[str, object]],
    *,
    employee_info: Optional[Dict[str, Optional[str]]] = None,
    title: str = "Metadata",
) -> None:
    if not metadata:
        return

    details = []
    if employee_info:
        if employee_info.get("metadata"):
            details.append(("Empleado", employee_info["metadata"]))
        elif employee_info.get("final"):
            details.append(("Empleado", employee_info["final"]))
    if metadata.get("company"):
        details.append(("Empresa", metadata.get("company")))
    if metadata.get("period_start") and metadata.get("period_end"):
        details.append(("Periodo", f"{metadata['period_start']} -> {metadata['period_end']}"))
    if metadata.get("month_name"):
        details.append(("Mes", metadata.get("month_name")))

    if not details:
        return

    with st.expander(title, expanded=False):
        render_info_grid(details)


def render_baninter_report(report: Optional[Dict[str, object]]) -> None:
    if not report:
        return
    missing_cols = report.get("missing_optional_columns") or []
    filled_fecha = report.get("filled_fecha", 0)
    filled_proyecto = report.get("filled_proyecto", 0)
    filled_fase = report.get("filled_fase", 0)
    valid_before = report.get("valid_before", 0)
    valid_after = report.get("valid_after", 0)
    coverage_before = report.get("coverage_before", 0.0)
    coverage_after = report.get("coverage_after", 0.0)
    warnings = report.get("warnings") or []

    with st.expander("BANINTER - Imputaciones", expanded=False):
        missing_text = ", ".join(missing_cols) if missing_cols else "Ninguna"
        st.markdown(f"**Columnas de interes faltantes:** {missing_text}")
        st.markdown(f"**Imputaciones:** Fecha={filled_fecha}, Proyecto={filled_proyecto}, Fase={filled_fase}")
        st.markdown(
            f"**Filas validas:** antes={valid_before} ({coverage_before:.0%}), despues={valid_after} ({coverage_after:.0%})"
        )
        if warnings:
            for w in warnings:
                st.warning(w)


def build_baninter_individuals_zip(batch_results: List[BatchFileResult]) -> Optional[bytes]:
    buffer = BytesIO()
    written = 0
    used_names = set()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, res in enumerate(batch_results):
            if not (res.success and res.result):
                continue
            try:
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
            except Exception as exc:
                logger.warning("No se pudo generar individual BANINTER para %s: %s", res.file_name, exc)
                continue
    if written == 0:
        return None
    buffer.seek(0)
    return buffer.getvalue()


def render_holiday_block(
    dataframe: pd.DataFrame,
    date_column: Optional[str],
    *,
    title: str = "📅 Feriados del mes",
    metadata: Optional[Dict[str, object]] = None,
) -> None:
    info = None

    # 🔹 PRIORIDAD 1: Datos reales del DataFrame (SIEMPRE más confiable)
    if date_column and date_column in dataframe.columns and not dataframe.empty:
        try:
            info = holiday_detector.detect_month_holidays(dataframe, date_column)
            logger.info(f"✅ Feriados detectados desde datos reales: {info.month_name} {info.year}")
        except Exception as exc:
            logger.warning(f"⚠️ No se pudieron detectar feriados desde datos: {exc}")
            
            # 🔹 PRIORIDAD 2: Metadata como fallback SOLO si los datos fallan
            if metadata and metadata.get("period_start") and metadata.get("period_end"):
                try:
                    info = holiday_detector.detect_period_holidays(
                        metadata.get("period_start"),
                        metadata.get("period_end")
                    )
                    logger.info(f"✅ Feriados detectados desde metadata (fallback): {info.month_name} {info.year}")
                except Exception as exc2:
                    logger.warning(f"⚠️ Metadata también falló: {exc2}")
                    return
            else:
                return
    
    # Si NO hay columna de fecha, pero SÍ hay metadata válida
    elif metadata and metadata.get("period_start") and metadata.get("period_end"):
        try:
            info = holiday_detector.detect_period_holidays(
                metadata.get("period_start"),
                metadata.get("period_end")
            )
            logger.info(f"✅ Feriados detectados desde metadata: {info.month_name} {info.year}")
        except Exception as exc:
            logger.warning(f"⚠️ Error usando metadata: {exc}")
            return
    else:
        # No hay suficiente información
        return

    if not info or info.month is None or info.year is None:
        return

    # Preparar la etiqueta del mes
    month_label = info.month_name or str(info.month)
    if str(info.year) not in month_label:
        month_label = f"{month_label} {info.year}"

    # =========================================================
    # 🎨 UI: Usar st.expander para hacerlo desplegable
    # =========================================================
    with st.expander(title, expanded=False):
        st.markdown(f"**Mes analizado:** {month_label}")

        if not info.holidays:
            st.caption("✅ Sin feriados registrados para este mes.")
            return

        for holiday in info.holidays:
            st.markdown(f"🗓️ **{holiday['date']}** — {holiday['name']}")


def render_validation_settings() -> Tuple[int, int, float, bool]:
    with st.expander("⚙️ Configuración Avanzada", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**🔍 Detección de duplicados**")
            similarity_threshold = st.slider(
                "Umbral de similitud",
                min_value=70,
                max_value=100,
                value=90,
                format="%d%%",
            )
            min_duplicates = st.number_input(
                "Mínimo de repeticiones",
                min_value=1,
                max_value=1000,
                value=3,
                help="Cuántas repeticiones antes de marcarlo como posible duplicado",
            )

        with col2:
            st.markdown("**⏰ Validación de horas**")
            tolerance_factor = st.slider(
                "Factor de tolerancia",
                min_value=1.0,
                max_value=3.0,
                value=1.5,
                step=0.1,
            )
            show_time_suggestions = st.checkbox("Mostrar referencias de tiempo", value=True)

    st.session_state["show_time_suggestions"] = show_time_suggestions
    return int(similarity_threshold), int(min_duplicates), float(tolerance_factor), bool(show_time_suggestions)


def build_mapping_from_values(values: Dict[str, str]) -> Optional[ColumnMapping]:
    def _safe_strip(value: object) -> str:
        if value is None:
            return ""
        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass
        return str(value).strip()

    date_col = _safe_strip(values.get("date"))
    hours_col = _safe_strip(values.get("hours"))
    desc_col = _safe_strip(values.get("description"))
    proj_col = _safe_strip(values.get("project"))

    if not date_col or not hours_col or not desc_col:
        return None

    return ColumnMapping(
        date=date_col,
        hours=hours_col,
        description=desc_col,
        project=proj_col or None,
    )


def auto_detect_profile_from_files(
    files: List
) -> Tuple[Optional[str], Optional[Dict[str, object]]]:

    if not files:
        return None, None

    profiles = get_profile_catalog()
    sample = files[0]

    sheets = load_multiple_sheets(sample.getvalue())
    parsed = next((s for s in sheets if not s.dataframe.empty), None)
    if not parsed:
        return None, {}

    metadata = parsed.metadata or {}
    df = parsed.dataframe
    df_columns = [str(c).lower() for c in df.columns]

    company = str(metadata.get("company", "")).lower()

    # =====================================================
    # 1️⃣ PRIORIDAD ABSOLUTA: metadata / alias de empresa
    # =====================================================
    for pid, profile in profiles.items():
        # nombre directo
        if profile.name.lower() in company:
            return pid, metadata

        # aliases
        aliases = profile.company_aliases or []
        if isinstance(aliases, str):
            aliases = [aliases]

        for alias in aliases:
            if str(alias).lower() in company:
                return pid, metadata

    # =====================================================
    # 2️⃣ FALLBACK: heurística por columnas
    # =====================================================
    best_match = None
    best_score = 0

    for pid, profile in profiles.items():
        mapping = profile.mapping or {}

        expected_cols = [
            str(v).lower()
            for v in mapping.values()
            if v
        ]

        matches = sum(
            1 for col in expected_cols
            if any(col in df_col for df_col in df_columns)
        )

        if matches > best_score:
            best_score = matches
            best_match = pid

    # mínimo razonable
    if best_match and best_score >= 3:
        return best_match, metadata

    return None, metadata



def render_batch_sidebar() -> Dict[str, object]:
    st.sidebar.markdown("**📁 Archivos**")

    # ⬇️ uploader NORMAL
    new_files = st.sidebar.file_uploader(
        "Cargar archivos",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    # ⬇️ Persistir SOLO la lista de UploadedFile
    if new_files is not None:
        st.session_state["uploaded_files_cache"] = new_files

    uploaded_files = st.session_state.get("uploaded_files_cache") or []

    profiles = get_profile_catalog()
    manual_option = "__manual__"

    if uploaded_files:
        st.sidebar.success(f"✓ {len(uploaded_files)} archivo(s)")

        # =====================================================
        # 📌 FIRMA DE ARCHIVOS (ÚNICA FUENTE DE VERDAD)
        # =====================================================
        current_files_signature = tuple((f.name, f.size) for f in uploaded_files)
        previous_signature = st.session_state.get("batch_files_signature")

        if previous_signature != current_files_signature:
            # 🆕 archivos nuevos → reset TOTAL
            st.session_state["batch_files_signature"] = current_files_signature
            st.session_state["batch_selected_profile"] = "__manual__"
            st.session_state.pop("auto_mapping_detected", None)

            # limpiar inputs de mapping
            for k in ["date", "hours", "description", "project"]:
                st.session_state[f"batch_map_{k}"] = ""

            detected_profile_id, _ = auto_detect_profile_from_files(uploaded_files)

            if detected_profile_id and detected_profile_id in profiles:
                detected_profile = profiles[detected_profile_id]

                st.session_state["batch_selected_profile"] = detected_profile_id
                st.session_state["auto_mapping_detected"] = detected_profile.mapping.copy()

                for k, v in detected_profile.mapping.items():
                    st.session_state[f"batch_map_{k}"] = v

                st.sidebar.success(f"🎯 Cliente detectado: {detected_profile.name}")






    # =====================================================
    # 🏢 CLIENTE
    # =====================================================
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🏢 Cliente**")

    options = [manual_option] + sorted(profiles.keys())

    def _fmt(option: str) -> str:
        if option == manual_option:
            return "📝 Mapeo manual"
        p = profiles.get(option)
        return f"🏢 {p.name}" if p else option

    selected_profile = st.sidebar.selectbox(
        "Cliente",
        options=options,
        format_func=_fmt,
        index=options.index(st.session_state.get("batch_selected_profile", manual_option))
        if st.session_state.get("batch_selected_profile") in options
        else 0,
        label_visibility="collapsed",
    )

    
    prev_profile = st.session_state.get("_prev_batch_profile")
    st.session_state["batch_selected_profile"] = selected_profile

    # 🔥 si el usuario cambió manualmente el cliente → limpiar auto-mapping
    if prev_profile and prev_profile != selected_profile:
        st.session_state.pop("auto_mapping_detected", None)
        for k in ["date", "hours", "description", "project"]:
            st.session_state[f"batch_map_{k}"] = ""

    st.session_state["_prev_batch_profile"] = selected_profile

    profile_obj = profiles.get(selected_profile)

    # =====================================================
    # 🗺️ MAPEOS
    # =====================================================
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
        profile_settings = profile_obj.settings
        profile_id = selected_profile

    else:
        st.sidebar.caption("Define el mapeo:")

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
            profile_settings = profile_obj.settings
            profile_id = selected_profile

        else:
            st.sidebar.caption("Define el mapeo:")

            auto_mapping = st.session_state.get("auto_mapping_detected", {})

            mapping_values = {
                "date": st.sidebar.text_input("📅 Fecha", key="batch_map_date", value=auto_mapping.get("date", "")),
                "hours": st.sidebar.text_input("⏱️ Horas", key="batch_map_hours", value=auto_mapping.get("hours", "")),
                "description": st.sidebar.text_input("📝 Descripción", key="batch_map_description", value=auto_mapping.get("description", "")),
                "project": st.sidebar.text_input("🏷️ Proyecto", key="batch_map_project", value=auto_mapping.get("project", "")),
            }
            profile_settings = {}
            profile_id = None


    return {
        "files": uploaded_files or [],
        "profile_id": profile_id,
        "mapping_values": mapping_values,
        "profile_settings": profile_settings,
    }


# =============================================================================
# BATCH MODE
# =============================================================================
def render_batch_consolidated_report(results: List[BatchFileResult]) -> None:
    valid = [r for r in results if r.success and r.result is not None]
    if len(valid) <= 1:
        return

    rows = []
    for item in valid:
        summary = item.result.summary
        md = item.result.metadata or {}
        employee_name = md.get("employee") or md.get("empleado") or Path(item.file_name).stem
        rows.append(
            {
                "Empleado": employee_name,
                "Horas": summary.horas_totales,
                "Registros": summary.total_registros,
                "Score": summary.quality_score, # Aquí viene 90, 100, etc.
                "Errores": summary.total_errores,
            }
        )

    df = pd.DataFrame(rows)

    render_divider()
    render_section_header("Reporte consolidado", icon="📊", description="Resumen del equipo")

    cols = st.columns(4)
    cols[0].metric("👥 Empleados", len(df))
    cols[1].metric("⏰ Horas", f"{df['Horas'].sum():.1f} h")
    cols[2].metric("📈 Score promedio", f"{df['Score'].mean():.0f}%")
    cols[3].metric("📝 Registros", int(df["Registros"].sum()))

    # Calculamos el estado (Usamos 90, 80, 60 tal cual vienen)
    df["Estado"] = df["Score"].apply(
        lambda s: "✅ Excelente" if s >= 90 else "🟢 Bueno" if s >= 80 else "🟡 Revisar" if s >= 60 else "🔴 Crítico"
    )

    # ---------------------------------------------------------
    # CORRECCIÓN VISUAL:
    # 1. NO dividimos para 100. Dejamos el valor original (ej: 90).
    # 2. Configuramos max_value=100.
    # 3. Usamos format="%d%%" para que muestre "90%" sin decimales.
    # ---------------------------------------------------------

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score", 
                format="%d%%",   # <--- ESTO QUITA LOS CEROS (Muestra 90% en vez de 90.00%)
                min_value=0, 
                max_value=100    # <--- ESCALA DE 0 a 100
            ),
            "Horas": st.column_config.NumberColumn("Horas", format="%.1f"),
        },
    )

    theme = get_plotly_theme()
    fig = px.bar(df, x="Empleado", y="Horas", color="Score", color_continuous_scale="RdYlGn", title="Horas por empleado")
    fig.update_layout(
        plot_bgcolor=theme["bg"],
        paper_bgcolor=theme["paper_bg"],
        font=dict(family="Inter, sans-serif", color=theme["font_color"]),
        margin=dict(t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    # BANINTER: no generar consolidado, solo descarga de individuales
    is_baninter_batch = any(is_baninter_result(r) for r in results)
    if is_baninter_batch:
        render_divider()
        render_section_header("Descarga BANINTER")
        zip_bytes = build_baninter_individuals_zip(results)
        if zip_bytes:
            st.download_button(
                "DESCARGAR INDIVIDUALES BANINTER (ZIP)",
                data=zip_bytes,
                file_name="BANINTER_Individuales_BusinessIT.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True,
            )
        else:
            st.warning("No se pudieron generar archivos individuales para BANINTER.")
        return

    # ... (El resto de la función para generar el Excel sigue igual) ...
    render_divider()
    render_section_header("Generar consolidado Excel", icon="📄")

    is_valid, warnings = validate_batch_results_for_consolidation(results)
    if warnings:
        with st.expander("⚠️ Advertencias", expanded=False):
            for w in warnings:
                st.warning(w)

    detected_name = None
    profiles = get_profile_catalog()
    for r in results:
        if not r.success:
            continue
        if r.client_id and r.client_id in profiles:
            detected_name = profiles[r.client_id].name
            break
        company = (r.metadata or {}).get("company")
        if company:
            detected_name = str(company)
            break

    default_client_name = detected_name or "NOVA - TI"
    col1, col2 = st.columns([2, 1])

    with col1:
        is_nova = "nova" in default_client_name.lower()
        if is_nova:
            auto_area = detect_area_from_names(
                [
                    (r.result.metadata or {}).get("employee")
                    or (r.result.metadata or {}).get("empleado")
                    or Path(r.file_name).stem
                    for r in results
                    if r.success and r.result
                ]
            )

            area_options = [
                "NOVA - TI (BIT Nova)",
                "NOVA - Centro Digital",
                "Manual",
            ]
            default_area = "Manual"
            if auto_area == "CD":
                default_area = "NOVA - Centro Digital"
            elif auto_area == "TI":
                default_area = "NOVA - TI (BIT Nova)"
            elif "centro digital" in default_client_name.lower() or "cd" in default_client_name.lower():
                default_area = "NOVA - Centro Digital"
            else:
                default_area = "NOVA - TI (BIT Nova)"

            area_selection = st.selectbox(
                "Cliente / Área",
                options=area_options,
                index=area_options.index(default_area),
            )
            if auto_area:
                st.caption(
                    f"Detectado automáticamente: {'NOVA - Centro Digital' if auto_area == 'CD' else 'NOVA - TI (BIT Nova)'}"
                )

            if area_selection == "NOVA - TI (BIT Nova)":
                cliente_nombre = "BIT Nova - TI"
            elif area_selection == "NOVA - Centro Digital":
                cliente_nombre = "NOVA - Centro Digital"
            else:
                cliente_nombre = sanitize_text_input(
                    st.text_input("Nombre del cliente", value=default_client_name), 100
                )
        else:
            cliente_nombre = sanitize_text_input(
                st.text_input("Nombre del cliente", value=default_client_name), 100
            )

    with col2:
        default_filename = "Consolidado.xlsx"
        first_valid = next((r for r in results if r.success and r.metadata), None)
        if first_valid:
            mes = first_valid.metadata.get("month_name", "Mes")
            year = first_valid.metadata.get("year", "2025")
            default_filename = f"Consolidado_{default_client_name.replace(' ', '_')}_{mes}_{year}.xlsx"
        output_filename = sanitize_filename(st.text_input("Nombre archivo", value=default_filename))

    if st.button("🚀 Generar Consolidado", type="primary", disabled=not is_valid, use_container_width=True):
        with st.spinner("Generando..."):
            try:
                consolidated = generate_consolidated_from_batch_results(
                    batch_results=results,
                    cliente=cliente_nombre,
                    output_filename=output_filename,
                )
                st.success("✅ Consolidado generado")

                a, b, c = st.columns(3)
                a.metric("Consultores", consolidated.consultores_incluidos)
                c.metric("Horas", f"{consolidated.total_horas:.1f} h")

                st.download_button(
                    "⬇️ Descargar Excel",
                    data=consolidated.workbook_bytes,
                    file_name=consolidated.output_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as exc:
                st.error(f"Error: {exc}")
                logger.exception("Error generando consolidado: %s", exc)

def run_batch_mode(
    batch_state: Dict[str, object],
    correct_spelling: bool,
    employee_role: str,
    similarity_threshold: int,
    min_duplicates: int,
    tolerance_factor: float,
    show_time_suggestions: bool,
) -> None:


    uploaded_files: List = batch_state.get("files") or []

    if not uploaded_files:
        st.markdown(
            """
            <style>
            .cool-empty {
              border: 1px dashed rgba(148,163,184,0.6);
              background: linear-gradient(135deg, rgba(148,163,184,0.12), rgba(15,23,42,0.05));
              padding: 22px 24px;
              border-radius: 16px;
              text-align: left;
            }
            .cool-empty h3 {
              margin: 0 0 8px 0;
              font-size: 20px;
            }
            .cool-empty p {
              margin: 0;
              color: #64748b;
              font-size: 14px;
            }
            </style>
            <div class="cool-empty">
              <h3>Listo para procesar cuando tu tambien lo estes</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.session_state.get("show_time_suggestions"):
            st.caption("Referencias: Daily ~0.25h · Reuniones 0.25-3h · Dev 1-8h · Review 0.25-2h")
        return

    # =========================
    # PERFIL / CLIENTE
    # =========================
    profiles_catalog = get_profile_catalog()
    profile_id = batch_state.get("profile_id")
    profile_obj = profiles_catalog.get(profile_id) if profile_id else None

    preview_metadata: Optional[Dict[str, object]] = None
    if profile_obj is None:
        base_mapping = build_mapping_from_values(
            batch_state.get("mapping_values", {})
        )
        if base_mapping is None:
            st.warning("⚠️ Define columnas de Fecha, Horas y Descripción.")
            return
        profile_settings = batch_state.get("profile_settings") or {}
        header_keywords = []
        for v in (batch_state.get("mapping_values") or {}).values():
            if v is None:
                continue
            try:
                if pd.isna(v):
                    continue
            except Exception:
                pass
            txt = str(v).strip()
            if txt:
                header_keywords.append(txt)
    else:
        base_mapping = profile_obj.to_column_mapping()
        if base_mapping is None:
            st.error("El perfil no tiene columnas obligatorias.")
            return
        profile_settings = profile_obj.settings or {}
        header_keywords = [v for v in profile_obj.mapping.values() if v]

    duplicate_threshold = int(
        profile_settings.get(
            "duplicate_similarity_threshold", similarity_threshold
        )
    )
    min_duplicates_setting = int(
        profile_settings.get("duplicate_min_occurrences", min_duplicates)
    )
    hours_tolerance = float(
        profile_settings.get("hours_tolerance_factor", tolerance_factor)
    )
    role_to_use = str(
        profile_settings.get("rol_default")
        or profile_settings.get("role")
        or employee_role
    )
    spelling_flag = bool(
        profile_settings.get("correct_spelling", correct_spelling)
    )

# =========================
# PREPARAR REQUESTS (DINÁMICOS)
# =========================
    requests: List[BatchFileRequest] = []

    if not uploaded_files:
        st.warning("⚠️ No hay archivos cargados.")
        return  # ⛔ ESTE return ES VÁLIDO porque estamos DENTRO de la función

    def _infer_client_id_for_file(
        file_name: str,
        metadata: Optional[Dict[str, object]],
        fallback_client_id: Optional[str],
    ) -> Optional[str]:
        # Si ya está definido explícitamente como BANINTER, respetarlo
        if fallback_client_id == "cliente_talent":
            return fallback_client_id

        fname = str(file_name or "").lower()
        company = str((metadata or {}).get("company", "")).lower()

        # Señales BANINTER
        if (
            "baninter" in fname
            or "banco internacional" in fname
            or "resumen actividades recursos" in fname
            or "baninter" in company
            or "banco internacional" in company
        ):
            return "cliente_talent"

        # Señales NOVA/BIT
        if (
            "nova" in fname
            or "bit" in fname
            or "nova" in company
            or "bit" in company
        ):
            return "cliente_bit"

        return fallback_client_id

    for file_obj in uploaded_files:
        parsed = load_sheet_with_header(
            file_obj.getvalue(),
            header_keywords=header_keywords,
        )

        effective_client_id = _infer_client_id_for_file(
            file_name=file_obj.name or "",
            metadata=getattr(parsed, "metadata", {}) or {},
            fallback_client_id=profile_id,
        )

        dynamic_mapping = infer_column_mapping(
            parsed.dataframe,
            profile_obj.mapping if profile_obj else {},
        )

        mapping_to_use = dynamic_mapping or base_mapping

        if dynamic_mapping:
            logger.warning(
                f"⚠️ Plantilla no estándar detectada en '{file_obj.name}'. "
                "Se aplicó mapeo inferido automáticamente."
            )

            requests.append(
                BatchFileRequest(
                    file_name=file_obj.name or "reporte.xlsx",
                    file_bytes=file_obj.getvalue(),
                    mapping=mapping_to_use,
                    client_id=effective_client_id,
                    header_keywords=header_keywords,
                    profile_settings=profile_settings,
                    parsed_sheet=parsed,
                    processor_kwargs={
                        "correct_spelling": spelling_flag,
                        "role": role_to_use,
                        "project_name": mapping_to_use.project or "No especificado",
                        "duplicate_similarity_threshold": duplicate_threshold,
                        "duplicate_min_occurrences": min_duplicates_setting,
                        "hours_tolerance_factor": hours_tolerance,
                        "batch_fast_mode": True,
                        "enable_debug_exports": False,
                    },
                )
            )

    # =========================
    # BOTÓN PROCESAR
    # =========================
    if st.button(
        f"▶️ Procesar {len(requests)} archivo(s)",
        type="primary",
        use_container_width=True,
    ):
        progress_placeholder = st.empty()
        progress_bar = st.progress(0)
        progress_placeholder.info("⏳ Iniciando procesamiento...")
        progress_bar.progress(1)

        def update_progress(
            current: int, total: int, message: str
        ) -> None:
            pct = 0 if total == 0 else int((current / total) * 100)
            progress_placeholder.info(
                f"🔄 {message} ({current}/{total})"
            )
            progress_bar.progress(min(pct, 100))

        results = batch_processor.process_batch(
            requests, progress_callback=update_progress
        )

        progress_placeholder.success("✅ Procesamiento completado")
        progress_bar.empty()

        st.session_state["batch_results"] = results
        st.session_state["batch_mapping"] = base_mapping
        st.rerun()

    if st.session_state.get("batch_results"):
        render_batch_results()


# =========================
# RESULTADOS
# =========================
def render_batch_results():
    batch_results: List[BatchFileResult] = st.session_state.get(
        "batch_results", []
    )

    if not batch_results:
        st.info("📋 Presiona el botón para iniciar.")
        return

    success_count = sum(1 for r in batch_results if r.success)
    render_divider()
    render_section_header(
        f"Resultados ({success_count}/{len(batch_results)})",
        icon="📋",
    )

    for result in batch_results:
        if result.success and result.result:
            s = result.result.summary
            md = result.result.metadata or {}

            st.success(f"✅ {result.file_name}")
            emp_info = resolve_employee(md, result.file_name)
            render_metadata_summary(
                md, employee_info=emp_info, title=f"📄 {result.file_name}"
            )
            if is_baninter_result(result):
                render_baninter_report(md.get("baninter_report"))
            metrics = st.columns(4)
            metrics[0].metric("📝 Registros", s.total_registros)
            metrics[1].metric("⏰ Horas", f"{s.horas_totales:.1f}")
            metrics[2].metric("🚨 Errores", s.errores_criticos)
            metrics[3].metric("📈 Score", f"{s.quality_score:.0f}%")

            c1, c2 = st.columns(2)
            if is_baninter_result(result):
                try:
                    business_bytes, business_name = generate_individual_business_it_excel(
                        result, cliente="BANINTER"
                    )
                    c1.download_button(
                        "⬇️ Excel Business IT",
                        data=business_bytes,
                        file_name=business_name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except Exception:
                    c1.download_button(
                        "⬇️ Excel",
                        data=result.result.workbook_bytes,
                        file_name=result.result.output_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
            else:
                c1.download_button(
                    "⬇️ Excel",
                    data=result.result.workbook_bytes,
                    file_name=result.result.output_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            summary_json = json.dumps(
                {"calidad": s.quality_score, "registros": s.total_registros},
                indent=2,
            )
            c2.download_button(
                "⬇️ JSON",
                data=summary_json,
                file_name=f"{Path(result.result.output_filename).stem}.json",
                mime="application/json",
            )

            with st.expander("Errores detectados", expanded=False):
                if result.result.errors_dataframe.empty:
                    st.success("Sin errores reportados.")
                else:
                    sorted_errors = sort_errors_dataframe(result.result.errors_dataframe)
                    st.dataframe(
                        sorted_errors,
                        use_container_width=True,
                        hide_index=True,
                    )
                    
            batch_mapping = st.session_state.get("batch_mapping")

            render_holiday_block(
                result.result.corrected_dataframe,
                batch_mapping.date if batch_mapping else None,
                metadata=md,
            )

            st.markdown("---")
        else:
            st.error(f"❌ {result.file_name}")
            if result.error:
                st.write(result.error)

    render_batch_consolidated_report(batch_results)

    if st.session_state.get("show_time_suggestions"):
        st.caption(
            "📌 Referencias: Daily ~0.25h · Reuniones 0.25-3h · Dev 1-8h · Review 0.25-2h"
        )

# =============================================================================
# INDIVIDUAL MULTI-SHEET MODE (TU CASO “1 EXCEL = N EMPLEADOS”)
# =============================================================================
def run_individual_multisheet(correct_spelling: bool, employee_role: str) -> None:
    render_section_header("Cargar archivo", icon="📤")

    uploaded_file = st.file_uploader("Excel", type=["xlsx", "xls"], label_visibility="collapsed")
    if not uploaded_file:
        st.session_state["batch_results_accumulator"] = None
        render_empty_state(
            "⚡",
            "Tu reporte en segundos",
            "Sube tu Excel y el sistema ordena, valida y consolida automáticamente.",
        )
        return

    source_bytes = uploaded_file.getvalue()
    source_name = uploaded_file.name or "reporte.xlsx"

    parsed_sig = f"{source_name}:{len(source_bytes)}"
    cached_sig = st.session_state.get("multi_parsed_sheets_sig")
    cached_sheets = st.session_state.get("multi_parsed_sheets_cache")
    if cached_sig == parsed_sig and cached_sheets is not None:
        all_parsed_sheets = cached_sheets
    else:
        with st.spinner("Analizando archivo..."):
            all_parsed_sheets = load_multiple_sheets(source_bytes)
        st.session_state["multi_parsed_sheets_sig"] = parsed_sig
        st.session_state["multi_parsed_sheets_cache"] = all_parsed_sheets

    if not all_parsed_sheets:
        st.error("❌ No se detectaron hojas válidas con datos.")
        return

    # 🔹 FILTRAR HOJAS BASURA
    filtered_sheets = []
    skipped_generic_sheets = []

    for sheet in all_parsed_sheets:
        sheet_name_lower = sheet.sheet_name.lower()
        metadata = sheet.metadata or {}
        
        is_generic_name = sheet_name_lower in ["hoja1", "sheet1", "hoja", "sheet", "hoja 1", "sheet 1"]
        has_no_metadata = not metadata.get("company") and not metadata.get("employee")
        
        if is_generic_name and has_no_metadata:
            skipped_generic_sheets.append(sheet.sheet_name)
            continue
        
        filtered_sheets.append(sheet)

    if skipped_generic_sheets:
        with st.expander("🗑️ Hojas ignoradas (sin metadata)", expanded=False):
            for name in skipped_generic_sheets:
                st.caption(f"• {name} (hoja genérica sin datos de cliente/empleado)")

    if not filtered_sheets:
        st.error("❌ No se encontraron hojas con datos válidos de timesheet.")
        return

    all_parsed_sheets = filtered_sheets
    num_consultores = len(all_parsed_sheets)

    if num_consultores > 1:
        st.success(f"✅ Se detectaron **{num_consultores} empleados**.")
    else:
        st.success(f"✅ Hoja detectada: **{all_parsed_sheets[0].sheet_name}**")

    render_section_header("Configuración", icon="⚙️")

    first_sheet = all_parsed_sheets[0]
    columns = [str(c) for c in first_sheet.dataframe.columns]

    def find_col(keywords: List[str], fallback_index: Optional[int] = None) -> Optional[str]:
        for col in columns:
            cl = str(col).lower()
            if any(k in cl for k in keywords):
                return col
        if fallback_index is not None and 0 <= fallback_index < len(columns):
            return columns[fallback_index]
        return None

    mapping = ColumnMapping(
        date=find_col(["fecha", "date"]),
        hours=find_col(["horas", "hours", "tiempo"]),
        description=find_col(["actividad", "descrip", "task", "tarea"]),
        project=find_col(["tipo actividad", "proyecto", "project"]),
    )

    profiles = list(get_profile_catalog().values())
    auto_profile_id = auto_detect_profile(source_name, getattr(first_sheet, "metadata", {}), profiles)

    if not auto_profile_id:
        metadata = getattr(first_sheet, "metadata", {})
        company = str(metadata.get("company", "")).lower()
        for profile in profiles:
            if profile.name.lower() in company:
                auto_profile_id = profile.client_id
                st.success(f"🎯 Cliente detectado (por nombre): **{profile.name}**")
                break
            aliases = profile.company_aliases or []
            if isinstance(aliases, str): aliases = [aliases]
            for alias in aliases:
                if str(alias).lower() in company:
                    auto_profile_id = profile.client_id
                    st.success(f"🎯 Cliente detectado (por alias): **{profile.name}**")
                    break
            if auto_profile_id: break

    selected_settings = {
        "correct_spelling": True,
        "duplicate_similarity_threshold": 90,
        "duplicate_min_occurrences": 3,
        "hours_tolerance_factor": 1.5,
        "role": "Consultor",
    }

    if auto_profile_id:
        detected_profile = next((p for p in profiles if p.client_id == auto_profile_id), None)
        if detected_profile:
            selected_settings.update(detected_profile.settings or {})
            st.info(f"🎯 Perfil aplicado: **{detected_profile.name}**")

    with st.expander("🛠️ Configuración Avanzada (Clic para editar)", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            use_ia = st.checkbox("🤖 Corrección con IA", value=bool(selected_settings["correct_spelling"]))
            similarity = st.slider("🔍 Sensibilidad Duplicados", 70, 100, int(selected_settings["duplicate_similarity_threshold"]))
        with c2:
            tolerance = st.slider("⏰ Tolerancia Horas", 1.0, 3.0, float(selected_settings["hours_tolerance_factor"]))
            min_duplicates = st.number_input("🔢 Mínimo repeticiones", min_value=1, max_value=1000, value=int(selected_settings.get("duplicate_min_occurrences", 3)))
            role_select = st.selectbox("👤 Rol", ["Consultor", "Developer", "Manager"], index=0)

        selected_settings["correct_spelling"] = bool(use_ia)
        selected_settings["duplicate_similarity_threshold"] = int(similarity)
        selected_settings["duplicate_min_occurrences"] = int(min_duplicates)
        selected_settings["hours_tolerance_factor"] = float(tolerance)
        selected_settings["role"] = str(role_select)

    # ------------------ CLIENTE / ÁREA (AUTO + MANUAL) ------------------
    names_for_area = [
        (sheet.metadata or {}).get("employee") or sheet.sheet_name
        for sheet in all_parsed_sheets
    ]
    company_meta = getattr(first_sheet, "metadata", {}) or {}
    company_name = company_meta.get("company", "")
    is_nova = "nova" in company_name.lower()
    if not is_nova and auto_profile_id:
        p = next((p for p in profiles if p.client_id == auto_profile_id), None)
        if p and "nova" in p.name.lower():
            is_nova = True

    auto_area = None
    area_selection = None
    if is_nova:
        auto_area = detect_area_from_names(names_for_area)

        area_options = [
            "NOVA - TI (BIT Nova)",
            "NOVA - Centro Digital",
            "Manual",
        ]
        default_area = "Manual"
        if auto_area == "CD":
            default_area = "NOVA - Centro Digital"
        elif auto_area == "TI":
            default_area = "NOVA - TI (BIT Nova)"

        area_selection = st.selectbox(
            "Cliente / Área",
            options=area_options,
            index=area_options.index(default_area),
        )
        if auto_area:
            st.caption(
                f"Detectado automáticamente: {'NOVA - Centro Digital' if auto_area == 'CD' else 'NOVA - TI (BIT Nova)'}"
            )

    # ------------------ PROCESS BUTTON ------------------
    if st.button(f"🚀 PROCESAR {num_consultores} CONSULTORES", type="primary", use_container_width=True):
        st.session_state["batch_results_accumulator"] = None
        st.session_state["consolidated_result"] = None

        progress_text = st.empty()
        progress_bar = st.progress(0)

        batch_results_accumulator: List[BatchFileResult] = []
        skipped_sheets: List[Tuple[str, List[str]]] = []

        try:
            total_sheets = len(all_parsed_sheets)

            for i, sheet in enumerate(all_parsed_sheets):
                sheet_metadata = sheet.metadata or {}
                emp_name = sheet_metadata.get("employee")
                
                if not emp_name:
                    cols_detectadas = [str(c) for c in list(sheet.dataframe.columns)]
                    skipped_sheets.append((sheet.sheet_name, cols_detectadas))
                    continue
                
                if emp_name.lower() in ["hoja1", "sheet1", "empleado", "consultor", "hoja", "sheet"]:
                    cols_detectadas = [str(c) for c in list(sheet.dataframe.columns)]
                    skipped_sheets.append((sheet.sheet_name, cols_detectadas))
                    continue

                progress_text.info(f"⏳ Procesando ({i+1}/{total_sheets}): {emp_name}")
                progress_bar.progress(int((i / max(total_sheets, 1)) * 90))

                profile_mapping = {}
                if auto_profile_id:
                    detected_profile = next((p for p in profiles if p.client_id == auto_profile_id), None)
                    if detected_profile: profile_mapping = detected_profile.mapping or {}

                mapping_to_use = infer_column_mapping(sheet.dataframe, profile_mapping)

                if mapping_to_use is None:
                    cols_detectadas = [str(c) for c in list(sheet.dataframe.columns)]
                    skipped_sheets.append((sheet.sheet_name, cols_detectadas))
                    continue

                result_single = processor.process_parsed_sheet(
                    parsed_sheet=sheet,
                    mapping=mapping_to_use,
                    source_name=f"{source_name} :: {emp_name}",
                    original_excel_bytes=None,
                    correct_spelling=bool(selected_settings["correct_spelling"]),
                    upload_to_blob=False,
                    role=str(selected_settings["role"]),
                    project_name=mapping_to_use.project or "No especificado",
                    duplicate_similarity_threshold=int(selected_settings["duplicate_similarity_threshold"]),
                    duplicate_min_occurrences=int(selected_settings["duplicate_min_occurrences"]),
                    hours_tolerance_factor=float(selected_settings["hours_tolerance_factor"]),
                    client_profile_id=auto_profile_id,
                    client_profile_settings=selected_settings,
                    batch_fast_mode=True,
                    enable_debug_exports=False,
                )

                batch_results_accumulator.append(
                    BatchFileResult(
                        file_name=f"{emp_name}.xlsx",
                        success=True,
                        result=result_single,
                        sheet_name=emp_name,
                        client_id=auto_profile_id or "manual",
                        metadata=sheet_metadata,
                    )
                )

            if skipped_sheets:
                with st.expander("🗂️ Hojas ignoradas", expanded=False):
                    for name, cols in skipped_sheets:
                        st.warning(f"Se ignoró **{name}**. Columnas: {cols}")

            if not batch_results_accumulator:
                progress_bar.empty()
                progress_text.empty()
                st.error("❌ No se encontró ninguna hoja válida de timesheet.")
                return

            progress_text.info("📊 Generando consolidado...")
            progress_bar.progress(95)

            if is_nova and area_selection == "NOVA - TI (BIT Nova)":
                cliente_nombre = "BIT Nova - TI"
            elif is_nova and area_selection == "NOVA - Centro Digital":
                cliente_nombre = "NOVA - Centro Digital"
            else:
                if auto_profile_id:
                    p = next((p for p in profiles if p.client_id == auto_profile_id), None)
                    if p:
                        cliente_nombre = p.name
                    else:
                        cliente_nombre = company_name or "Cliente"
                else:
                    cliente_nombre = company_name or "Cliente"

            consolidated = generate_consolidated_from_batch_results(
                batch_results=batch_results_accumulator,
                cliente=cliente_nombre,
                output_filename=f"Consolidado_{cliente_nombre.replace(' ', '_')}_{len(batch_results_accumulator)}_Consultores.xlsx",
            )

            progress_bar.progress(100)
            time.sleep(0.2)
            progress_text.empty()
            progress_bar.empty()

            st.session_state["batch_results_accumulator"] = batch_results_accumulator
            st.session_state["consolidated_result"] = consolidated
            st.session_state["current_file_signature"] = f"{source_name}_{len(source_bytes)}"

        except Exception as exc:
            progress_bar.empty()
            progress_text.empty()
            st.error(f"💀 Ocurrió un error: {exc}")
            logger.exception("Error processing multi-sheet")
            return

    # ------------------ DISPLAY ------------------
    file_sig = f"{source_name}_{len(source_bytes)}"
    has_results = st.session_state.get("batch_results_accumulator") is not None
    is_same_file = st.session_state.get("current_file_signature") == file_sig

    if not (has_results and is_same_file):
        return

    batch_results = st.session_state["batch_results_accumulator"]
    consolidated = st.session_state["consolidated_result"]

    # =========================================================
    # 1. MOSTRAR LISTA DETALLADA (SCROLL) - PRIMERO
    # =========================================================
    render_divider()
    st.markdown("#### 🔍 Detalle Individual")
    
    st.markdown("""<style>.consultor-scroll {max-height: 600px; overflow-y: auto; padding-right: 10px;}</style>""", unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="consultor-scroll">', unsafe_allow_html=True)
        for idx, res in enumerate(batch_results):
            if not (res.success and res.result): continue
            
            summ = res.result.summary
            md = res.result.metadata or {}
            # Nombre prioritario: Metadata > Nombre Hoja
            nombre = md.get("employee") or res.sheet_name or f"Consultor {idx+1}"

            # ENCABEZADO Y MÉTRICAS
            st.markdown("---")
            st.markdown(f"### 👤 {nombre} | Score: {summ.quality_score}%")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📝 Registros", summ.total_registros)
            c2.metric("⏰ Horas", f"{summ.horas_totales:.1f}")
            c3.metric("🚨 Errores", summ.total_errores)
            c4.metric("📈 Score", f"{summ.quality_score:.0f}%")

            if is_baninter_result(res):
                render_baninter_report(md.get("baninter_report"))

            if is_baninter_result(res):
                try:
                    business_bytes, business_name = generate_individual_business_it_excel(
                        res, cliente="BANINTER"
                    )
                    st.download_button(
                        f"⬇️ Excel Business IT - {nombre}",
                        data=business_bytes,
                        file_name=business_name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"baninter_dl_{idx}",
                    )
                except Exception:
                    pass

            # ERRORES (Expander)
            if not res.result.errors_dataframe.empty:
                with st.expander(f"⚠️ Errores detectados ({len(res.result.errors_dataframe)})", expanded=False):
                    sorted_errors = sort_errors_dataframe(res.result.errors_dataframe)
                    st.dataframe(
                        sorted_errors[["fecha", "tipo_error", "descripcion", "valor_original"]],
                        use_container_width=True,
                        hide_index=True,
                    )
            else:
                st.success("🎉 Sin errores detectados.")

            # FERIADOS (Expander)
            render_holiday_block(
                res.result.corrected_dataframe,
                mapping.date if mapping else None,
                metadata=res.result.metadata,
                # use_expander=True (Por defecto)
            )

        st.markdown('</div>', unsafe_allow_html=True)

    # =========================================================
    # 2. MOSTRAR TABLA RESUMEN (DETALLE POR CONSULTOR) - SEGUNDO
    # =========================================================
    render_divider()
    render_section_header("Detalle por Consultor", icon="📋")

    resumen = []
    for idx, r in enumerate(batch_results):
        if r.success and r.result:
            s = r.result.summary
            md = r.result.metadata or {}
            emp = md.get("employee", r.sheet_name)
            estado = "✅" if s.quality_score >= 90 else "🟢" if s.quality_score >= 80 else "🟡" if s.quality_score >= 60 else "🔴"
            resumen.append({
                "Index": idx, "Consultor": emp, "Estado": estado,
                "Registros": s.total_registros, "Horas": float(f"{s.horas_totales:.1f}"),
                "Errores": s.total_errores, "Score": s.quality_score,
            })

    df_resumen = pd.DataFrame(resumen)
    st.dataframe(
        df_resumen.drop(columns=["Index"]), 
        use_container_width=True, 
        hide_index=True, 
        column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d%%")}
    )

    # =========================================================
    # 3. DESCARGAS FINALES
    # =========================================================
    render_divider()
    is_baninter_batch = any(is_baninter_result(r) for r in batch_results)
    if is_baninter_batch:
        render_section_header("Descarga BANINTER", icon="📦")
        zip_bytes = build_baninter_individuals_zip(batch_results)
        if zip_bytes:
            st.download_button(
                "DESCARGAR INDIVIDUALES BANINTER (ZIP)",
                data=zip_bytes,
                file_name="BANINTER_Individuales_BusinessIT.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True,
            )
        else:
            st.warning("No se pudieron generar archivos individuales para BANINTER.")
    else:
        render_section_header("Reporte Listo", icon="🏁")
        c1, c2 = st.columns(2)
        c1.metric("⏰ Horas Totales", f"{consolidated.total_horas:.1f} h")
        c2.metric("👥 Consultores", consolidated.consultores_incluidos)
        st.download_button(
            "📥 DESCARGAR EXCEL CONSOLIDADO",
            data=consolidated.workbook_bytes,
            file_name=consolidated.output_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )
# =============================================================================
# APP SHELL (SIDEBAR + ROUTER)
# =============================================================================
with st.sidebar:

    # Solo mostrar este bloque si el usuario está en "Por lotes"
    if st.session_state.get("processing_mode") == "Por lotes":
        render_section_header("Procesamiento por lotes", icon="📦", description="Procesa múltiples archivos")
        similarity_threshold, min_duplicates, tolerance_factor, show_time_suggestions = render_validation_settings()
    else:
        similarity_threshold = min_duplicates = tolerance_factor = show_time_suggestions = None

    st.markdown("### 🎨 Apariencia")
    render_theme_toggle()
    st.markdown("---")

    st.markdown("### ⚙️ Configuración")
    processing_mode = st.radio(
    "Modo",
    ["Individual", "Por lotes"],
    horizontal=True,
    key="processing_mode",
    )

    correct_spelling = st.checkbox("🤖 Corrección ortográfica", value=True)
    employee_role = st.selectbox(
        "👤 Rol del empleado",
        ["Desconocido", "Developer", "QA", "DevOps", "Project Manager", "Otro"],
    )

    batch_sidebar_state: Optional[Dict[str, object]] = None
    if processing_mode == "Por lotes":
        st.markdown("---")
        batch_sidebar_state = render_batch_sidebar()

    # 🔥 SI CAMBIÓ EL CLIENTE → BORRAR AUTO MAPPING
    prev_profile = st.session_state.get("_prev_batch_profile")
    current_profile = st.session_state.get("batch_selected_profile")

    if prev_profile != current_profile:
        st.session_state.pop("auto_mapping_detected", None)

    st.session_state["_prev_batch_profile"] = current_profile

    # Usuario (siempre al final del sidebar)
    render_user_info_sidebar()



# MAIN
render_header("Depurador de Horas", "Valida y depura registros de timesheet automáticamente")

if processing_mode == "Por lotes":
    if batch_sidebar_state is None:
        st.error("Error de configuración.")
    else:
        run_batch_mode(
            batch_state=batch_sidebar_state,
            correct_spelling=correct_spelling,
            employee_role=employee_role,
            similarity_threshold=similarity_threshold,
            min_duplicates=min_duplicates,
            tolerance_factor=tolerance_factor,
            show_time_suggestions=show_time_suggestions,
        )
else:
    run_individual_multisheet(correct_spelling=correct_spelling, employee_role=employee_role)

st.markdown("---")
st.caption("Depurador de Horas v2.0 · Nova-TI")
