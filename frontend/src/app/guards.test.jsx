import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Guard } from "./guards";
import { AuthContext, makeHasRole } from "./providers/auth-context";

function renderGuard(userRoles, roles) {
  const user = { username: "u", roles: userRoles, branches: [] };
  render(
    <AuthContext.Provider value={{ user, hasRole: makeHasRole(user) }}>
      <MemoryRouter><Guard roles={roles}><p>Secret page</p></Guard></MemoryRouter>
    </AuthContext.Provider>
  );
}

describe("Guard", () => {
  it("blocks users without the role", () => {
    renderGuard(["employee"], ["finance"]);
    expect(screen.getByText(/do not have access/i)).toBeInTheDocument();
    expect(screen.queryByText("Secret page")).not.toBeInTheDocument();
  });
  it("lets the right role in", () => {
    renderGuard(["finance"], ["finance"]);
    expect(screen.getByText("Secret page")).toBeInTheDocument();
  });
  it("lets Super Admin into role-restricted and admin-only pages", () => {
    renderGuard(["super_admin"], []);
    expect(screen.getByText("Secret page")).toBeInTheDocument();
  });
  it("keeps admin-only pages from everyone else", () => {
    renderGuard(["hr"], []);
    expect(screen.queryByText("Secret page")).not.toBeInTheDocument();
  });
});