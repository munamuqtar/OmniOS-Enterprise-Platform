import { describe, it, expect } from "vitest";
import { calcTotals } from "./money";

describe("calcTotals (mirrors the server's math)", () => {
  it("applies the discount before tax", () => {
    const t = calcTotals([{ quantity: "2", unit_price: "100" }, { quantity: "1", unit_price: "50" }], "10", "10");
    expect([t.subtotal, t.tax, t.total]).toEqual([250, 24, 264]);
  });
  it("calculates a plain quote", () => {
    expect(calcTotals([{ quantity: "100", unit_price: "50" }], "0", "10").total).toBe(5500);
  });
  it("warns when the discount is larger than the subtotal", () => {
    expect(calcTotals([{ quantity: "1", unit_price: "10" }], "50", "0").discountTooHigh).toBe(true);
  });
  it("handles empty rows without NaN", () => {
    expect(calcTotals([{ quantity: "", unit_price: "" }], "", "").total).toBe(0);
  });
});