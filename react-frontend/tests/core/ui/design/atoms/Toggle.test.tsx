import { render, screen, fireEvent } from "@testing-library/react";
import { Toggle } from "@/core/ui/design/atoms/Toggle";
import { describe, it, expect, vi } from "vitest";
import React from "react";

describe("Toggle component", () => {
    it("renders label correctly", () => {
        render(<Toggle label="Enable feature" />);
        expect(screen.getByText("Enable feature")).toBeInTheDocument();
    });

    it("renders checkbox input", () => {
        render(<Toggle />);
        expect(screen.getByRole("checkbox")).toBeInTheDocument();
    });

    it("handles change events", () => {
        const handleChange = vi.fn();
        render(<Toggle onChange={handleChange} />);
        const checkbox = screen.getByRole("checkbox");
        fireEvent.click(checkbox);
        expect(handleChange).toHaveBeenCalled();
    });

    it("can be checked", () => {
        render(<Toggle checked readOnly />);
        expect(screen.getByRole("checkbox")).toBeChecked();
    });
});
