import { Profile } from "./Timesheet";
import {
    AnalyzeBatchResponse,
    AnalyzeIndividualResponse,
    ConsolidateResponse,
    ProcessResponse,
} from "../../../core/api/domain/ApiResponses";

export interface ITimesheetRepository {
    getProfiles(): Promise<Profile[]>;
    getMe(): Promise<Record<string, unknown> | null>;
    analyzeBatch(files: File[]): Promise<AnalyzeBatchResponse>;
    processBatch(files: File[], payload: Record<string, unknown>): Promise<ProcessResponse>;
    analyzeIndividual(file: File): Promise<AnalyzeIndividualResponse>;
    processIndividual(file: File, payload: Record<string, unknown>): Promise<ProcessResponse>;
    consolidateBatch(payload: Record<string, unknown>): Promise<ConsolidateResponse>;
    buildBaninterZip(payload: Record<string, unknown>): Promise<{ download_id: string; filename: string }>;
    downloadFile(fileId: string): Promise<Blob>;
}
