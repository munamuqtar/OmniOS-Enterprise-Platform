import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DonutChart } from "./DashboardSection";

describe("DonutChart", () => {
  it("shows the total and a legend with each value", () => {
    render(<DonutChart items={[["draft", 2], ["paid", 3]]} />);
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getByText("Paid")).toBeInTheDocument();
  });
  it("shows an empty state when there is nothing to draw", () => {
    render(<DonutChart items={[["draft", 0]]} />);
    expect(screen.getByText("Nothing yet")).toBeInTheDocument();
  });
});