import { describe, it, expect } from "vitest";
import { displayName, greeting, initials } from "./format";

describe("greeting", () => {
  it("changes with the time of day", () => {
    expect(greeting(new Date(2026, 0, 1, 9))).toBe("Good morning");
    expect(greeting(new Date(2026, 0, 1, 14))).toBe("Good afternoon");
    expect(greeting(new Date(2026, 0, 1, 20))).toBe("Good evening");
  });
});

describe("user display helpers", () => {
  it("builds initials from the full name, or the username when there is no name", () => {
    expect(initials({ first_name: "Muna", last_name: "Ali" })).toBe("MA");
    expect(initials({ username: "muna" })).toBe("M");
  });
  it("shows the full name, falling back to the username", () => {
    expect(displayName({ first_name: "Muna", last_name: "Ali", username: "muna" })).toBe("Muna Ali");
    expect(displayName({ username: "muna" })).toBe("muna");
  });
});