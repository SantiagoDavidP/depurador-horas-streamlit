import { render, screen } from "@testing-library/react";
import { InfoItem } from "@/core/ui/design/molecules/InfoItem";
import { describe, it, expect } from "vitest";
import React from "react";

describe("InfoItem component", () => {
    it("renders label and value correctly", () => {
        render(<InfoItem label="Client" value="ACME Corp" />);
        expect(screen.getByText("Client")).toBeInTheDocument();
        expect(screen.getByText("ACME Corp")).toBeInTheDocument();
    });
});
