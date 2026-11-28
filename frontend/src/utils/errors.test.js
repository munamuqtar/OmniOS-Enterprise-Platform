import { describe, it, expect } from "vitest";
import { parseApiError } from "./errors";
import { unwrap } from "../services/api/client";

const failure = (status, data) => ({ response: { status, data } });

describe("parseApiError", () => {
  it("explains a network failure", () => expect(parseApiError({}).message).toMatch(/cannot reach the server/i));
  it("maps validation errors to fields", () => {
    const e = parseApiError(failure(400, { message: "Validation failed", errors: { email: ["Already registered."] } }));
    expect(e.fields.email).toBe("Already registered.");
  });
  it("shows a friendly message when rate limited", () => expect(parseApiError(failure(429, {})).message).toMatch(/too many attempts/i));
  it("explains permission errors", () => expect(parseApiError(failure(403, {})).message).toMatch(/permission/i));
    it("flattens nested line-item errors", () => {
    const e = parseApiError(failure(400, { errors: { items: [{}, { quantity: ["Must be greater than zero."] }] } }));
    expect(e.fields.items).toBe("quantity: Must be greater than zero.");
  });
});

describe("unwrap", () => {
  it("unwraps the API envelope", () => expect(unwrap({ data: { success: true, data: { a: 1 }, errors: null } })).toEqual({ a: 1 }));
  it("passes plain bodies through", () => expect(unwrap({ data: { results: [] } })).toEqual({ results: [] }));
});