import { describe, it, expect } from "vitest";
import { formatDate, formatKpi, formatMoney, titleCase } from "./format";

describe("format helpers", () => {
  it("title-cases snake_case values", () => expect(titleCase("partially_paid")).toBe("Partially Paid"));
  it("formats money with its currency", () => expect(formatMoney("1234.5", "USD")).toBe("USD 1,234.50"));
  it("does not shift plain dates across time zones", () => expect(formatDate("2026-11-26")).toBe("Nov 26, 2026"));
  it("formats dashboard KPI shapes", () => {
    expect(formatKpi(1500)).toBe("1,500");
    expect(formatKpi([{ currency: "USD", amount: "100" }])).toBe("USD 100.00");
    expect(formatKpi([])).toBe("0.00");
  });
});