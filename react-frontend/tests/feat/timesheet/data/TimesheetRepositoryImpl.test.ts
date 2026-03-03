import { vi, describe, it, expect, beforeEach } from "vitest";
import { TimesheetRepositoryImpl } from "@/feat/timesheet/data/TimesheetRepositoryImpl";
import * as api from "@/core/api/data/ApiService";

vi.mock("@/core/api/data/ApiService", () => ({
    getProfiles: vi.fn(),
    getMe: vi.fn(),
    analyzeBatch: vi.fn(),
    processBatch: vi.fn(),
    analyzeIndividual: vi.fn(),
    processIndividual: vi.fn(),
    consolidateBatch: vi.fn(),
    buildBaninterZip: vi.fn(),
    downloadFile: vi.fn(),
}));

describe("TimesheetRepositoryImpl", () => {
    let repository: TimesheetRepositoryImpl;

    beforeEach(() => {
        repository = new TimesheetRepositoryImpl();
        vi.clearAllMocks();
    });

    it("should call api.getProfiles", async () => {
        await repository.getProfiles();
        expect(api.getProfiles).toHaveBeenCalled();
    });

    it("should call api.getMe", async () => {
        await repository.getMe();
        expect(api.getMe).toHaveBeenCalled();
    });

    it("should call api.analyzeBatch", async () => {
        const files = [new File([""], "test.xlsx")];
        await repository.analyzeBatch(files);
        expect(api.analyzeBatch).toHaveBeenCalledWith(files);
    });

    it("should call api.processBatch", async () => {
        const files = [new File([""], "test.xlsx")];
        const payload = { profile_id: "1" };
        await repository.processBatch(files, payload);
        expect(api.processBatch).toHaveBeenCalledWith(files, payload);
    });

    it("should call api.analyzeIndividual", async () => {
        const file = new File([""], "test.xlsx");
        await repository.analyzeIndividual(file);
        expect(api.analyzeIndividual).toHaveBeenCalledWith(file);
    });

    it("should call api.processIndividual", async () => {
        const file = new File([""], "test.xlsx");
        const payload = { profile_id: "1" };
        await repository.processIndividual(file, payload);
        expect(api.processIndividual).toHaveBeenCalledWith(file, payload);
    });

    it("should call api.consolidateBatch", async () => {
        const payload = { batch_id: "1" };
        await repository.consolidateBatch(payload);
        expect(api.consolidateBatch).toHaveBeenCalledWith(payload);
    });

    it("should call api.buildBaninterZip", async () => {
        const payload = { batch_id: "1" };
        await repository.buildBaninterZip(payload);
        expect(api.buildBaninterZip).toHaveBeenCalledWith(payload);
    });

    it("should call api.downloadFile", async () => {
        await repository.downloadFile("123");
        expect(api.downloadFile).toHaveBeenCalledWith("123");
    });
});
