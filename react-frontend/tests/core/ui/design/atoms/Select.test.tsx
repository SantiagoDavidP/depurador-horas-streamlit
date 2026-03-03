import { render, screen, fireEvent } from "@testing-library/react";
import { Select } from "@/core/ui/design/atoms/Select";
import { describe, it, expect, vi } from "vitest";
import React from "react";

describe("Select component", () => {
    const options = [
        { value: "1", label: "Option 1" },
        { value: "2", label: "Option 2" },
    ];

    it("renders options correctly", () => {
        render(<Select options={options} />);
        expect(screen.getByText("Option 1")).toBeInTheDocument();
        expect(screen.getByText("Option 2")).toBeInTheDocument();
    });

    it("handles value change", () => {
        const handleChange = vi.fn();
        render(<Select options={options} onChange={handleChange} />);
        const select = screen.getByRole("combobox");
        fireEvent.change(select, { target: { value: "2" } });
        expect(handleChange).toHaveBeenCalled();
    });
});
