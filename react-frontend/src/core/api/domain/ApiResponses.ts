import { ResultItem } from "../../../feat/timesheet/domain/Timesheet";

export interface AnalyzeBatchResponse {
    auto_profile_id?: string | null;
    profile_mapping?: Record<string, string>;
    profile_settings?: Record<string, unknown>;
    metadata?: Record<string, unknown>;
}

export interface AnalyzeIndividualResponse {
    sheets: {
        sheet_name: string;
        metadata: Record<string, unknown>;
        columns: string[];
        row_count: number;
        header_row: number;
    }[];
    skipped_sheets: string[];
    auto_profile_id?: string | null;
    is_nova: boolean;
    auto_area?: string | null;
    company?: string;
    employee_count: number;
}

export interface ProcessResponse {
    batch_id: string;
    results: ResultItem[];
    consolidated?: {
        download_id: string;
        filename: string;
        consultores: number;
        total_horas: number;
    };
    baninter_zip?: {
        download_id: string;
        filename: string;
    } | null;
    skipped_sheets?: { name: string; columns: string[] }[];
    is_baninter?: boolean;
    default_client_name?: string;
    auto_area?: string | null;
}

export interface ConsolidateResponse {
    download_id: string;
    filename: string;
    consultores: number;
    total_horas: number;
    warnings?: string[];
}
