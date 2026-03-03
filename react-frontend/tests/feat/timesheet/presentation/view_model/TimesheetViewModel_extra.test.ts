import { renderHook, act, cleanup } from "@testing-library/react";
import { useTimesheetViewModel } from "@/feat/timesheet/presentation/view_model/TimesheetViewModel";
import { TimesheetRepositoryImpl } from "@/feat/timesheet/data/TimesheetRepositoryImpl";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";

const { mockTimesheetRepository } = vi.hoisted(() => ({
    mockTimesheetRepository: {
        getProfiles: vi.fn().mockResolvedValue([{ client_id: "1", client_name: "Client 1" }]),
        getMe: vi.fn().mockResolvedValue({ name: "Test User" }),
        analyzeBatch: vi.fn().mockResolvedValue({
            auto_profile_id: "p1",
            profile_mapping: { date: "A", hours: "B" }
        }),
        processBatch: vi.fn().mockResolvedValue({ results: [], batch_id: "b1", is_baninter: false }),
        buildBaninterZip: vi.fn().mockResolvedValue({ download_id: "zip1", filename: "test.zip" }),
        consolidateBatch: vi.fn().mockResolvedValue({ filename: "results.xlsx" }),
        downloadFile: vi.fn().mockResolvedValue(new Blob(["test"])),
        analyzeIndividual: vi.fn().mockResolvedValue({ employee_count: 5 }),
        processIndividual: vi.fn().mockResolvedValue({ results: [], batch_id: "indiv1" }),
    }
}));

vi.mock("@/feat/timesheet/data/TimesheetRepositoryImpl", () => {
    return {
        TimesheetRepositoryImpl: vi.fn().mockImplementation(function () {
            return mockTimesheetRepository;
        }),
    };
});

describe("TimesheetViewModel Flow", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
        document.body.innerHTML = '';
        if (!window.URL.createObjectURL) window.URL.createObjectURL = vi.fn();
        if (!window.URL.revokeObjectURL) window.URL.revokeObjectURL = vi.fn();
        vi.spyOn(window.URL, 'createObjectURL').mockReturnValue("blob:mock-url");
        vi.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => { });
    });

    afterEach(() => {
        cleanup();
    });

    it("should handle batch consolidation", async () => {
        const { result } = renderHook(() => useTimesheetViewModel());
        const file = new File([""], "f.xlsx");

        act(() => { result.current.setBatchFiles([file]); });

        mockTimesheetRepository.processBatch.mockResolvedValueOnce({
            results: [{ file_name: "test.xlsx", status: "success" }],
            batch_id: "B-CONSO"
        });

        await act(async () => {
            await result.current.handleBatchProcess();
        });

        await act(async () => {
            await result.current.handleBatchConsolidate();
        });

        expect(mockTimesheetRepository.consolidateBatch).toHaveBeenCalled();
    });

    it("should handle batch file removal and clear", async () => {
        const { result } = renderHook(() => useTimesheetViewModel());
        const file = new File([""], "f.xlsx");
        act(() => { result.current.setBatchFiles([file]); });
        act(() => { result.current.handleRemoveBatchFile(0); });
        expect(result.current.batchFiles).toHaveLength(0);
        act(() => {
            result.current.setBatchFiles([file]);
            result.current.handleClearBatchFiles();
        });
        expect(result.current.batchFiles).toHaveLength(0);
    });

    it("should handle errors in batch process", async () => {
        const { result } = renderHook(() => useTimesheetViewModel());
        const file = new File([""], "f.xlsx");
        act(() => { result.current.setBatchFiles([file]); });

        mockTimesheetRepository.processBatch.mockRejectedValueOnce(new Error("Process failed"));
        await act(async () => {
            await result.current.handleBatchProcess();
        });
        expect(result.current.batchError).toBe("Process failed");
    });
});
