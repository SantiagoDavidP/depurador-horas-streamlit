"""
SNIPPET para agregar al frontend/app.py

Este código debe agregarse/reemplazar en la función render_batch_consolidated_report
para incluir la funcionalidad de generar el Excel consolidado.

Ubicación: Después de la línea 359 (después del gráfico de barras)
"""

# ======================================================================
# AGREGAR ESTE IMPORT AL INICIO DEL ARCHIVO app.py (después de línea 28)
# ======================================================================
from backend.consolidator_integration import (  # noqa: E402
    generate_consolidated_from_batch_results,
    validate_batch_results_for_consolidation,
)

# ======================================================================
# MODIFICAR/REEMPLAZAR LA FUNCIÓN render_batch_consolidated_report
# (líneas 312-359 del app.py original)
# ======================================================================


def render_batch_consolidated_report(results: List[BatchFileResult]) -> None:
    """
    Renderiza el reporte consolidado del batch con dashboard y opción de generar Excel.

    Esta función ahora incluye:
    1. Dashboard visual con métricas (como antes)
    2. Botón para generar Excel consolidado profesional
    """
    valid = [item for item in results if item.success and item.result is not None]
    if len(valid) <= 1:
        return

    # ============================================================
    # PARTE 1: Dashboard visual (código original mantenido)
    # ============================================================
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
        rows.append(
            {
                "Empleado": employee_name,
                "Horas": summary.horas_totales,
                "Registros": summary.total_registros,
                "Score": summary.quality_score,
                "Errores": summary.total_errores,
            }
        )

    df_summary = pd.DataFrame(rows)
    st.markdown("## 📊 Reporte consolidado del equipo")

    cols = st.columns(4)
    cols[0].metric("Empleados", len(df_summary))
    cols[1].metric("Horas totales", f"{df_summary['Horas'].sum():.1f} h")
    cols[2].metric("Score promedio", f"{df_summary['Score'].mean():.0f}/100")
    cols[3].metric("Registros", int(df_summary["Registros"].sum()))

    df_summary["Estado"] = df_summary["Score"].apply(
        lambda score: "✅ Excelente"
        if score >= 90
        else "🟢 Bueno"
        if score >= 80
        else "🟡 Revisar"
        if score >= 60
        else "🔴 Crítico"
    )

    st.dataframe(df_summary, use_container_width=True, hide_index=True)

    fig = px.bar(
        df_summary,
        x="Empleado",
        y="Horas",
        color="Score",
        color_continuous_scale="RdYlGn",
        title="Horas por empleado",
        labels={"Horas": "Horas registradas"},
    )
    st.plotly_chart(fig, use_container_width=True)

    # ============================================================
    # PARTE 2: Generación de Excel Consolidado (NUEVO)
    # ============================================================
    st.markdown("---")
    st.markdown("### 📄 Generar Informe Consolidado Excel")

    # Validar que los resultados sean aptos para consolidación
    is_valid, warnings = validate_batch_results_for_consolidation(results)

    # Mostrar warnings si existen
    if warnings:
        with st.expander("⚠️ Advertencias detectadas", expanded=False):
            for warning in warnings:
                st.warning(warning)

    # Configuración del consolidado
    col1, col2 = st.columns([2, 1])

    with col1:
        cliente_nombre = st.text_input(
            "Nombre del cliente",
            value="NOVA - TI",
            help="Nombre que aparecerá en el encabezado del consolidado",
        )

    with col2:
        # Auto-generar nombre de archivo basado en el periodo
        first_valid = next((r for r in results if r.success and r.metadata), None)
        if first_valid:
            mes = first_valid.metadata.get("month_name", "Unknown")
            year = first_valid.metadata.get("year", "2025")
            default_filename = f"Informe_TI_{cliente_nombre.replace(' ', '_')}_{mes}_{year}_Consolidado.xlsx"
        else:
            default_filename = "Informe_Consolidado.xlsx"

        output_filename = st.text_input(
            "Nombre del archivo",
            value=default_filename,
            help="Nombre del archivo Excel a generar",
        )

    # Botón para generar el consolidado
    if st.button(
        "🚀 Generar Consolidado Excel",
        type="primary",
        disabled=not is_valid,
        use_container_width=True,
    ):
        with st.spinner("Generando reporte consolidado profesional..."):
            try:
                # Generar el consolidado
                consolidated = generate_consolidated_from_batch_results(
                    batch_results=results,
                    cliente=cliente_nombre,
                    output_filename=output_filename,
                )

                # Mostrar resumen del consolidado generado
                st.success("✅ Consolidado generado exitosamente")

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Consultores incluidos", consolidated.consultores_incluidos)
                col_b.metric(
                    "Total a facturar", f"${consolidated.total_facturar:,.2f}"
                )
                col_c.metric("Total horas", f"{consolidated.total_horas:.1f} h")

                st.info(
                    f"📅 **Periodo:** {consolidated.periodo} · "
                    f"**Días laborables:** {consolidated.dias_laborables}"
                )

                # Botón de descarga
                st.download_button(
                    label="⬇️ Descargar Consolidado Excel",
                    data=consolidated.workbook_bytes,
                    file_name=consolidated.output_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

                # Mostrar preview del contenido
                with st.expander("📋 Vista previa del contenido", expanded=False):
                    st.markdown("**Estructura del archivo generado:**")
                    st.markdown(
                        f"""
                        - **Hoja 1: Resumen** - Tabla con {consolidated.consultores_incluidos} consultores
                        - **Hojas 2-{consolidated.consultores_incluidos + 1}:** Reportes individuales por consultor

                        **Información incluida en la hoja Resumen:**
                        - Cliente: {cliente_nombre}
                        - Periodo: {consolidated.periodo}
                        - Días laborables: {consolidated.dias_laborables}
                        - Total a facturar: ${consolidated.total_facturar:,.2f}

                        **Cálculos realizados por consultor:**
                        - Días laborados (fechas únicas con actividades)
                        - Total horas normales (HN)
                        - Total horas extras
                        - Valor tarifa según cargo (Senior/Semisenior/Junior)
                        - Cálculos de facturación
                        """
                    )

            except ValueError as ve:
                st.error(f"❌ Error de validación: {ve}")
            except Exception as exc:
                st.error(f"❌ Error generando consolidado: {exc}")
                logger.exception("Error generando consolidado: %s", exc)


# ======================================================================
# NOTAS DE IMPLEMENTACIÓN
# ======================================================================
# 1. Esta función reemplaza completamente render_batch_consolidated_report
# 2. Mantiene la funcionalidad del dashboard visual original
# 3. Agrega la sección de generación de Excel consolidado
# 4. El botón solo se habilita si hay resultados válidos para consolidar
# 5. Muestra warnings si hay inconsistencias en los datos
# 6. Permite personalizar el nombre del cliente y archivo de salida
# 7. Genera vista previa y botón de descarga del archivo
