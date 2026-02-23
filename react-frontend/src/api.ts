import { getAccessToken } from "./auth";
import {
  AnalyzeBatchResponse,
  AnalyzeIndividualResponse,
  ConsolidateResponse,
  ProcessResponse,
  Profile,
} from "./types";

const baseUrl = import.meta.env.VITE_API_BASE_URL || "";

const withAuth = async (headers: HeadersInit = {}) => {
  const token = await getAccessToken();
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
    const detail = await res.text();
    throw new Error(detail || "Error procesando por lotes.");
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
    const detail = await res.text();
    throw new Error(detail || "Error procesando archivo.");
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
    const detail = await res.text();
    throw new Error(detail || "Error generando consolidado.");
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
    const detail = await res.text();
    throw new Error(detail || "Error generando ZIP BANINTER.");
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
