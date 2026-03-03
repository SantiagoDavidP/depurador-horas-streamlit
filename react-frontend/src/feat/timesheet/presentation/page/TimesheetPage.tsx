import React from "react";
import Plot from "react-plotly.js";
import { useTimesheetViewModel } from "../view_model/TimesheetViewModel";
import { ResultItem } from "../../domain/Timesheet";

// Atomic Design Imports
import { Typography } from "../../../../core/ui/design/atoms/Typography";
import { Button } from "../../../../core/ui/design/atoms/Button";
import { Toggle } from "../../../../core/ui/design/atoms/Toggle";
import { Select } from "../../../../core/ui/design/atoms/Select";
import { MetricCard } from "../../../../core/ui/design/molecules/MetricCard";
import { MainLayout } from "../../../../core/ui/design/templates/MainLayout";
import { ProgressPanel } from "../../../../core/ui/design/organisms/ProgressPanel";
import { FileUploader } from "../../../../core/ui/design/organisms/FileUploader";
import { ResultCard } from "../../../../core/ui/design/organisms/ResultCard";

export const TimesheetPage: React.FC = () => {
    const vm = useTimesheetViewModel();

    const consolidatedChart = (results: ResultItem[]) => {
        const rows = results.filter((r) => r.success && r.summary);
        if (rows.length <= 1) return null;
        const x = rows.map(
            (r) => r.employee_info?.metadata || r.employee_info?.final || r.sheet_name || r.file_name
        );
        const y = rows.map((r) => r.summary?.horas_totales || 0);
        const score = rows.map((r) => r.summary?.quality_score || 0);
        return (
            <Plot
                data={[
                    {
                        type: "bar",
                        x,
                        y,
                        marker: { color: score, colorscale: "RdYlGn" },
                    },
                ]}
                layout={{
                    paper_bgcolor: "rgba(0,0,0,0)",
                    plot_bgcolor: "rgba(0,0,0,0)",
                    font: { color: "var(--text-primary)", family: "Source Sans 3, sans-serif" },
                    margin: { t: 50, b: 40, l: 40, r: 20 },
                    title: "Horas por empleado",
                }}
                style={{ width: "100%", height: "360px" }}
                useResizeHandler
            />
        );
    };

    const consultantDetailTable = (results: ResultItem[]) => (
        <table className="table">
            <thead>
                <tr>
                    <th>Consultor</th>
                    <th>Registros</th>
                    <th>Horas</th>
                    <th>Errores</th>
                    <th>Score</th>
                </tr>
            </thead>
            <tbody>
                {results.map((r, idx) => (
                    <tr key={idx}>
                        <td>{r.employee_info?.final || r.sheet_name || r.file_name}</td>
                        <td>{r.summary?.total_registros ?? "-"}</td>
                        <td>{r.summary?.horas_totales?.toFixed(1) ?? "-"}</td>
                        <td>{r.summary?.total_errores ?? "-"}</td>
                        <td>
                            {r.summary?.quality_score?.toFixed(0)}%{" "}
                            <div className="progress-bar">
                                <span style={{ width: `${r.summary?.quality_score || 0}%` }} />
                            </div>
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );

    return (
        <MainLayout
            sidebar={{
                theme: vm.theme,
                onThemeToggle: vm.toggleTheme,
                processingMode: vm.processingMode,
                onModeChange: vm.setProcessingMode,
                volumeLabel: vm.volumeLabel,
                statusLabel: vm.statusLabel,
                userInfo: vm.userInfo as any,
                children: null // We could add more specific sidebar items here
            }}
            headerTitle={vm.processingMode === "Individual" ? "Procesamiento Individual" : "Procesamiento por Lotes"}
        >
            <section className="section grid">
                <FileUploader
                    title="Carga de Archivos"
                    files={vm.processingMode === "Individual" ? (vm.individualFile ? [vm.individualFile] : []) : vm.batchFiles}
                    multiple={vm.processingMode === "Por lotes"}
                    inputRef={vm.processingMode === "Por lotes" ? vm.batchInputRef : undefined}
                    onFileChange={(e) => {
                        if (vm.processingMode === "Individual") {
                            const file = e.target.files?.[0];
                            if (file) {
                                vm.setIndividualFile(file);
                                vm.handleIndividualAnalyze(file);
                            }
                        } else {
                            if (e.target.files) {
                                vm.setBatchFiles(Array.from(e.target.files));
                            }
                        }
                    }}
                    onRemoveFile={(i) => vm.processingMode === "Individual" ? vm.setIndividualFile(null) : vm.handleRemoveBatchFile(i)}
                />

                {vm.individualProcessing && vm.processingMode === "Individual" && (
                    <ProgressPanel
                        title="Analizando archivo..."
                        detail={vm.individualFile?.name || ""}
                        seconds={vm.individualElapsed}
                        pct={vm.individualProgressPct}
                        noPadding={true}
                    />
                )}
                {vm.individualError && vm.processingMode === "Individual" && <div className="error-box">{vm.individualError}</div>}

                {vm.batchProcessing && vm.processingMode === "Por lotes" && (
                    <ProgressPanel
                        title="Procesando archivos..."
                        detail={`${vm.batchFiles.length} archivos`}
                        seconds={vm.batchElapsed}
                        pct={vm.batchProgressPct}
                    />
                )}
                {vm.batchError && vm.processingMode === "Por lotes" && <div className="error-box">{vm.batchError}</div>}

                <div className="card">
                    <Typography variant="h3">Parametría</Typography>
                    <Toggle
                        label="Corrección con IA Activada"
                        checked={vm.correctSpelling}
                        onChange={(e) => vm.handleSpellingToggle(e.target.checked)}
                        style={{ marginBottom: 16 }}
                    />

                    <div className="field">
                        <Typography variant="label">Rol del Consultor</Typography>
                        <Select
                            value={vm.employeeRole}
                            onChange={(e) => vm.setEmployeeRole(e.target.value)}
                            options={[
                                { value: "Consultor", label: "Consultor" },
                                { value: "Arquitecto", label: "Arquitecto" },
                                { value: "Gerente", label: "Gerente" },
                                { value: "Desconocido", label: "Desconocido" }
                            ]}
                        />
                    </div>

                    <div className="field">
                        <Typography variant="label">Sensibilidad Duplicados: {vm.dupThreshold}%</Typography>
                        <input
                            type="range"
                            min="50" max="100"
                            value={vm.dupThreshold}
                            onChange={(e) => vm.setDupThreshold(Number(e.target.value))}
                        />
                    </div>
                </div>
            </section>

            <section className="section">
                <div className="flex-between" style={{ marginBottom: 16 }}>
                    <Typography variant="h2">Resultados</Typography>
                    <Button
                        variant="primary"
                        disabled={vm.processingMode === 'Individual' ? !vm.individualFile || vm.individualProcessing : vm.batchFiles.length === 0 || vm.batchProcessing}
                        onClick={vm.processingMode === 'Individual' ? vm.handleIndividualProcess : vm.handleBatchProcess}
                    >
                        Procesar Ahora
                    </Button>
                </div>

                {(vm.processingMode === "Individual" ? vm.individualResults : vm.batchResults).length > 0 && (
                    <div className="results-container">
                        <div className="results-list">
                            {(vm.processingMode === "Individual" ? vm.individualResults : vm.batchResults).map((res, i) => (
                                <ResultCard
                                    key={i}
                                    result={res}
                                    index={i}
                                    errorColWidths={vm.errorColWidths}
                                    onResizeStart={vm.handleResizeStart}
                                    onDownload={vm.handleDownload}
                                    noPadding={vm.processingMode === "Individual"}
                                />
                            ))}
                        </div>

                        <div className="results-analytics">
                            <div className="card">
                                <Typography variant="h3">Consolidado</Typography>
                                {consolidatedChart(vm.processingMode === "Individual" ? vm.individualResults : vm.batchResults)}
                                {consultantDetailTable(vm.processingMode === "Individual" ? vm.individualResults : vm.batchResults)}
                            </div>
                        </div>
                    </div>
                )}
            </section>
        </MainLayout>
    );
};
