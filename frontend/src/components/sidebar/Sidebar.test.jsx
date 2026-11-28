import { describe, it, expect } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Sidebar from "./Sidebar";
import { AuthContext, makeHasRole } from "../../app/providers/auth-context";

function renderFor(roles, path = "/") {
  const user = { username: "u", first_name: "Test", roles, branches: [] };
  render(
    <AuthContext.Provider value={{ user, hasRole: makeHasRole(user) }}>
      <MemoryRouter initialEntries={[path]}><Sidebar open onNavigate={() => {}} /></MemoryRouter>
    </AuthContext.Provider>
  );
}
const shows = (name) => screen.queryByRole("link", { name }) !== null;

describe("role-based navigation", () => {
  it("shows an employee only their own screens", () => {
    renderFor(["employee"]);
    ["Dashboard", "Employees", "Projects", "Tasks", "Timesheets"].forEach((n) => expect(shows(n)).toBe(true));
    ["Invoices", "Payments", "Leads", "Users", "Recruitment"].forEach((n) => expect(shows(n)).toBe(false));
  });
  it("shows finance the money screens but not CRM or settings", () => {
    renderFor(["finance"]);
    ["Invoices", "Payments", "Clients", "Quotations"].forEach((n) => expect(shows(n)).toBe(true));
    ["Leads", "Recruitment", "Users"].forEach((n) => expect(shows(n)).toBe(false));
  });
  it("shows Super Admin everything", () => {
    renderFor(["super_admin"]);
    ["Users", "Payments", "Leads", "Recruitment", "Audit Logs", "Branches", "Organization"].forEach((n) => expect(shows(n)).toBe(true));
  });
  it("combines screens for users with several roles", () => {
    renderFor(["hr", "sales"]);
    expect(shows("Recruitment") && shows("Leads")).toBe(true);
    expect(shows("Payments")).toBe(false);
  });
});

describe("dropdown groups", () => {
  it("opens and closes when the group is clicked", () => {
    renderFor(["super_admin"]);
    const hr = screen.getByRole("button", { name: "HR" });
    expect(hr).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(hr);
    expect(hr).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(hr);
    expect(hr).toHaveAttribute("aria-expanded", "false");
  });
  it("opens the group that contains the current page", () => {
    renderFor(["super_admin"], "/hr/recruitment");
    expect(screen.getByRole("button", { name: "HR" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: "Finance" })).toHaveAttribute("aria-expanded", "false");
  });
});