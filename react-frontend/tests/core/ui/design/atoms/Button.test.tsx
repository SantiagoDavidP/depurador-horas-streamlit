import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "@/core/ui/design/atoms/Button";
import { describe, it, expect, vi } from "vitest";
import React from "react";

describe("Button component", () => {
    it("renders children correctly", () => {
        render(<Button>Click me</Button>);
        expect(screen.getByText("Click me")).toBeInTheDocument();
    });

    it("applies primary variant by default", () => {
        const { container } = render(<Button>Test</Button>);
        expect(container.firstChild).toHaveClass("primary");
    });

    it("applies outline variant", () => {
        const { container } = render(<Button variant="outline">Test</Button>);
        expect(container.firstChild).toHaveClass("outline");
    });

    it("applies fullWidth class", () => {
        const { container } = render(<Button fullWidth>Test</Button>);
        expect(container.firstChild).toHaveClass("full");
    });

    it("handles click events", () => {
        const handleClick = vi.fn();
        render(<Button onClick={handleClick}>Click me</Button>);
        fireEvent.click(screen.getByText("Click me"));
        expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("can be disabled", () => {
        render(<Button disabled>Disabled</Button>);
        expect(screen.getByText("Disabled")).toBeDisabled();
    });
});
