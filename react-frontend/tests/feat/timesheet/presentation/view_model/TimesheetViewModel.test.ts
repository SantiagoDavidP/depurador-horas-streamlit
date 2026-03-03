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
        handleBatchConsolidate: vi.fn().mockResolvedValue({ filename: "results.xlsx" }),
        downloadFile: vi.fn().mockResolvedValue(new Blob(["test"])),
        analyzeIndividual: vi.fn().mockResolvedValue({ employee_count: 5 }),
        processIndividual: vi.fn().mockResolvedValue({ results: [], batch_id: "indiv1" }),
    }
}));

// Mock the repository
vi.mock("@/feat/timesheet/data/TimesheetRepositoryImpl", () => {
    return {
        TimesheetRepositoryImpl: vi.fn().mockImplementation(function () {
            return mockTimesheetRepository;
        }),
    };
});

describe("TimesheetViewModel", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
        document.body.innerHTML = '';

        // Mock URL
        if (!window.URL.createObjectURL) {
            window.URL.createObjectURL = vi.fn();
        }
        if (!window.URL.revokeObjectURL) {
            window.URL.revokeObjectURL = vi.fn();
        }
        vi.spyOn(window.URL, 'createObjectURL').mockReturnValue("blob:mock-url");
        vi.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => { });
    });

    afterEach(() => {
        cleanup();
    });

    it("should initialize and load profiles", async () => {
        const { result } = renderHook(() => useTimesheetViewModel());

        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });

        expect(result.current.profiles).toHaveLength(1);
        expect(result.current.userInfo).toEqual({ name: "Test User" });
    });

    it("should toggle theme", async () => {
        const { result } = renderHook(() => useTimesheetViewModel());

        act(() => {
            result.current.toggleTheme(true);
        });
        expect(result.current.theme).toBe("dark");

        act(() => {
            result.current.toggleTheme(false);
        });
        expect(result.current.theme).toBe("light");
    });

    it("should handle batch analysis flow via useEffect", async () => {
        const { result } = renderHook(() => useTimesheetViewModel());
        const file = new File([""], "test.xlsx");

        await act(async () => {
            result.current.setBatchFiles([file]);
        });

        // Wait for useEffect
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();
        });

        expect(result.current.batchAnalyzeInfo).not.toBeNull();
        expect(result.current.batchProfileId).toBe("p1");
    });

    it("should handle batch processing flow", async () => {
        const { result } = renderHook(() => useTimesheetViewModel());

        act(() => {
            result.current.setBatchProfileId("p1");
            result.current.setBatchFiles([new File([""], "test.xlsx")]);
        });

        await act(async () => {
            await result.current.handleBatchProcess();
        });

        expect(result.current.batchResults).not.toBeNull();
        expect(result.current.batchProcessing).toBe(false);
    });

    it("should handle individual analyze and process flow", async () => {
        const { result } = renderHook(() => useTimesheetViewModel());
        const file = new File([""], "test.xlsx");

        await act(async () => {
            await result.current.handleIndividualAnalyze(file);
        });
        expect(result.current.individualAnalysis?.employee_count).toBe(5);

        await act(async () => {
            await result.current.handleIndividualProcess(file, "p1");
        });
        expect(result.current.individualResults).not.toBeNull();
    });

    it("should handle download", async () => {
        const { result } = renderHook(() => useTimesheetViewModel());

        const link = {
            click: vi.fn(),
            setAttribute: vi.fn(),
            style: {},
            remove: vi.fn(),
            parentNode: { removeChild: vi.fn() }
        };
        vi.spyOn(document, 'createElement').mockReturnValue(link as any);
        vi.spyOn(document.body, 'appendChild').mockImplementation(() => null as any);

        await act(async () => {
            await result.current.handleDownload("123", "test.xlsx");
        });

        expect(mockTimesheetRepository.downloadFile).toHaveBeenCalledWith("123");
        expect(link.click).toHaveBeenCalled();
    });
});
