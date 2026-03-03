import { render, screen } from "@testing-library/react";
import { MetricCard } from "@/core/ui/design/molecules/MetricCard";
import { describe, it, expect } from "vitest";
import React from "react";

describe("MetricCard component", () => {
    it("renders label and value correctly", () => {
        render(<MetricCard label="Total Hours" value="120.5" />);
        expect(screen.getByText("Total Hours")).toBeInTheDocument();
        expect(screen.getByText("120.5")).toBeInTheDocument();
    });

    it("applies metric-card class", () => {
        const { container } = render(<MetricCard label="M" value="V" />);
        expect(container.firstChild).toHaveClass("metric-card");
    });
});
