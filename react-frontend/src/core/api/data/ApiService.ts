import { AuthRepositoryImpl } from "../../../feat/auth/data/AuthRepositoryImpl";
import { Profile } from "../../../feat/timesheet/domain/Timesheet";
import {
    AnalyzeBatchResponse,
    AnalyzeIndividualResponse,
    ConsolidateResponse,
    ProcessResponse,
} from "../domain/ApiResponses";

const baseUrl = import.meta.env.VITE_API_BASE_URL || "";
const authRepo = new AuthRepositoryImpl();

const parseErrorDetail = async (res: Response, fallback: string): Promise<string> => {
    const raw = await res.text();
    if (!raw) return fallback;
    try {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed.detail === "string" && parsed.detail.trim()) {
            return parsed.detail;
        }
    } catch {
        // noop
    }
    return raw || fallback;
};

const withAuth = async (headers: HeadersInit = {}) => {
    const token = await authRepo.getAccessToken();
    if (token) {
        return {
            ...headers,
            Authorization: `Bearer ${token}`,
        };
    }
    return headers;
};

export const getProfiles = async (): Promise<Profile[]> => {
    const res = await fetch(`${baseUrl}/api/profiles`, {
        headers: await withAuth(),
    });
    const data = await res.json();
    return data.profiles || [];
};

export const getMe = async (): Promise<Record<string, unknown> | null> => {
    const res = await fetch(`${baseUrl}/api/me`, { headers: await withAuth() });
    if (!res.ok) return null;
    const data = await res.json();
    return data.user || null;
};

export const analyzeBatch = async (
    files: File[]
): Promise<AnalyzeBatchResponse> => {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    const res = await fetch(`${baseUrl}/api/batch/analyze`, {
        method: "POST",
        body: form,
        headers: await withAuth(),
    });
    if (!res.ok) throw new Error("No se pudo analizar los archivos.");
    return res.json();
};

export const processBatch = async (
    files: File[],
    payload: Record<string, unknown>
): Promise<ProcessResponse> => {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    form.append("payload", JSON.stringify(payload));
    const res = await fetch(`${baseUrl}/api/batch/process`, {
        method: "POST",
        body: form,
        headers: await withAuth(),
    });
    if (!res.ok) {
        const detail = await parseErrorDetail(res, "Error procesando por lotes.");
        throw new Error(detail);
    }
    return res.json();
};

export const analyzeIndividual = async (
    file: File
): Promise<AnalyzeIndividualResponse> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${baseUrl}/api/individual/analyze`, {
        method: "POST",
        body: form,
        headers: await withAuth(),
    });
    if (!res.ok) throw new Error("No se pudo analizar el archivo.");
    return res.json();
};

export const processIndividual = async (
    file: File,
    payload: Record<string, unknown>
): Promise<ProcessResponse> => {
    const form = new FormData();
    form.append("file", file);
    form.append("payload", JSON.stringify(payload));
    const res = await fetch(`${baseUrl}/api/individual/process`, {
        method: "POST",
        body: form,
        headers: await withAuth(),
    });
    if (!res.ok) {
        const detail = await parseErrorDetail(res, "Error procesando archivo.");
        throw new Error(detail);
    }
    return res.json();
};

export const consolidateBatch = async (
    payload: Record<string, unknown>
): Promise<ConsolidateResponse> => {
    const res = await fetch(`${baseUrl}/api/batch/consolidate`, {
        method: "POST",
        headers: await withAuth({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
    });
    if (!res.ok) {
        const detail = await parseErrorDetail(res, "Error generando consolidado.");
        throw new Error(detail);
    }
    return res.json();
};

export const buildBaninterZip = async (
    payload: Record<string, unknown>
): Promise<{ download_id: string; filename: string }> => {
    const res = await fetch(`${baseUrl}/api/batch/baninter-zip`, {
        method: "POST",
        headers: await withAuth({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
    });
    if (!res.ok) {
        const detail = await parseErrorDetail(res, "Error generando ZIP BANINTER.");
        throw new Error(detail);
    }
    return res.json();
};

export const downloadFile = async (fileId: string): Promise<Blob> => {
    const res = await fetch(`${baseUrl}/api/download/${fileId}`, {
        headers: await withAuth(),
    });
    if (!res.ok) throw new Error("No se pudo descargar el archivo.");
    return res.blob();
};
