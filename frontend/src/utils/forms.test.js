import { describe, it, expect } from "vitest";
import { toFormData } from "./forms";

describe("toFormData", () => {
  it("keeps empty strings so fields can be cleared, and skips null and undefined", () => {
    const fd = toFormData({ phone: "", name: "Acme", logo: null, other: undefined });
    expect(fd.get("phone")).toBe("");
    expect(fd.get("name")).toBe("Acme");
    expect(fd.has("logo")).toBe(false);
    expect(fd.has("other")).toBe(false);
  });
  it("includes files", () => {
    const file = new File(["x"], "cv.pdf", { type: "application/pdf" });
    expect(toFormData({ resume: file }).get("resume").name).toBe("cv.pdf");
  });
});