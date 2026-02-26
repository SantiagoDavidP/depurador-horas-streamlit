
import React, { useEffect, useMemo, useRef, useState } from "react";
import Plot from "react-plotly.js";
import {
  analyzeBatch,
  analyzeIndividual,
  buildBaninterZip,
  consolidateBatch,
  downloadFile,
  getMe,
  getProfiles,
  processBatch,
  processIndividual,
} from "./api";
import {
  AnalyzeBatchResponse,
  AnalyzeIndividualResponse,
  ConsolidateResponse,
  ProcessResponse,
  Profile,
  ResultItem,
} from "./types";
import { AuthGate } from "./auth";

type Mode = "Individual" | "Por lotes";

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};

const formatBytes = (bytes: number) => {
  if (!bytes) return "0 KB";
  const units = ["B", "KB", "MB", "GB"];
  const idx = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  const value = bytes / Math.pow(1024, idx);
  return `${value.toFixed(value >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
};

const App = () => {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = localStorage.getItem("theme_mode");
    return saved === "dark" ? "dark" : "light";
  });

  const [processingMode, setProcessingMode] = useState<Mode>("Individual");
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [userInfo, setUserInfo] = useState<Record<string, unknown> | null>(null);

  const [correctSpelling, setCorrectSpelling] = useState(true);
  const [employeeRole, setEmployeeRole] = useState("Desconocido");

  const [batchFiles, setBatchFiles] = useState<File[]>([]);
  const [batchProfileId, setBatchProfileId] = useState<string>("__manual__");
  const [batchMapping, setBatchMapping] = useState({
    date: "",
    hours: "",
    description: "",
    project: "",
  });
  const [batchProfileSettings, setBatchProfileSettings] = useState<Record<string, unknown>>({});
  const [batchAnalyzeInfo, setBatchAnalyzeInfo] = useState<AnalyzeBatchResponse | null>(null);
  const [batchResults, setBatchResults] = useState<ResultItem[]>([]);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [batchProcessing, setBatchProcessing] = useState(false);
  const [batchElapsed, setBatchElapsed] = useState(0);
  const [batchProgressPct, setBatchProgressPct] = useState(0);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [batchWarning, setBatchWarning] = useState<string | null>(null);
  const [batchConsolidated, setBatchConsolidated] = useState<ConsolidateResponse | null>(null);
  const [batchConsolidating, setBatchConsolidating] = useState(false);
  const [batchBaninterZip, setBatchBaninterZip] = useState<{ download_id: string; filename: string } | null>(null);
  const [batchIsBaninter, setBatchIsBaninter] = useState(false);
  const [batchClientName, setBatchClientName] = useState("NOVA - TI");
  const [batchAreaSelection, setBatchAreaSelection] = useState("Manual");
  const [batchOutputFilename, setBatchOutputFilename] = useState("");

  const [dupThreshold, setDupThreshold] = useState(90);
  const [minDuplicates, setMinDuplicates] = useState(3);
  const [hoursTolerance, setHoursTolerance] = useState(1.5);
  const [showTimeSuggestions, setShowTimeSuggestions] = useState(true);

  const [individualFile, setIndividualFile] = useState<File | null>(null);
  const [individualAnalysis, setIndividualAnalysis] = useState<AnalyzeIndividualResponse | null>(null);
  const [individualProcessing, setIndividualProcessing] = useState(false);
  const [individualElapsed, setIndividualElapsed] = useState(0);
  const [individualProgressPct, setIndividualProgressPct] = useState(0);
  const [individualError, setIndividualError] = useState<string | null>(null);
  const [individualResults, setIndividualResults] = useState<ResultItem[]>([]);
  const [individualBatchId, setIndividualBatchId] = useState<string | null>(null);
  const [individualConsolidated, setIndividualConsolidated] = useState<ProcessResponse["consolidated"] | null>(null);
  const [individualBaninterZip, setIndividualBaninterZip] = useState<{ download_id: string; filename: string } | null>(null);
  const [individualSkipped, setIndividualSkipped] = useState<{ name: string; columns: string[] }[]>([]);
  const [individualOutputFilename, setIndividualOutputFilename] = useState("");

  const [errorColWidths, setErrorColWidths] = useState([140, 180, 360, 220]);
  const resizeRef = useRef<{ index: number; startX: number; startWidth: number } | null>(null);
  const batchInputRef = useRef<HTMLInputElement | null>(null);

  const [individualSettings, setIndividualSettings] = useState({
    correctSpelling: true,
    duplicateSimilarityThreshold: 90,
    duplicateMinOccurrences: 3,
    hoursToleranceFactor: 1.5,
    role: "Consultor",
  });
  const [individualAreaSelection, setIndividualAreaSelection] = useState("Manual");

  const profileMap = useMemo(() => {
    const map: Record<string, Profile> = {};
    profiles.forEach((p) => (map[p.client_id] = p));
    return map;
  }, [profiles]);

  useEffect(() => {
    getProfiles().then(setProfiles).catch(() => undefined);
    getMe().then(setUserInfo).catch(() => undefined);
  }, []);

  useEffect(() => {
    localStorage.setItem("theme_mode", theme);
  }, [theme]);

  useEffect(() => {
    if (!batchProcessing) {
      setBatchElapsed(0);
      setBatchProgressPct(0);
      return;
    }
    const start = Date.now();
    const interval = window.setInterval(() => {
      const elapsed = Math.floor((Date.now() - start) / 1000);
      setBatchElapsed(elapsed);
      const expected = Math.max(12, batchFiles.length * 8);
      const ratio = Math.min(0.95, elapsed / expected);
      setBatchProgressPct(Math.floor(ratio * 100));
    }, 1000);
    return () => window.clearInterval(interval);
  }, [batchProcessing, batchFiles.length]);

  useEffect(() => {
    if (!individualProcessing) {
      setIndividualElapsed(0);
      setIndividualProgressPct(0);
      return;
    }
    const start = Date.now();
    const interval = window.setInterval(() => {
      const elapsed = Math.floor((Date.now() - start) / 1000);
      setIndividualElapsed(elapsed);
      const count = individualAnalysis?.employee_count || 1;
      const expected = Math.max(10, count * 8);
      const ratio = Math.min(0.95, elapsed / expected);
      setIndividualProgressPct(Math.floor(ratio * 100));
    }, 1000);
    return () => window.clearInterval(interval);
  }, [individualProcessing, individualAnalysis?.employee_count]);

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      if (!resizeRef.current) return;
      const { index, startX, startWidth } = resizeRef.current;
      const delta = event.clientX - startX;
      const nextWidth = Math.max(90, startWidth + delta);
      setErrorColWidths((prev) => {
        const copy = [...prev];
        copy[index] = nextWidth;
        return copy;
      });
    };

    const handleMouseUp = () => {
      resizeRef.current = null;
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);
  useEffect(() => {
    if (batchFiles.length === 0) {
      setBatchAnalyzeInfo(null);
      setBatchProfileId("__manual__");
      setBatchMapping({ date: "", hours: "", description: "", project: "" });
      return;
    }

    analyzeBatch(batchFiles)
      .then((info) => {
        setBatchAnalyzeInfo(info);
        if (info.auto_profile_id) {
          setBatchProfileId(info.auto_profile_id);
          setBatchMapping({
            date: info.profile_mapping?.date || "",
            hours: info.profile_mapping?.hours || "",
            description: info.profile_mapping?.description || "",
            project: info.profile_mapping?.project || "",
          });
          setBatchProfileSettings(info.profile_settings || {});
        }
      })
      .catch(() => undefined);
  }, [batchFiles]);

  useEffect(() => {
    if (batchProfileId !== "__manual__" && profileMap[batchProfileId]) {
      const profile = profileMap[batchProfileId];
      setBatchMapping({
        date: profile.mapping.date || "",
        hours: profile.mapping.hours || "",
        description: profile.mapping.description || "",
        project: profile.mapping.project || "",
      });
      setBatchProfileSettings(profile.settings || {});
    }
  }, [batchProfileId, profileMap]);

  const handleBatchProcess = async () => {
    if (batchFiles.length === 0) return;
    setBatchProcessing(true);
    setBatchError(null);
    setBatchWarning(null);
    setBatchResults([]);
    setBatchConsolidated(null);
    setBatchBaninterZip(null);
    try {
      const payload = {
        profileId: batchProfileId === "__manual__" ? null : batchProfileId,
        mappingValues: batchMapping,
        settings: {
          correctSpelling,
          duplicateSimilarityThreshold: dupThreshold,
          duplicateMinOccurrences: minDuplicates,
          hoursToleranceFactor: hoursTolerance,
          role: employeeRole,
        },
        maxWorkers: 4,
      };
      const response = await processBatch(batchFiles, payload);
      setBatchResults(response.results || []);
      setBatchId(response.batch_id);
      setBatchIsBaninter(!!response.is_baninter);
      setBatchClientName(response.default_client_name || "NOVA - TI");
      setBatchAreaSelection(
        response.auto_area === "CD"
          ? "NOVA - Centro Digital"
          : response.auto_area === "TI"
          ? "NOVA - TI (BIT Nova)"
          : "Manual"
      );

      const successfulResults = (response.results || []).filter((r) => r.success);
      const isBaninterResult = (result: ResultItem) => {
        const clientId = String(result.client_id || "").toLowerCase();
        const metadata = (result.metadata || {}) as Record<string, unknown>;
        const company = String(metadata.company || "").toLowerCase();
        const fileName = String(result.file_name || "").toLowerCase();
        return (
          clientId === "cliente_talent" ||
          company.includes("baninter") ||
          company.includes("banco internacional") ||
          fileName.includes("baninter")
        );
      };

      const hasBaninter = successfulResults.some((result) => isBaninterResult(result));
      const hasOtherClient = successfulResults.some((result) => !isBaninterResult(result));

      if (hasBaninter && hasOtherClient) {
        setBatchWarning(
          "Se detectaron dos clientes distintos (BANINTER y NOVA) en el mismo lote. Por favor procese un solo cliente por carga."
        );
      }

      if (response.is_baninter && response.batch_id && hasBaninter && !hasOtherClient) {
        try {
          const zip = await buildBaninterZip({ batchId: response.batch_id });
          setBatchBaninterZip(zip);
        } catch {
          setBatchBaninterZip(null);
        }
      }
      setBatchProgressPct(100);
    } catch (err: any) {
      setBatchError(err?.message || "Error procesando por lotes.");
    } finally {
      setBatchProcessing(false);
    }
  };

  const handleBatchConsolidate = async () => {
    if (!batchId) return;
    setBatchConsolidating(true);
    try {
      const clientName =
        batchAreaSelection === "NOVA - TI (BIT Nova)"
          ? "BIT Nova - TI"
          : batchAreaSelection === "NOVA - Centro Digital"
          ? "NOVA - Centro Digital"
          : batchClientName;
      const response = await consolidateBatch({
        batchId,
        clientName,
        outputFilename: batchOutputFilename || undefined,
      });
      setBatchConsolidated(response);
      if (response.filename) {
        setBatchOutputFilename(response.filename);
      }
    } catch (err: any) {
      setBatchError(err?.message || "Error generando consolidado.");
    } finally {
      setBatchConsolidating(false);
    }
  };

  const handleDownload = async (downloadId?: string, filename?: string) => {
    if (!downloadId || !filename) return;
    const blob = await downloadFile(downloadId);
    downloadBlob(blob, filename);
  };

  const handleIndividualAnalyze = async (file: File) => {
    setIndividualProcessing(true);
    setIndividualError(null);
    try {
      const analysis = await analyzeIndividual(file);
      setIndividualAnalysis(analysis);
      setIndividualAreaSelection(
        analysis.auto_area === "CD"
          ? "NOVA - Centro Digital"
          : analysis.auto_area === "TI"
          ? "NOVA - TI (BIT Nova)"
          : "Manual"
      );
    } catch (err: any) {
      setIndividualError(err?.message || "No se pudo analizar el archivo.");
    } finally {
      setIndividualProcessing(false);
    }
  };

  const handleIndividualProcess = async () => {
    if (!individualFile) return;
    setIndividualProcessing(true);
    setIndividualError(null);
    setIndividualResults([]);
    setIndividualConsolidated(null);
    setIndividualBaninterZip(null);
    try {
      const consultantsCount = Math.max(1, individualAnalysis?.employee_count || 1);
      const workerCap = individualSettings.correctSpelling ? 4 : 8;
      const individualWorkers = Math.min(workerCap, consultantsCount);
      const response = await processIndividual(individualFile, {
        settings: individualSettings,
        profileId: individualAnalysis?.auto_profile_id || null,
        areaSelection: individualAreaSelection,
        maxWorkers: individualWorkers,
      });
      setIndividualResults(response.results || []);
      setIndividualBatchId(response.batch_id);
      setIndividualConsolidated(response.consolidated || null);
      setIndividualBaninterZip(response.baninter_zip || null);
      setIndividualSkipped(response.skipped_sheets || []);
      if (response.consolidated?.filename) {
        setIndividualOutputFilename(response.consolidated.filename);
      }
      setIndividualProgressPct(100);
    } catch (err: any) {
      setIndividualError(err?.message || "Error procesando archivo.");
    } finally {
      setIndividualProcessing(false);
    }
  };
  const formatDuration = (seconds: number) => {
    if (!seconds || seconds < 0) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const renderProgressPanel = (
    title: string,
    detail: string,
    seconds: number,
    pct: number,
    currentLabel?: string,
    currentIndex?: number,
    total?: number
  ) => {
    return (
      <div className="progress-panel">
        <div className="progress-head">
          <div>
            <div className="progress-title">{title}</div>
            <div className="progress-subtitle">{detail}</div>
          </div>
          <div className="progress-time">Tiempo: {formatDuration(seconds)}</div>
        </div>
        {currentLabel && typeof currentIndex === "number" && total ? (
          <div className="progress-current">
            Procesando: <strong>{currentLabel}</strong> ({currentIndex + 1}/{total})
          </div>
        ) : null}
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
          <div className="progress-bar-animate" />
        </div>
        <div className="progress-caption">Progreso estimado: {pct}%</div>
      </div>
    );
  };
  const handleResizeStart = (index: number, event: React.MouseEvent) => {
    event.preventDefault();
    resizeRef.current = {
      index,
      startX: event.clientX,
      startWidth: errorColWidths[index] ?? 140,
    };
  };

  const aiEnabled =
    processingMode === "Individual"
      ? individualSettings.correctSpelling
      : correctSpelling;
  const spellingToggleChecked =
    processingMode === "Individual"
      ? individualSettings.correctSpelling
      : correctSpelling;
  const handleSpellingToggle = (checked: boolean) => {
    if (processingMode === "Individual") {
      setIndividualSettings((prev) => ({
        ...prev,
        correctSpelling: checked,
      }));
      setIndividualResults([]);
      setIndividualConsolidated(null);
      setIndividualBaninterZip(null);
    } else {
      setCorrectSpelling(checked);
      setBatchResults([]);
      setBatchConsolidated(null);
      setBatchBaninterZip(null);
      setBatchWarning(null);
    }
  };
  const resetBatchInput = () => {
    if (batchInputRef.current) {
      batchInputRef.current.value = "";
    }
  };
  const handleRemoveBatchFile = (index: number) => {
    setBatchFiles((prev) => prev.filter((_, idx) => idx !== index));
    resetBatchInput();
  };
  const handleClearBatchFiles = () => {
    setBatchFiles([]);
    resetBatchInput();
  };
  const volumeLabel =
    processingMode === "Individual"
      ? individualAnalysis?.employee_count
        ? `${individualAnalysis.employee_count} consultor(es)`
        : individualFile
        ? "1 archivo"
        : "Sin archivo"
      : batchFiles.length
      ? `${batchFiles.length} archivo(s)`
      : "Sin archivos";
  const statusLabel =
    processingMode === "Individual"
      ? individualProcessing
        ? "Procesando"
        : individualFile
        ? "Listo"
        : "Sin carga"
      : batchProcessing
      ? "Procesando"
      : batchFiles.length
      ? "Listo"
      : "Sin carga";

  const renderErrorsTable = (errors?: Record<string, unknown>[]) => {
    if (!errors || errors.length === 0) {
      return <div className="status-card">Sin errores detectados.</div>;
    }
    const headers = ["Fecha", "Tipo", "Descripción", "Valor"];
    return (
      <div className="table-wrap">
        <table className="table table-errors">
          <colgroup>
            {headers.map((_, idx) => (
              <col key={idx} style={{ width: errorColWidths[idx] || 140 }} />
            ))}
          </colgroup>
          <tbody>
            <tr className="table-header-row">
              {headers.map((label, idx) => (
                <th key={label} scope="col" className="resizable-cell">
                  <div className="cell-resize">
                    <span className="cell-content">{label}</span>
                    <span
                      className="col-resizer"
                      onMouseDown={(event) => handleResizeStart(idx, event)}
                    />
                  </div>
                </th>
              ))}
            </tr>
            {errors.map((row, idx) => {
              const values = [
                String(row["fecha"] ?? ""),
                String(row["tipo_error"] ?? ""),
                String(row["descripcion"] ?? ""),
                String(row["valor_original"] ?? ""),
              ];
              return (
                <tr key={idx}>
                  {values.map((value, colIdx) => (
                    <td key={colIdx} className="resizable-cell">
                      <div className="cell-resize">
                        <span className="cell-content">{value}</span>
                        <span
                          className="col-resizer"
                          onMouseDown={(event) =>
                            handleResizeStart(colIdx, event)
                          }
                        />
                      </div>
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  const renderHoliday = (holidayInfo: ResultItem["holiday_info"]) => {
    if (!holidayInfo) return null;
    return (
      <details className="expander">
        <summary>Feriados del mes</summary>
        <div className="expander-content">
          <strong>Mes analizado:</strong> {holidayInfo.month_label}
          {holidayInfo.holidays.length === 0 ? (
            <p className="small">Sin feriados registrados.</p>
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

  const renderResultCard = (result: ResultItem, index: number) => {
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

    return (
      <div key={`${result.file_name}-${index}`} className="card" style={{ marginBottom: 16 }}>
        <div className="flex-between">
          <h3 style={{ margin: 0 }}>{employeeName}</h3>
          <span className="tag">Score: {score.toFixed(0)}%</span>
        </div>

        {metadataItems.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <details className="expander">
              <summary>Metadata</summary>
              <div className="expander-content">
                <div className="info-grid">
                  {metadataItems.map((item) => (
                    <div key={item.label} className="info-item">
                      <div className="info-label">{item.label}</div>
                      <div className="info-value">{item.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </details>
          </div>
        )}

        {summary && (
          <div className="metric-grid" style={{ marginTop: 12 }}>
            <div className="metric-card">
              <div className="metric-label">Registros</div>
              <div className="metric-value">{summary.total_registros}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Horas</div>
              <div className="metric-value">{summary.horas_totales.toFixed(1)}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Errores</div>
              <div className="metric-value">{summary.total_errores}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Score</div>
              <div className="metric-value">{summary.quality_score.toFixed(0)}%</div>
            </div>
          </div>
        )}
        {typeof result.llm_enabled === "boolean" && (
          <p className="small" style={{ marginTop: 8 }}>
            IA aplicada: {result.llm_enabled ? "Si" : "No"} - Correcciones IA: {result.llm_corrections_count ?? 0}
          </p>
        )}

        {baninterReport && (
          <div style={{ marginTop: 12 }}>
            <details className="expander">
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
                  <ul>
                    {baninterReport.warnings.map((w: string, idx: number) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                )}
              </div>
            </details>
          </div>
        )}

        {result.download_id &&
          result.output_filename &&
          !(result.baninter_business_id && result.baninter_business_filename) && (
          <div style={{ marginTop: 12 }}>
            <button className="button outline" onClick={() => handleDownload(result.download_id, result.output_filename)}>
              Descargar Excel
            </button>
          </div>
        )}
        {result.baninter_business_id && result.baninter_business_filename && (
          <div style={{ marginTop: 8 }}>
            <button
              className="button outline"
              onClick={() =>
                handleDownload(result.baninter_business_id, result.baninter_business_filename)
              }
            >
              Descargar Excel Business IT
            </button>
          </div>
        )}

        <div style={{ marginTop: 12 }}>
          <details className="expander">
            <summary>Errores detectados ({result.errors?.length || 0})</summary>
            <div className="expander-content">{renderErrorsTable(result.errors)}</div>
          </details>
        </div>
        <div style={{ marginTop: 12 }}>{renderHoliday(result.holiday_info)}</div>
      </div>
    );
  };

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
    <AuthGate>
      <div className={`app ${theme === "dark" ? "theme-dark" : ""}`}>
        <aside className="sidebar">
          <div className="brand">
            <div className="brand-logo-wrap">
              <img src="/logobit.png" className="brand-logo" alt="Business IT" />
            </div>
            <div className="brand-text">
              <div className="brand-subtitle">Timesheet Intelligence</div>
            </div>
          </div>
          <div className="brand-divider" />
          <div className="sidebar-section">
            <h3 style={{ marginTop: 0 }}>Apariencia</h3>
            <div className="toggle">
              <input
                type="checkbox"
                checked={theme === "dark"}
                onChange={(e) => setTheme(e.target.checked ? "dark" : "light")}
              />
              <span>Tema {theme === "dark" ? "Oscuro" : "Claro"}</span>
            </div>
          </div>

          <div className="sidebar-section">
            <h3 style={{ marginBottom: 8 }}>Configuración</h3>
            <div className="label">Modo</div>
            <div className="flex">
              <label>
                <input
                  type="radio"
                  checked={processingMode === "Individual"}
                  onChange={() => setProcessingMode("Individual")}
                />
                Individual
              </label>
              <label>
                <input
                  type="radio"
                  checked={processingMode === "Por lotes"}
                  onChange={() => setProcessingMode("Por lotes")}
                />
                Por lotes
              </label>
            </div>
            <div style={{ marginTop: 10 }}>
              <div className="ai-toggle">
                <div className="ai-toggle-row">
                  <span className="ai-toggle-title">Corrección ortográfica</span>
                  <span className="tag">IA</span>
                  <label className="ai-toggle-control">
                    <input
                      type="checkbox"
                      checked={spellingToggleChecked}
                      onChange={(e) => handleSpellingToggle(e.target.checked)}
                      aria-label="Corrección ortográfica"
                    />
                  </label>
                </div>
              </div>
            </div>
            <div style={{ marginTop: 10 }}>
              {processingMode === "Por lotes" && (
                <details className="expander">
                  <summary>Configuración avanzada</summary>
                  <div className="expander-content">
                    <div className="label">Sensibilidad duplicados</div>
                    <input
                      type="range"
                      min={70}
                      max={100}
                      value={dupThreshold}
                      onChange={(e) => setDupThreshold(Number(e.target.value))}
                    />
                    <div className="small">{dupThreshold}%</div>
                    <div className="label" style={{ marginTop: 8 }}>
                      Mínimo repeticiones
                    </div>
                    <input
                      className="input"
                      type="number"
                      min={1}
                      value={minDuplicates}
                      onChange={(e) => setMinDuplicates(Number(e.target.value))}
                    />
                    <div className="label" style={{ marginTop: 8 }}>
                      Tolerancia horas
                    </div>
                    <input
                      type="range"
                      min={1}
                      max={3}
                      step={0.1}
                      value={hoursTolerance}
                      onChange={(e) => setHoursTolerance(Number(e.target.value))}
                    />
                    <div className="small">{hoursTolerance.toFixed(1)}</div>
                    <label className="flex" style={{ marginTop: 8 }}>
                      <input
                        type="checkbox"
                        checked={showTimeSuggestions}
                        onChange={(e) => setShowTimeSuggestions(e.target.checked)}
                      />
                      Mostrar referencias de tiempo
                    </label>
                  </div>
                </details>
              )}
            </div>
          </div>

          {processingMode === "Por lotes" && (
            <div className="sidebar-section">
              <h3>Archivos</h3>
              <input
                className="input"
                type="file"
                multiple
                accept=".xlsx,.xls"
                ref={batchInputRef}
                onChange={(e) => {
                  setBatchFiles(Array.from(e.target.files || []));
                }}
              />
              {batchFiles.length > 0 ? (
                <p className="small">{batchFiles.length} archivo(s) cargado(s)</p>
              ) : (
                <p className="small">Sin archivos cargados.</p>
              )}

              <hr className="divider" />

              <h4>Cliente</h4>
              <select value={batchProfileId} onChange={(e) => setBatchProfileId(e.target.value)}>
                <option value="__manual__">Mapeo manual</option>
                {profiles.map((p) => (
                  <option key={p.client_id} value={p.client_id}>
                    {p.name}
                  </option>
                ))}
              </select>

              {batchProfileId === "__manual__" ? (
                <div style={{ marginTop: 12 }}>
                  <div className="label">Mapeo manual</div>
                  <input
                    className="input"
                    placeholder="Fecha"
                    value={batchMapping.date}
                    onChange={(e) => setBatchMapping({ ...batchMapping, date: e.target.value })}
                  />
                  <input
                    className="input"
                    placeholder="Horas"
                    value={batchMapping.hours}
                    onChange={(e) => setBatchMapping({ ...batchMapping, hours: e.target.value })}
                    style={{ marginTop: 6 }}
                  />
                  <input
                    className="input"
                    placeholder="Descripción"
                    value={batchMapping.description}
                    onChange={(e) => setBatchMapping({ ...batchMapping, description: e.target.value })}
                    style={{ marginTop: 6 }}
                  />
                  <input
                    className="input"
                    placeholder="Proyecto"
                    value={batchMapping.project}
                    onChange={(e) => setBatchMapping({ ...batchMapping, project: e.target.value })}
                    style={{ marginTop: 6 }}
                  />
                </div>
              ) : (
                <div style={{ marginTop: 12 }}>
                  <div className="label">Mapeo detectado</div>
                  <ul className="small">
                    {Object.entries(batchMapping).map(([key, val]) => (
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
            <label className="label">Rol del empleado</label>
            <select value={employeeRole} onChange={(e) => setEmployeeRole(e.target.value)}>
              <option>Desconocido</option>
              <option>Developer</option>
              <option>QA</option>
              <option>DevOps</option>
              <option>Project Manager</option>
              <option>Otro</option>
            </select>
          </div>

          {userInfo && (
            <div className="sidebar-section">
              <hr className="divider" />
              <h4>Usuario</h4>
              <p style={{ margin: 0 }}>{String(userInfo["displayName"] || "Usuario")}</p>
              <p className="small">{String(userInfo["mail"] || userInfo["userPrincipalName"] || "")}</p>
            </div>
          )}
        </aside>

        <main className="main">
          <div className="header">
            <div className="header-brand">
              <div className="header-accent" aria-hidden="true" />
              <div>
                <div className="header-eyebrow">Business IT · Nova Analytics</div>
                <h1 className="gradient-title">Depurador de Horas</h1>
                <p className="header-subtitle">Valida y depura registros de timesheet automáticamente</p>
              </div>
            </div>
            <div className="header-status">
              <div className="status-pill">
                <span className="status-label-inline">Modo</span>
                <span className="status-value-inline">{processingMode}</span>
              </div>
              <div className="status-pill">
                <span className="status-label-inline">IA</span>
                <span className="status-value-inline">
                  <span className={`status-dot ${aiEnabled ? "on" : "off"}`} />
                  {aiEnabled ? "Activa" : "Inactiva"}
                </span>
              </div>
              <div className="status-pill">
                <span className="status-label-inline">Carga</span>
                <span className="status-value-inline">
                  {volumeLabel} · {statusLabel}
                </span>
              </div>
            </div>
          </div>

          {processingMode === "Individual" ? (
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
                  setIndividualFile(file);
                  setIndividualAnalysis(null);
                  setIndividualResults([]);
                  setIndividualConsolidated(null);
                  if (file) handleIndividualAnalyze(file);
                }}
              />

              {!individualFile && (
                <div className="empty-state" style={{ marginTop: 16 }}>
                  <div className="empty-title">Tu reporte en segundos</div>
                  <div className="empty-desc">Sube tu Excel y el sistema ordena, valida y consolida automáticamente.</div>
                </div>
              )}

              {individualAnalysis && (
                <>
                  <div style={{ marginTop: 16 }}>
                    {individualAnalysis.employee_count > 1 ? (
                      <div className="status-card">Se detectaron {individualAnalysis.employee_count} empleados.</div>
                    ) : (
                      <div className="status-card">Hoja detectada: {individualAnalysis.sheets[0]?.sheet_name}</div>
                    )}
                  </div>

                  <div className="section-header" style={{ marginTop: 16 }}>
                    <h2 className="section-header-title">Configuración</h2>
                  </div>

                  <details className="expander">
                    <summary>Configuración avanzada</summary>
                    <div className="expander-content">
                      <div className="flex">
                        <label className="flex">
                          <input
                            type="checkbox"
                            checked={individualSettings.correctSpelling}
                            onChange={(e) =>
                              setIndividualSettings((prev) => ({
                                ...prev,
                                correctSpelling: e.target.checked,
                              }))
                            }
                          />
                          Corrección con IA
                        </label>
                      </div>
                      <div className="label" style={{ marginTop: 8 }}>
                        Sensibilidad duplicados
                      </div>
                      <input
                        type="range"
                        min={70}
                        max={100}
                        value={individualSettings.duplicateSimilarityThreshold}
                        onChange={(e) =>
                          setIndividualSettings((prev) => ({
                            ...prev,
                            duplicateSimilarityThreshold: Number(e.target.value),
                          }))
                        }
                      />
                      <div className="small">{individualSettings.duplicateSimilarityThreshold}%</div>
                      <div className="label" style={{ marginTop: 8 }}>
                        Mínimo repeticiones
                      </div>
                      <input
                        className="input"
                        type="number"
                        min={1}
                        value={individualSettings.duplicateMinOccurrences}
                        onChange={(e) =>
                          setIndividualSettings((prev) => ({
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
                        value={individualSettings.hoursToleranceFactor}
                        onChange={(e) =>
                          setIndividualSettings((prev) => ({
                            ...prev,
                            hoursToleranceFactor: Number(e.target.value),
                          }))
                        }
                      />
                      <div className="small">{individualSettings.hoursToleranceFactor.toFixed(1)}</div>
                      <div className="label" style={{ marginTop: 8 }}>
                        Rol
                      </div>
                      <select
                        value={individualSettings.role}
                        onChange={(e) =>
                          setIndividualSettings((prev) => ({ ...prev, role: e.target.value }))
                        }
                      >
                        <option>Consultor</option>
                        <option>Developer</option>
                        <option>Manager</option>
                      </select>
                    </div>
                  </details>

                  {individualAnalysis.is_nova && (
                    <div style={{ marginTop: 12 }}>
                      <div className="label">Cliente / Area</div>
                      <select value={individualAreaSelection} onChange={(e) => setIndividualAreaSelection(e.target.value)}>
                        <option>NOVA - TI (BIT Nova)</option>
                        <option>NOVA - Centro Digital</option>
                        <option>Manual</option>
                      </select>
                      {individualAnalysis.auto_area && (
                        <p className="small">
                          Detectado automáticamente: {individualAnalysis.auto_area === "CD" ? "NOVA - Centro Digital" : "NOVA - TI (BIT Nova)"}
                        </p>
                      )}
                    </div>
                  )}

                  <div style={{ marginTop: 16 }}>
                    <button className="button primary full" onClick={handleIndividualProcess} disabled={individualProcessing}>
                      PROCESAR {individualAnalysis.employee_count} CONSULTORES
                    </button>
                  </div>
                </>
              )}

              {individualProcessing &&
                renderProgressPanel(
                  "Procesando archivo",
                  `Analizando ${individualAnalysis?.employee_count || 1} consultor(es).`,
                  individualElapsed,
                  individualProgressPct,
                  (() => {
                    const sheets = individualAnalysis?.sheets || [];
                    const total = sheets.length || individualAnalysis?.employee_count || 1;
                    const expected = Math.max(10, total * 8);
                    const ratio = Math.min(0.99, individualElapsed / expected);
                    const idx = Math.min(total - 1, Math.floor(ratio * total));
                    if (sheets[idx]?.sheet_name) return sheets[idx].sheet_name;
                    return `Consultor ${idx + 1}`;
                  })(),
                  (() => {
                    const sheets = individualAnalysis?.sheets || [];
                    const total = sheets.length || individualAnalysis?.employee_count || 1;
                    const expected = Math.max(10, total * 8);
                    const ratio = Math.min(0.99, individualElapsed / expected);
                    return Math.min(total - 1, Math.floor(ratio * total));
                  })(),
                  individualAnalysis?.sheets?.length || individualAnalysis?.employee_count || 1
                )}
              {individualError && <div className="status-card error">{individualError}</div>}

              {individualResults.length > 0 && (
                <>
                  <hr className="divider" />
                  {individualSkipped.length > 0 && (
                    <details className="expander" style={{ marginBottom: 12 }}>
                      <summary>Hojas ignoradas</summary>
                      <div className="expander-content">
                        <ul>
                          {individualSkipped.map((item, idx) => (
                            <li key={idx}>
                              {item.name} - Columnas: {item.columns.join(", ")}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </details>
                  )}
                  <h3>Detalle Individual</h3>
                  {individualResults.map((result, idx) => renderResultCard(result, idx))}

                  <hr className="divider" />
                  <h3>Detalle por Consultor</h3>
                  {consultantDetailTable(individualResults)}
                  {individualResults.length > 1 && (
                    <>
                      <hr className="divider" />
                      {consolidatedChart(individualResults)}
                    </>
                  )}

                  <hr className="divider" />
                  {individualBaninterZip ? (
                    <div>
                      <h3>Descarga BANINTER</h3>
                      <button
                        className="button primary full"
                        onClick={() => handleDownload(individualBaninterZip.download_id, individualBaninterZip.filename)}
                      >
                        DESCARGAR INDIVIDUALES BANINTER (ZIP)
                      </button>
                    </div>
                  ) : (
                    <div>
                      <h3>Reporte listo</h3>
                      {individualConsolidated && (
                        <div className="metric-grid" style={{ marginBottom: 12 }}>
                          <div className="metric-card">
                            <div className="metric-label">Horas totales</div>
                            <div className="metric-value">
                              {individualConsolidated.total_horas.toFixed(1)} h
                            </div>
                          </div>
                          <div className="metric-card">
                            <div className="metric-label">Consultores</div>
                            <div className="metric-value">{individualConsolidated.consultores}</div>
                          </div>
                        </div>
                      )}
                      {individualConsolidated && (
                        <>
                          <div className="label" style={{ marginTop: 8 }}>
                            Nombre del Excel
                          </div>
                          <input
                            className="input"
                            placeholder="Consolidado_Consultores.xlsx"
                            value={individualOutputFilename}
                            onChange={(e) => setIndividualOutputFilename(e.target.value)}
                          />
                          <div className="highlight-card" style={{ marginTop: 12 }}>
                            <div className="highlight-title">Consolidado listo</div>
                            <div className="highlight-subtitle">
                              Entrega lista para revisión del cliente.
                            </div>
                            <div className="highlight-name">
                              Nombre: {individualOutputFilename || individualConsolidated.filename}
                            </div>
                            <div className="highlight-actions">
                              <button
                                className="button primary full download-glow"
                                onClick={() =>
                                  handleDownload(
                                    individualConsolidated.download_id,
                                    individualOutputFilename || individualConsolidated.filename
                                  )
                                }
                              >
                                DESCARGAR EXCEL CONSOLIDADO
                              </button>
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </>
              )}
            </>
          ) : (
            <>
              {batchFiles.length > 0 && (
                <details className="expander" style={{ marginBottom: 12 }}>
                  <summary>Archivos cargados ({batchFiles.length})</summary>
                  <div className="expander-content">
                    <div className="file-panel" style={{ marginTop: 0 }}>
                      <div className="file-panel-head">
                        <div className="small">Lista de archivos</div>
                        <button className="btn btn-ghost btn-xs" onClick={handleClearBatchFiles}>
                          Limpiar todo
                        </button>
                      </div>
                      <div className="file-list">
                        {batchFiles.map((file, idx) => (
                          <div className="file-row" key={`${file.name}-${idx}`}>
                            <div className="file-meta">
                              <div className="file-name">{file.name}</div>
                              <div className="file-size">{formatBytes(file.size)}</div>
                            </div>
                            <button
                              className="btn btn-ghost btn-xs"
                              onClick={() => handleRemoveBatchFile(idx)}
                            >
                              Quitar
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </details>
              )}
              {batchFiles.length === 0 && (
                <div className="empty-state">
                  <div className="empty-title">Listo para procesar cuando tú también lo estés</div>
                </div>
              )}
              {batchFiles.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <button className="button primary full" onClick={handleBatchProcess} disabled={batchProcessing}>
                    Procesar {batchFiles.length} archivo(s)
                  </button>
                  {batchProcessing &&
                    renderProgressPanel(
                      "Procesamiento por lotes",
                      `Procesando ${batchFiles.length} archivo(s).`,
                      batchElapsed,
                      batchProgressPct,
                      (() => {
                        const total = batchFiles.length || 1;
                        const expected = Math.max(12, total * 8);
                        const ratio = Math.min(0.99, batchElapsed / expected);
                        const idx = Math.min(total - 1, Math.floor(ratio * total));
                        return batchFiles[idx]?.name || `Archivo ${idx + 1}`;
                      })(),
                      (() => {
                        const total = batchFiles.length || 1;
                        const expected = Math.max(12, total * 8);
                        const ratio = Math.min(0.99, batchElapsed / expected);
                        return Math.min(total - 1, Math.floor(ratio * total));
                      })(),
                      batchFiles.length || 1
                    )}
                  {batchError && <div className="status-card error">{batchError}</div>}
                  {batchWarning && <div className="status-card">{batchWarning}</div>}
                </div>
              )}

              {batchResults.length > 0 && (
                <>
                  <h3>
                    Resultados ({batchResults.filter((r) => r.success).length}/{batchFiles.length})
                  </h3>
                  {batchResults.map((result, idx) => renderResultCard(result, idx))}

                  {showTimeSuggestions && (
                    <p className="small">
                      Referencias: Daily ~0.25h - Reuniones 0.25-3h - Dev 1-8h - Review 0.25-2h
                    </p>
                  )}

                  <hr className="divider" />
                  <h3>Detalle por Consultor</h3>
                  {consultantDetailTable(batchResults)}

                  {batchResults.length > 1 && (
                    <>
                      <hr className="divider" />
                      <h3>Reporte consolidado</h3>
                      <div className="metric-grid" style={{ marginBottom: 12 }}>
                        <div className="metric-card">
                          <div className="metric-label">Empleados</div>
                          <div className="metric-value">{batchResults.length}</div>
                        </div>
                        <div className="metric-card">
                          <div className="metric-label">Horas</div>
                          <div className="metric-value">
                            {batchResults
                              .reduce((acc, r) => acc + (r.summary?.horas_totales || 0), 0)
                              .toFixed(1)} h
                          </div>
                        </div>
                        <div className="metric-card">
                          <div className="metric-label">Score promedio</div>
                          <div className="metric-value">
                            {(
                              batchResults.reduce((acc, r) => acc + (r.summary?.quality_score || 0), 0) /
                              batchResults.length
                            ).toFixed(0)}%
                          </div>
                        </div>
                      </div>
                      {consolidatedChart(batchResults)}
                      {!batchIsBaninter && (
                        <>
                          <hr className="divider" />
                          <h3>Generar consolidado Excel</h3>
                          <div className="card">
                            <div className="label">Nombre del cliente</div>
                            <input
                              className="input"
                              value={batchClientName}
                              onChange={(e) => setBatchClientName(e.target.value)}
                            />
                            <div className="label" style={{ marginTop: 8 }}>
                              Area
                            </div>
                            <select value={batchAreaSelection} onChange={(e) => setBatchAreaSelection(e.target.value)}>
                              <option>NOVA - TI (BIT Nova)</option>
                              <option>NOVA - Centro Digital</option>
                              <option>Manual</option>
                            </select>
                            <div className="label" style={{ marginTop: 8 }}>
                              Nombre del Excel
                            </div>
                            <input
                              className="input"
                              placeholder="Consolidado_Cliente_Mes_Anio.xlsx"
                              value={batchOutputFilename}
                              onChange={(e) => setBatchOutputFilename(e.target.value)}
                            />
                            <div style={{ marginTop: 12 }}>
                              <button
                                className="button primary full"
                                onClick={handleBatchConsolidate}
                                disabled={batchConsolidating}
                              >
                                {batchConsolidating ? "Generando consolidado..." : "Generar Consolidado"}
                              </button>
                            </div>
                            {batchConsolidating && (
                              <div className="loading-inline">
                                <span className="spinner" aria-hidden="true" />
                                Generando consolidado. Esto puede tardar unos segundos.
                              </div>
                            )}
                          </div>
                          {batchConsolidated && (
                            <div className="highlight-card">
                              <div className="highlight-title">Consolidado listo</div>
                              <div className="highlight-subtitle">
                                Entrega lista para revisión del cliente.
                              </div>
                              <div className="highlight-name">
                                Nombre: {batchOutputFilename || batchConsolidated.filename}
                              </div>
                              <div className="highlight-actions">
                                <button
                                  className="button primary full download-glow"
                                  onClick={() =>
                                    handleDownload(
                                      batchConsolidated.download_id,
                                      batchOutputFilename || batchConsolidated.filename
                                    )
                                  }
                                >
                                  DESCARGAR EXCEL CONSOLIDADO
                                </button>
                              </div>
                            </div>
                          )}
                        </>
                      )}
                      {batchIsBaninter && batchBaninterZip && (
                        <>
                          <hr className="divider" />
                          <h3>Descarga BANINTER</h3>
                          <button
                            className="button primary full"
                            onClick={() => handleDownload(batchBaninterZip.download_id, batchBaninterZip.filename)}
                          >
                            DESCARGAR INDIVIDUALES BANINTER (ZIP)
                          </button>
                        </>
                      )}
                    </>
                  )}
                </>
              )}
            </>
          )}
        </main>
      </div>
    </AuthGate>
  );
};

export default App;
