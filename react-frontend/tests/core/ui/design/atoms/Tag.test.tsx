import { render, screen } from "@testing-library/react";
import { Tag } from "@/core/ui/design/atoms/Tag";
import { describe, it, expect } from "vitest";
import React from "react";

describe("Tag component", () => {
    it("renders children correctly", () => {
        render(<Tag>Active</Tag>);
        expect(screen.getByText("Active")).toBeInTheDocument();
    });

    it("applies tag class", () => {
        const { container } = render(<Tag>Test</Tag>);
        expect(container.firstChild).toHaveClass("tag");
    });
});
