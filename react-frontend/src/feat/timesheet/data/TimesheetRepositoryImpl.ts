import { ITimesheetRepository } from "../domain/ITimesheetRepository";
import { Profile } from "../domain/Timesheet";
import * as api from "../../../core/api/data/ApiService";
import {
    AnalyzeBatchResponse,
    AnalyzeIndividualResponse,
    ConsolidateResponse,
    ProcessResponse,
} from "../../../core/api/domain/ApiResponses";

export class TimesheetRepositoryImpl implements ITimesheetRepository {
    async getProfiles(): Promise<Profile[]> {
        return api.getProfiles();
    }

    async getMe(): Promise<Record<string, unknown> | null> {
        return api.getMe();
    }

    async analyzeBatch(files: File[]): Promise<AnalyzeBatchResponse> {
        return api.analyzeBatch(files);
    }

    async processBatch(files: File[], payload: Record<string, unknown>): Promise<ProcessResponse> {
        return api.processBatch(files, payload);
    }

    async analyzeIndividual(file: File): Promise<AnalyzeIndividualResponse> {
        return api.analyzeIndividual(file);
    }

    async processIndividual(file: File, payload: Record<string, unknown>): Promise<ProcessResponse> {
        return api.processIndividual(file, payload);
    }

    async consolidateBatch(payload: Record<string, unknown>): Promise<ConsolidateResponse> {
        return api.consolidateBatch(payload);
    }

    async buildBaninterZip(payload: Record<string, unknown>): Promise<{ download_id: string; filename: string }> {
        return api.buildBaninterZip(payload);
    }

    async downloadFile(fileId: string): Promise<Blob> {
        return api.downloadFile(fileId);
    }
}
