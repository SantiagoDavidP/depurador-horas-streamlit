import { render, screen, fireEvent } from "@testing-library/react";
import { ThemeSwitch } from "@/core/ui/design/molecules/ThemeSwitch";
import { describe, it, expect, vi } from "vitest";
import React from "react";

describe("ThemeSwitch component", () => {
    it("renders both theme labels", () => {
        render(<ThemeSwitch theme="light" onToggle={() => { }} />);
        expect(screen.getByText("Tema Claro")).toBeInTheDocument();
        expect(screen.getByText("Tema Oscuro")).toBeInTheDocument();
    });

    it("applies active class when theme is dark", () => {
        const { container } = render(<ThemeSwitch theme="dark" onToggle={() => { }} />);
        expect(container.querySelector(".theme-switch")).toHaveClass("active");
    });

    it("calls onToggle when clicked", () => {
        const handleToggle = vi.fn();
        const { container } = render(<ThemeSwitch theme="light" onToggle={handleToggle} />);
        fireEvent.click(container.querySelector(".theme-switch")!);
        expect(handleToggle).toHaveBeenCalledWith(true);
    });
});
