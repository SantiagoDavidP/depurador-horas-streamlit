import { render } from "@testing-library/react";
import { ProgressTrack } from "@/core/ui/design/molecules/ProgressTrack";
import { describe, it, expect } from "vitest";
import React from "react";

describe("ProgressTrack component", () => {
    it("applies correct width based on pct", () => {
        const { container } = render(<ProgressTrack pct={45} />);
        const fill = container.querySelector(".progress-fill") as HTMLElement;
        expect(fill.style.width).toBe("45%");
    });
});
