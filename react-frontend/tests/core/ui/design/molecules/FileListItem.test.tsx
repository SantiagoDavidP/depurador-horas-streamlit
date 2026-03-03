import { render, screen, fireEvent } from "@testing-library/react";
import { FileListItem } from "@/core/ui/design/molecules/FileListItem";
import { describe, it, expect, vi } from "vitest";
import React from "react";

describe("FileListItem component", () => {
    it("renders file name correctly", () => {
        render(<FileListItem name="report.xlsx" onRemove={() => { }} />);
        expect(screen.getByText("report.xlsx")).toBeInTheDocument();
    });

    it("calls onRemove when clicking the button", () => {
        const handleRemove = vi.fn();
        render(<FileListItem name="test.csv" onRemove={handleRemove} />);
        fireEvent.click(screen.getByText("✕"));
        expect(handleRemove).toHaveBeenCalledTimes(1);
    });
});
