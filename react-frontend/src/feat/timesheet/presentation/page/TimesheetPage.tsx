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

    const aiEnabled = vm.processingMode === "Individual" ? vm.individualSettings.correctSpelling : vm.correctSpelling;

    return (
        <MainLayout
            sidebar={{
                theme: vm.theme,
                onThemeToggle: vm.toggleTheme,
                processingMode: vm.processingMode,
                onModeChange: vm.setProcessingMode,
                userInfo: vm.userInfo as any,
                children: (
                    <>
                        <div className="sidebar-section">
                            <div className="ai-toggle">
                                <div className="ai-toggle-row">
                                    <span className="ai-toggle-title">Corrección ortográfica</span>
                                    <span className="tag">IA</span>
                                    <label className="ai-toggle-control">
                                        <input
                                            type="checkbox"
                                            checked={aiEnabled}
                                            onChange={(e) => vm.handleSpellingToggle(e.target.checked)}
                                        />
                                    </label>
                                </div>
                            </div>

                            {vm.processingMode === "Por lotes" && (
                                <div style={{ marginTop: 10 }}>
                                    <details className="expander">
                                        <summary>Configuración avanzada</summary>
                                        <div className="expander-content">
                                            <div className="label">Sensibilidad duplicados</div>
                                            <input
                                                type="range"
                                                min={70}
                                                max={100}
                                                value={vm.dupThreshold}
                                                onChange={(e) => vm.setDupThreshold(Number(e.target.value))}
                                            />
                                            <div className="small">{vm.dupThreshold}%</div>

                                            <div className="label" style={{ marginTop: 8 }}>
                                                Mínimo repeticiones
                                            </div>
                                            <input
                                                className="input"
                                                type="number"
                                                min={1}
                                                value={vm.minDuplicates}
                                                onChange={(e) => vm.setMinDuplicates(Number(e.target.value))}
                                            />

                                            <div className="label" style={{ marginTop: 8 }}>
                                                Tolerancia horas
                                            </div>
                                            <input
                                                type="range"
                                                min={1}
                                                max={3}
                                                step={0.1}
                                                value={vm.hoursTolerance}
                                                onChange={(e) => vm.setHoursTolerance(Number(e.target.value))}
                                            />
                                            <div className="small">{vm.hoursTolerance.toFixed(1)}</div>

                                            <label className="flex" style={{ marginTop: 8 }}>
                                                <input
                                                    type="checkbox"
                                                    checked={vm.showTimeSuggestions}
                                                    onChange={(e) => vm.setShowTimeSuggestions(e.target.checked)}
                                                />
                                                <span className="small">Mostrar referencias de tiempo</span>
                                            </label>
                                        </div>
                                    </details>
                                </div>
                            )}
                        </div>

                        {vm.processingMode === "Por lotes" && (
                            <div className="sidebar-section">
                                <Typography variant="h3">Archivos</Typography>
                                <input
                                    className="input"
                                    type="file"
                                    multiple
                                    accept=".xlsx,.xls"
                                    ref={vm.batchInputRef}
                                    onChange={(e) => {
                                        if (e.target.files) {
                                            vm.setBatchFiles(Array.from(e.target.files));
                                        }
                                    }}
                                />
                                {vm.batchFiles.length > 0 ? (
                                    <p className="small">{vm.batchFiles.length} archivo(s) cargado(s)</p>
                                ) : (
                                    <p className="small">Sin archivos cargados.</p>
                                )}

                                <div className="divider" style={{ margin: "14px 0" }} />

                                <Typography variant="h3" style={{ marginBottom: 4 }}>Cliente</Typography>
                                <Select
                                    value={vm.batchProfileId}
                                    onChange={(e) => vm.setBatchProfileId(e.target.value)}
                                    options={[
                                        { value: "__manual__", label: "Mapeo manual" },
                                        ...vm.profiles.map(p => ({ value: p.client_id, label: p.name }))
                                    ]}
                                />

                                {vm.batchProfileId === "__manual__" ? (
                                    <div style={{ marginTop: 12 }}>
                                        <div className="label">Mapeo manual</div>
                                        <input
                                            className="input"
                                            placeholder="Fecha"
                                            value={vm.batchMapping.date}
                                            onChange={(e) => vm.setBatchMapping({ ...vm.batchMapping, date: e.target.value })}
                                        />
                                        <input
                                            className="input"
                                            placeholder="Horas"
                                            value={vm.batchMapping.hours}
                                            onChange={(e) => vm.setBatchMapping({ ...vm.batchMapping, hours: e.target.value })}
                                            style={{ marginTop: 6 }}
                                        />
                                        <input
                                            className="input"
                                            placeholder="Descripción"
                                            value={vm.batchMapping.description}
                                            onChange={(e) => vm.setBatchMapping({ ...vm.batchMapping, description: e.target.value })}
                                            style={{ marginTop: 6 }}
                                        />
                                        <input
                                            className="input"
                                            placeholder="Proyecto"
                                            value={vm.batchMapping.project}
                                            onChange={(e) => vm.setBatchMapping({ ...vm.batchMapping, project: e.target.value })}
                                            style={{ marginTop: 6 }}
                                        />
                                    </div>
                                ) : (
                                    <div style={{ marginTop: 12 }}>
                                        <div className="label">Mapeo detectado</div>
                                        <ul className="small" style={{ listStyle: "disc", paddingLeft: 16 }}>
                                            {Object.entries(vm.batchMapping).map(([key, val]) => (
                                                <li key={key}>
                                                    <strong>{key}</strong>: {val}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        )}

                        <div className="sidebar-section">
                            <Typography variant="label">Rol del empleado</Typography>
                            <Select
                                value={vm.employeeRole}
                                onChange={(e) => vm.setEmployeeRole(e.target.value)}
                                options={[
                                    { value: "Desconocido", label: "Desconocido" },
                                    { value: "Developer", label: "Developer" },
                                    { value: "QA", label: "QA" },
                                    { value: "DevOps", label: "DevOps" },
                                    { value: "Project Manager", label: "Project Manager" },
                                    { value: "Otro", label: "Otro" }
                                ]}
                            />
                        </div>
                    </>
                )
            }}
            volumeLabel={vm.volumeLabel}
            statusLabel={vm.statusLabel}
            aiEnabled={aiEnabled}
        >
            <div className="main-content-inner">
                {vm.processingMode === "Individual" ? (
                    <>
                        <div className="section-header">
                            <h2 className="section-header-title">Cargar archivo</h2>
                        </div>
                        <input
                            className="input"
                            type="file"
                            accept=".xlsx,.xls"
                            onChange={(e) => {
                                const file = e.target.files?.[0] || null;
                                vm.setIndividualFile(file);
                                if (file) vm.handleIndividualAnalyze(file);
                            }}
                        />

                        {!vm.individualFile && (
                            <div className="empty-state" style={{ marginTop: 16 }}>
                                <div className="empty-title">Tu reporte en segundos</div>
                                <div className="empty-desc">Sube tu Excel y el sistema ordena, valida y consolida automáticamente.</div>
                            </div>
                        )}

                        {vm.individualAnalysis && (
                            <>
                                <div style={{ marginTop: 16 }}>
                                    {vm.individualAnalysis.employee_count > 1 ? (
                                        <div className="status-card">Se detectaron {vm.individualAnalysis.employee_count} empleados.</div>
                                    ) : (
                                        <div className="status-card">Hoja detectada: {vm.individualAnalysis.sheets[0]?.sheet_name}</div>
                                    )}
                                </div>

                                <div className="section-header" style={{ marginTop: 16 }}>
                                    <h2 className="section-header-title">Configuración</h2>
                                </div>

                                <details className="expander">
                                    <summary>Configuración avanzada</summary>
                                    <div className="expander-content">
                                        <div className="label">Sensibilidad duplicados</div>
                                        <input
                                            type="range"
                                            min={70}
                                            max={100}
                                            value={vm.individualSettings.duplicateSimilarityThreshold}
                                            onChange={(e) =>
                                                vm.setIndividualSettings((prev) => ({
                                                    ...prev,
                                                    duplicateSimilarityThreshold: Number(e.target.value),
                                                }))
                                            }
                                        />
                                        <div className="small">{vm.individualSettings.duplicateSimilarityThreshold}%</div>

                                        <div className="label" style={{ marginTop: 8 }}>
                                            Mínimo repeticiones
                                        </div>
                                        <input
                                            className="input"
                                            type="number"
                                            min={1}
                                            value={vm.individualSettings.duplicateMinOccurrences}
                                            onChange={(e) =>
                                                vm.setIndividualSettings((prev) => ({
                                                    ...prev,
                                                    duplicateMinOccurrences: Number(e.target.value),
                                                }))
                                            }
                                        />

                                        <div className="label" style={{ marginTop: 8 }}>
                                            Tolerancia horas
                                        </div>
                                        <input
                                            type="range"
                                            min={1}
                                            max={3}
                                            step={0.1}
                                            value={vm.individualSettings.hoursToleranceFactor}
                                            onChange={(e) =>
                                                vm.setIndividualSettings((prev) => ({
                                                    ...prev,
                                                    hoursToleranceFactor: Number(e.target.value),
                                                }))
                                            }
                                        />
                                        <div className="small">{vm.individualSettings.hoursToleranceFactor.toFixed(1)}</div>
                                    </div>
                                </details>

                                {vm.individualAnalysis.is_nova && (
                                    <div style={{ marginTop: 12 }}>
                                        <div className="label">Cliente / Area</div>
                                        <Select
                                            value={vm.individualAreaSelection}
                                            onChange={(e) => vm.setIndividualAreaSelection(e.target.value)}
                                            options={[
                                                { value: "NOVA - TI (BIT Nova)", label: "NOVA - TI (BIT Nova)" },
                                                { value: "NOVA - Centro Digital", label: "NOVA - Centro Digital" },
                                                { value: "Manual", label: "Manual" }
                                            ]}
                                        />
                                    </div>
                                )}

                                <div style={{ marginTop: 16 }}>
                                    <Button
                                        variant="primary"
                                        className="full big"
                                        onClick={vm.handleIndividualProcess}
                                        disabled={vm.individualProcessing}
                                    >
                                        PROCESAR {vm.individualAnalysis.employee_count} CONSULTORES
                                    </Button>
                                </div>
                            </>
                        )}

                        {vm.individualProcessing && (
                            <ProgressPanel
                                title="Procesando archivo..."
                                detail={`Analizando ${vm.individualAnalysis?.employee_count || 1} consultor(es).`}
                                seconds={vm.individualElapsed}
                                pct={vm.individualProgressPct}
                            />
                        )}
                        {vm.individualError && <div className="status-card error" style={{ marginTop: 16 }}>{vm.individualError}</div>}

                        {vm.individualResults.length > 0 && (
                            <div style={{ marginTop: 24 }}>
                                <Typography variant="h2">Detalle Individual</Typography>
                                {vm.individualResults.map((res, i) => (
                                    <ResultCard
                                        key={i}
                                        result={res}
                                        index={i}
                                        errorColWidths={vm.errorColWidths}
                                        onResizeStart={vm.handleResizeStart}
                                        onDownload={vm.handleDownload}
                                        noPadding={true}
                                    />
                                ))}

                                <div className="divider" />
                                <Typography variant="h2">Detalle por Consultor</Typography>
                                <div className="card">
                                    {consultantDetailTable(vm.individualResults)}
                                </div>

                                {vm.individualResults.length > 1 && (
                                    <div className="card">
                                        <Typography variant="h3">Consolidado</Typography>
                                        {consolidatedChart(vm.individualResults)}
                                    </div>
                                )}

                                <div className="divider" />
                                {vm.individualBaninterZip ? (
                                    <div>
                                        <Typography variant="h2">Descarga BANINTER</Typography>
                                        <Button
                                            variant="primary"
                                            className="full big download-glow"
                                            onClick={() => vm.handleDownload(vm.individualBaninterZip?.download_id, vm.individualBaninterZip?.filename)}
                                        >
                                            DESCARGAR INDIVIDUALES BANINTER (ZIP)
                                        </Button>
                                    </div>
                                ) : vm.individualConsolidated && (
                                    <div>
                                        <Typography variant="h2">Reporte listo</Typography>
                                        <div className="metric-grid" style={{ marginBottom: 12 }}>
                                            <MetricCard label="Horas totales" value={`${vm.individualConsolidated.total_horas.toFixed(1)} h`} />
                                            <MetricCard label="Consultores" value={vm.individualConsolidated.consultores.toString()} />
                                        </div>
                                        <div className="highlight-card">
                                            <div className="highlight-title">Consolidado listo</div>
                                            <div className="highlight-subtitle">Entrega lista para revisión del cliente.</div>
                                            <div style={{ marginTop: 16 }}>
                                                <Button
                                                    variant="primary"
                                                    className="full big download-glow"
                                                    onClick={() => vm.handleDownload(vm.individualConsolidated?.download_id, vm.individualConsolidated?.filename)}
                                                >
                                                    DESCARGAR EXCEL CONSOLIDADO
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </>
                ) : (
                    <>
                        {vm.batchFiles.length === 0 && (
                            <div className="empty-state">
                                <div className="empty-title">Listo para procesar cuando tú también lo estés</div>
                            </div>
                        )}

                        {vm.batchFiles.length > 0 && (
                            <div style={{ marginBottom: 20 }}>
                                <Button
                                    variant="primary"
                                    className="full big"
                                    onClick={vm.handleBatchProcess}
                                    disabled={vm.batchProcessing}
                                >
                                    PROCESAR {vm.batchFiles.length} ARCHIVO(S)
                                </Button>
                            </div>
                        )}

                        {vm.batchProcessing && (
                            <ProgressPanel
                                title="Procesamiento por lotes"
                                detail={`Procesando ${vm.batchFiles.length} archivo(s).`}
                                seconds={vm.batchElapsed}
                                pct={vm.batchProgressPct}
                            />
                        )}
                        {vm.batchError && <div className="status-card error" style={{ marginTop: 16 }}>{vm.batchError}</div>}
                        {vm.batchWarning && <div className="status-card" style={{ marginTop: 16 }}>{vm.batchWarning}</div>}

                        {vm.batchResults.length > 0 && (
                            <div style={{ marginTop: 24 }}>
                                <Typography variant="h2">Resultados ({vm.batchResults.filter(r => r.success).length}/{vm.batchFiles.length})</Typography>
                                {vm.batchResults.map((res, i) => (
                                    <ResultCard
                                        key={i}
                                        result={res}
                                        index={i}
                                        errorColWidths={vm.errorColWidths}
                                        onResizeStart={vm.handleResizeStart}
                                        onDownload={vm.handleDownload}
                                    />
                                ))}

                                {vm.showTimeSuggestions && (
                                    <p className="small" style={{ marginTop: 12, opacity: 0.8 }}>
                                        Referencias: Daily ~0.25h - Reuniones 0.25-3h - Dev 1-8h - Review 0.25-2h
                                    </p>
                                )}

                                <div className="divider" />
                                <Typography variant="h2">Detalle por Consultor</Typography>
                                <div className="card">
                                    {consultantDetailTable(vm.batchResults)}
                                </div>

                                {vm.batchResults.length > 1 && (
                                    <>
                                        <div className="divider" />
                                        <Typography variant="h2">Reporte consolidado</Typography>
                                        <div className="metric-grid" style={{ marginBottom: 12 }}>
                                            <MetricCard label="Empleados" value={vm.batchResults.length.toString()} />
                                            <MetricCard
                                                label="Horas"
                                                value={`${vm.batchResults.reduce((acc, r) => acc + (r.summary?.horas_totales || 0), 0).toFixed(1)} h`}
                                            />
                                            <MetricCard
                                                label="Score promedio"
                                                value={`${(vm.batchResults.reduce((acc, r) => acc + (r.summary?.quality_score || 0), 0) / vm.batchResults.length).toFixed(0)}%`}
                                            />
                                        </div>
                                        <div className="card">
                                            {consolidatedChart(vm.batchResults)}
                                        </div>

                                        {!vm.batchIsBaninter && (
                                            <>
                                                <div className="divider" />
                                                <Typography variant="h2">Generar consolidado Excel</Typography>
                                                <div className="card">
                                                    <div className="label">Nombre del cliente</div>
                                                    <input
                                                        className="input"
                                                        value={vm.batchClientName}
                                                        onChange={(e) => vm.setBatchClientName(e.target.value)}
                                                    />
                                                    <div className="label" style={{ marginTop: 8 }}>Area</div>
                                                    <Select
                                                        value={vm.batchAreaSelection}
                                                        onChange={(e) => vm.setBatchAreaSelection(e.target.value)}
                                                        options={[
                                                            { value: "NOVA - TI (BIT Nova)", label: "NOVA - TI (BIT Nova)" },
                                                            { value: "NOVA - Centro Digital", label: "NOVA - Centro Digital" },
                                                            { value: "Manual", label: "Manual" }
                                                        ]}
                                                    />
                                                    <div className="label" style={{ marginTop: 12 }}>
                                                        <Button
                                                            variant="primary"
                                                            className="full"
                                                            onClick={vm.handleBatchConsolidate}
                                                            disabled={vm.batchConsolidating}
                                                        >
                                                            {vm.batchConsolidating ? "Generando..." : "GENERAR CONSOLIDADO"}
                                                        </Button>
                                                    </div>
                                                </div>
                                                {vm.batchConsolidated && (
                                                    <div className="highlight-card">
                                                        <div className="highlight-title">Consolidado listo</div>
                                                        <div className="highlight-subtitle">Entrega lista para revisión del cliente.</div>
                                                        <div style={{ marginTop: 16 }}>
                                                            <Button
                                                                variant="primary"
                                                                className="full big download-glow"
                                                                onClick={() => vm.handleDownload(vm.batchConsolidated?.download_id, vm.batchConsolidated?.filename)}
                                                            >
                                                                DESCARGAR EXCEL CONSOLIDADO
                                                            </Button>
                                                        </div>
                                                    </div>
                                                )}
                                            </>
                                        )}

                                        {vm.batchIsBaninter && vm.batchBaninterZip && (
                                            <>
                                                <div className="divider" />
                                                <Typography variant="h2">Descarga BANINTER</Typography>
                                                <Button
                                                    variant="primary"
                                                    className="full big download-glow"
                                                    onClick={() => vm.handleDownload(vm.batchBaninterZip?.download_id, vm.batchBaninterZip?.filename)}
                                                >
                                                    DESCARGAR INDIVIDUALES BANINTER (ZIP)
                                                </Button>
                                            </>
                                        )}
                                    </>
                                )}
                            </div>
                        )}
                    </>
                )}
            </div>
        </MainLayout>
    );
};

