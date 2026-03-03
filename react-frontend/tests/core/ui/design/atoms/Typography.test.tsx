import { render, screen } from "@testing-library/react";
import { Typography } from "@/core/ui/design/atoms/Typography";
import { describe, it, expect } from "vitest";

describe("Typography", () => {
    it("renders h1 correctly", () => {
        render(<Typography variant="h1">Hello</Typography>);
        expect(screen.getByText("Hello").tagName).toBe("H1");
    });

    it("renders h2 correctly", () => {
        render(<Typography variant="h2">Hello</Typography>);
        expect(screen.getByText("Hello").tagName).toBe("H2");
    });

    it("renders h3 correctly", () => {
        render(<Typography variant="h3">Hello</Typography>);
        expect(screen.getByText("Hello").tagName).toBe("H3");
    });

    it("renders h4 correctly", () => {
        render(<Typography variant="h4">Header 4</Typography>);
        expect(screen.getByText("Header 4").tagName).toBe("H4");
    });

    it("renders label as div with class", () => {
        render(<Typography variant="label">Label Text</Typography>);
        const el = screen.getByText("Label Text");
        expect(el.tagName).toBe("DIV");
        expect(el.className).toContain("label");
    });

    it("renders small correctly", () => {
        render(<Typography variant="small">Small Text</Typography>);
        const el = screen.getByText("Small Text");
        expect(el.tagName).toBe("P");
        expect(el.className).toContain("small");
    });

    it("renders eyebrow correctly", () => {
        render(<Typography variant="eyebrow">Eyebrow</Typography>);
        const el = screen.getByText("Eyebrow");
        expect(el.className).toContain("header-eyebrow");
    });

    it("renders gradient correctly", () => {
        render(<Typography variant="gradient">Gradient</Typography>);
        const el = screen.getByText("Gradient");
        expect(el.className).toContain("gradient-title");
    });

    it("applies custom className", () => {
        render(<Typography variant="h1" className="custom-class">Text</Typography>);
        expect(screen.getByText("Text").className).toContain("custom-class");
    });

    it("renders default case (span) if variant is invalid (casted)", () => {
        // @ts-ignore
        render(<Typography variant="invalid">Default</Typography>);
        expect(screen.getByText("Default").tagName).toBe("SPAN");
    });
});
