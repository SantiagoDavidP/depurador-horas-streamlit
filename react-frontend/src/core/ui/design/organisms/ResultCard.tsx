import React from "react";
import { ResultItem } from "../../../../feat/timesheet/domain/Timesheet";
import { ErrorsTable } from "./ErrorsTable";
import { Typography } from "../atoms/Typography";
import { Tag } from "../atoms/Tag";
import { InfoItem } from "../molecules/InfoItem";
import { MetricCard } from "../molecules/MetricCard";
import { Button } from "../atoms/Button";

interface ResultCardProps {
    result: ResultItem;
    index: number;
    errorColWidths: number[];
    onResizeStart: (index: number, event: React.MouseEvent) => void;
    onDownload: (downloadId?: string, filename?: string) => void;
    noPadding?: boolean;
}

export const ResultCard: React.FC<ResultCardProps> = ({
    result,
    index,
    errorColWidths,
    onResizeStart,
    onDownload,
    noPadding = false,
}) => {
    const summary = result.summary;
    const score = summary?.quality_score ?? 0;
    const employeeName =
        result.employee_info?.metadata ||
        result.employee_info?.final ||
        result.sheet_name ||
        result.file_name;

    const metadata = result.metadata || {};
    const metadataItems: { label: string; value: string }[] = [];
    const employeeLabel = result.employee_info?.metadata || result.employee_info?.final;
    if (employeeLabel) metadataItems.push({ label: "Empleado", value: String(employeeLabel) });
    if (metadata["company"]) metadataItems.push({ label: "Empresa", value: String(metadata["company"]) });
    if (metadata["period_start"] && metadata["period_end"]) {
        metadataItems.push({
            label: "Periodo",
            value: `${metadata["period_start"]} -> ${metadata["period_end"]}`,
        });
    }
    if (metadata["month_name"]) metadataItems.push({ label: "Mes", value: String(metadata["month_name"]) });
    const baninterReport = metadata["baninter_report"] as Record<string, any> | undefined;

    const renderHoliday = (holidayInfo: ResultItem["holiday_info"]) => {
        if (!holidayInfo) return null;
        return (
            <details className="expander">
                <summary>Feriados del mes</summary>
                <div className="expander-content">
                    <strong>Mes analizado:</strong> {holidayInfo.month_label}
                    {holidayInfo.holidays.length === 0 ? (
                        <Typography variant="small">Sin feriados registrados.</Typography>
                    ) : (
                        <ul>
                            {holidayInfo.holidays.map((h, idx) => (
                                <li key={idx}>
                                    {h.date} - {h.name}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </details>
        );
    };

    return (
        <div
            key={`${result.file_name}-${index}`}
            className={`card ${noPadding ? "card-no-padding" : ""}`}
            style={{ marginBottom: 16 }}
        >
            <div className={noPadding ? "card-text-content" : ""}>
                <div className="flex-between">
                    <Typography variant="h3" style={{ margin: 0 }}>{employeeName}</Typography>
                    <Tag>Score: {score.toFixed(0)}%</Tag>
                </div>
            </div>

            {metadataItems.length > 0 && (
                <details className="expander" style={!noPadding ? { marginTop: 12 } : {}}>
                    <summary>Metadata</summary>
                    <div className="expander-content">
                        <div className="info-grid">
                            {metadataItems.map((item) => (
                                <InfoItem key={item.label} label={item.label} value={item.value} />
                            ))}
                        </div>
                    </div>
                </details>
            )}

            {summary && (
                <div className={noPadding ? "card-grid-content" : ""} style={{ marginTop: 12 }}>
                    <div className="metric-grid">
                        <MetricCard label="Registros" value={summary.total_registros} />
                        <MetricCard label="Horas" value={summary.horas_totales.toFixed(1)} />
                        <MetricCard label="Errores" value={summary.total_errores} />
                        <MetricCard label="Score" value={`${summary.quality_score.toFixed(0)}%`} />
                    </div>
                </div>
            )}

            {typeof result.llm_enabled === "boolean" && (
                <div className={noPadding ? "card-text-content" : ""}>
                    <Typography variant="small" style={{ marginTop: 8 }}>
                        IA aplicada: {result.llm_enabled ? "Si" : "No"} - Correcciones IA: {result.llm_corrections_count ?? 0}
                    </Typography>
                </div>
            )}

            {baninterReport && (
                <details className="expander" style={!noPadding ? { marginTop: 12 } : {}}>
                    <summary>BANINTER - Imputaciones</summary>
                    <div className="expander-content">
                        <p>
                            Columnas de interes faltantes:{" "}
                            {Array.isArray(baninterReport.missing_optional_columns) &&
                                baninterReport.missing_optional_columns.length > 0
                                ? baninterReport.missing_optional_columns.join(", ")
                                : "Ninguna"}
                        </p>
                        <p>
                            Imputaciones: Fecha={baninterReport.filled_fecha ?? 0}, Proyecto={baninterReport.filled_proyecto ?? 0}, Fase={baninterReport.filled_fase ?? 0}
                        </p>
                        <p>
                            Filas validas: antes={baninterReport.valid_before ?? 0} ({Math.round((baninterReport.coverage_before ?? 0) * 100)}%), despues={baninterReport.valid_after ?? 0} ({Math.round((baninterReport.coverage_after ?? 0) * 100)}%)
                        </p>
                        {Array.isArray(baninterReport.warnings) && baninterReport.warnings.length > 0 && (
                            <ul style={{ paddingLeft: 20 }}>
                                {baninterReport.warnings.map((w: string, idx: number) => (
                                    <li key={idx}>{w}</li>
                                ))}
                            </ul>
                        )}
                    </div>
                </details>
            )}

            <div className={noPadding ? "card-text-content" : ""}>
                {result.download_id &&
                    result.output_filename &&
                    !(result.baninter_business_id && result.baninter_business_filename) && (
                        <div style={{ marginTop: 12 }}>
                            <Button variant="outline" onClick={() => onDownload(result.download_id, result.output_filename)}>
                                Descargar Excel
                            </Button>
                        </div>
                    )}
                {result.baninter_business_id && result.baninter_business_filename && (
                    <div style={{ marginTop: 8 }}>
                        <Button
                            variant="outline"
                            onClick={() =>
                                onDownload(result.baninter_business_id, result.baninter_business_filename)
                            }
                        >
                            Descargar Excel Business IT
                        </Button>
                    </div>
                )}
            </div>

            <details className="expander" style={!noPadding ? { marginTop: 12 } : {}}>
                <summary>Errores detectados ({result.errors?.length || 0})</summary>
                <div className="expander-content">
                    <ErrorsTable
                        errors={result.errors}
                        errorColWidths={errorColWidths}
                        onResizeStart={onResizeStart}
                    />
                </div>
            </details>
            {result.holiday_info && (
                <div className={noPadding ? "" : ""} style={!noPadding ? { marginTop: 12 } : {}}>
                    {renderHoliday(result.holiday_info)}
                </div>
            )}
        </div>
    );

};
