import { render, screen, fireEvent } from "@testing-library/react";
import { Input } from "@/core/ui/design/atoms/Input";
import { describe, it, expect, vi } from "vitest";
import React from "react";

describe("Input component", () => {
    it("renders input correctly", () => {
        render(<Input placeholder="Enter text" />);
        expect(screen.getByPlaceholderText("Enter text")).toBeInTheDocument();
    });

    it("handles value change", () => {
        const handleChange = vi.fn();
        render(<Input onChange={handleChange} />);
        const input = screen.getByRole("textbox");
        fireEvent.change(input, { target: { value: "test" } });
        expect(handleChange).toHaveBeenCalled();
    });

    it("applies input class", () => {
        const { container } = render(<Input />);
        expect(container.firstChild).toHaveClass("input");
    });
});
