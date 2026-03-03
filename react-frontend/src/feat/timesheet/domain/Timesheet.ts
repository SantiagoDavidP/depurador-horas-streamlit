export interface Profile {
    client_id: string;
    name: string;
    mapping: Record<string, string>;
    settings: Record<string, unknown>;
    keywords: string[];
    company_aliases: string[];
}

export interface Summary {
    total_registros: number;
    total_errores: number;
    horas_totales: number;
    dias_con_problemas_horas: number;
    errores_por_tipo: Record<string, number>;
    metadata_removidas?: number;
    errores_criticos?: number;
    errores_advertencia?: number;
    quality_score: number;
    ai_summary?: Record<string, unknown>;
    role_coherence_score?: number;
    role_validation_details?: Record<string, unknown>[];
}

export interface HolidayInfo {
    month: number;
    year: number;
    month_label: string;
    holidays: { date: string; name: string }[];
    source: string;
}

export interface EmployeeInfo {
    metadata?: string | null;
    filename?: string | null;
    final?: string | null;
}

export interface ResultItem {
    file_name: string;
    sheet_name?: string | null;
    success: boolean;
    error?: string | null;
    client_id?: string | null;
    metadata?: Record<string, unknown>;
    summary?: Summary;
    errors?: Record<string, unknown>[];
    download_id?: string;
    output_filename?: string;
    employee_info?: EmployeeInfo;
    holiday_info?: HolidayInfo | null;
    baninter_business_id?: string;
    baninter_business_filename?: string;
    llm_enabled?: boolean;
    llm_corrections_count?: number;
}
