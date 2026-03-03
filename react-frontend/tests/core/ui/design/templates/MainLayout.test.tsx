import { render, screen, fireEvent } from "@testing-library/react";
import { MainLayout } from "@/core/ui/design/templates/MainLayout";
import { describe, it, expect, vi } from "vitest";

describe("MainLayout", () => {
    const defaultProps = {
        sidebar: {
            theme: "light" as const,
            onThemeToggle: vi.fn(),
            processingMode: "Individual" as const,
            onModeChange: vi.fn(),
            volumeLabel: "Low",
            statusLabel: "Idle",
            userInfo: { name: "Test User" },
        },
        headerTitle: "Test Page",
        children: <div data-testid="children">Content</div>,
    };

    it("should render correctly", () => {
        render(<MainLayout {...defaultProps} />);
        expect(screen.getByText("Test Page")).toBeInTheDocument();
        expect(screen.getByTestId("children")).toBeInTheDocument();
        expect(screen.getByText("Test User")).toBeInTheDocument();
        expect(screen.getByText("Low")).toBeInTheDocument();
        expect(screen.getByText("Idle")).toBeInTheDocument();
    });

    it("should call onModeChange when radio buttons are clicked", () => {
        render(<MainLayout {...defaultProps} />);
        const batchRadio = screen.getByLabelText("Por lotes");
        fireEvent.click(batchRadio);
        expect(defaultProps.sidebar.onModeChange).toHaveBeenCalledWith("Por lotes");
    });

    it("should apply dark theme class when theme is dark", () => {
        const darkProps = {
            ...defaultProps,
            sidebar: { ...defaultProps.sidebar, theme: "dark" as const },
        };
        const { container } = render(<MainLayout {...darkProps} />);
        expect(container.firstChild).toHaveClass("theme-dark");
    });
});
