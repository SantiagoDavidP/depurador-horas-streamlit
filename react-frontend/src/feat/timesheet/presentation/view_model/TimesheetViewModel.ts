import { useState, useMemo, useEffect, useRef } from "react";
import { TimesheetRepositoryImpl } from "../../data/TimesheetRepositoryImpl";
import { Profile, ResultItem } from "../../domain/Timesheet";
import {
    AnalyzeBatchResponse,
    AnalyzeIndividualResponse,
    ConsolidateResponse,
    ProcessResponse,
} from "../../../../core/api/domain/ApiResponses";

type Mode = "Individual" | "Por lotes";

export const useTimesheetViewModel = () => {
    const repository = new TimesheetRepositoryImpl();

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
        repository.getProfiles().then(setProfiles).catch(() => undefined);
        repository.getMe().then(setUserInfo).catch(() => undefined);
    }, []);

    useEffect(() => {
        localStorage.setItem("theme_mode", theme);
    }, [theme]);

    // Batch Progress Timer
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

    // Individual Progress Timer
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

    // Resize column handlers
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

    // Batch analysis on file change
    useEffect(() => {
        if (batchFiles.length === 0) {
            setBatchAnalyzeInfo(null);
            setBatchProfileId("__manual__");
            setBatchMapping({ date: "", hours: "", description: "", project: "" });
            return;
        }

        repository.analyzeBatch(batchFiles)
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

    const toggleTheme = (isDark: boolean) => {
        setTheme(isDark ? "dark" : "light");
    };

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
            const response = await repository.processBatch(batchFiles, payload);
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
                    const zip = await repository.buildBaninterZip({ batchId: response.batch_id });
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
            const response = await repository.consolidateBatch({
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
        const blob = await repository.downloadFile(downloadId);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    };

    const handleIndividualAnalyze = async (file: File) => {
        setIndividualProcessing(true);
        setIndividualError(null);
        try {
            const analysis = await repository.analyzeIndividual(file);
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
            const response = await repository.processIndividual(individualFile, {
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

    const handleResizeStart = (index: number, event: React.MouseEvent) => {
        event.preventDefault();
        resizeRef.current = {
            index,
            startX: event.clientX,
            startWidth: errorColWidths[index] ?? 140,
        };
    };

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

    const handleRemoveBatchFile = (index: number) => {
        setBatchFiles((prev) => prev.filter((_, idx) => idx !== index));
        if (batchInputRef.current) {
            batchInputRef.current.value = "";
        }
    };

    const handleClearBatchFiles = () => {
        setBatchFiles([]);
        if (batchInputRef.current) {
            batchInputRef.current.value = "";
        }
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

    const [showTimeSuggestions, setShowTimeSuggestions] = useState(true);

    return {
        theme,
        toggleTheme,
        processingMode,
        setProcessingMode,
        profiles,
        userInfo,
        correctSpelling,
        setCorrectSpelling,
        employeeRole,
        setEmployeeRole,
        batchFiles,
        setBatchFiles,
        batchProfileId,
        setBatchProfileId,
        batchMapping,
        setBatchMapping,
        batchAnalyzeInfo,
        batchResults,
        batchId,
        batchProcessing,
        batchElapsed,
        batchProgressPct,
        batchError,
        batchWarning,
        batchConsolidated,
        batchConsolidating,
        batchBaninterZip,
        batchIsBaninter,
        batchClientName,
        setBatchClientName,
        batchAreaSelection,
        setBatchAreaSelection,
        batchOutputFilename,
        setBatchOutputFilename,
        dupThreshold,
        setDupThreshold,
        minDuplicates,
        setMinDuplicates,
        hoursTolerance,
        setHoursTolerance,
        showTimeSuggestions,
        setShowTimeSuggestions,
        individualFile,
        setIndividualFile,
        individualAnalysis,
        individualProcessing,
        individualElapsed,
        individualProgressPct,
        individualError,
        individualResults,
        individualBatchId,
        individualConsolidated,
        individualBaninterZip,
        individualSkipped,
        individualOutputFilename,
        setIndividualOutputFilename,
        errorColWidths,
        batchInputRef,
        individualSettings,
        setIndividualSettings,
        individualAreaSelection,
        setIndividualAreaSelection,
        handleBatchProcess,
        handleBatchConsolidate,
        handleDownload,
        handleIndividualAnalyze,
        handleIndividualProcess,
        handleResizeStart,
        handleSpellingToggle,
        handleRemoveBatchFile,
        handleClearBatchFiles,
        volumeLabel,
        statusLabel,
    };

};
