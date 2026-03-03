import { render, screen } from "@testing-library/react";
import { TimesheetPage } from "@/feat/timesheet/presentation/page/TimesheetPage";
import { vi, describe, it, expect, beforeEach } from "vitest";

// Mock the ViewModel
vi.mock("@/feat/timesheet/presentation/view_model/TimesheetViewModel", () => ({
    useTimesheetViewModel: () => ({
        theme: "light",
        toggleTheme: vi.fn(),
        processingMode: "Individual",
        setProcessingMode: vi.fn(),
        volumeLabel: "0",
        statusLabel: "Listo",
        userInfo: { name: "Test User" },
        profiles: [],
        handleDownload: vi.fn(),
        handleClearBatchFiles: vi.fn(),
        handleRemoveBatchFile: vi.fn(),
        batchFiles: [],
        setBatchFiles: vi.fn(),
        batchProcessing: false,
        handleBatchProcess: vi.fn(),
        batchResults: [],
        handleBatchConsolidate: vi.fn(),
        batchConsolidated: null,
        batchBaninterZip: null,
        handleIndividualAnalyze: vi.fn(),
        individualAnalysis: null,
        handleIndividualProcess: vi.fn(),
        individualResults: [],
        setIndividualFile: vi.fn(),
        individualFile: null,
        batchProfileId: "",
        setBatchProfileId: vi.fn(),
        batchMapping: {},
        setBatchMapping: vi.fn(),
        correctSpelling: true,
        setCorrectSpelling: vi.fn(),
        dupThreshold: 85,
        setDupThreshold: vi.fn(),
        minDuplicates: 2,
        setMinDuplicates: vi.fn(),
        hoursTolerance: 0.1,
        setHoursTolerance: vi.fn(),
        employeeRole: "",
        setEmployeeRole: vi.fn(),
        batchAnalyzeInfo: null,
    })
}));

describe("TimesheetPage", () => {
    it("should render the page title", () => {
        render(<TimesheetPage />);
        expect(screen.getByText("Procesamiento Individual")).toBeInTheDocument();
        expect(screen.getByText("Test User")).toBeInTheDocument();
    });

    it("should show file uploader title", () => {
        render(<TimesheetPage />);
        expect(screen.getByText("Carga de Archivos")).toBeInTheDocument();
    });
});
