import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import AuthProvider from "../../app/providers/AuthProvider";
import LoginPage from "./LoginPage";
import * as authApi from "../../services/api/auth";

vi.mock("../../services/api/auth", () => ({ login: vi.fn(), fetchMe: vi.fn(), logout: vi.fn() }));

function setup(entry = "/login") {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthProvider>
        <MemoryRouter initialEntries={[entry]}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/dashboard" element={<p>Dashboard page</p>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

async function submit() {
  await userEvent.type(screen.getByLabelText(/username/i), "sales");
  await userEvent.type(screen.getByLabelText(/password/i), "secret");
  await userEvent.click(screen.getByRole("button", { name: /^login$/i }));
}

describe("LoginPage", () => {
  beforeEach(() => { localStorage.clear(); vi.clearAllMocks(); });

  it("signs in and goes to the dashboard", async () => {
    authApi.login.mockResolvedValue({ username: "sales", roles: ["sales"], branches: [] });
    setup();
    await submit();
    expect(await screen.findByText("Dashboard page")).toBeInTheDocument();
    expect(authApi.login).toHaveBeenCalledWith("sales", "secret");
  });

  it("always starts on the dashboard, even when the previous user was on another page", async () => {
    authApi.login.mockResolvedValue({ username: "sales", roles: ["sales"], branches: [] });
    setup({ pathname: "/login", state: { from: { pathname: "/settings/users" } } });
    await submit();
    expect(await screen.findByText("Dashboard page")).toBeInTheDocument();
  });

  it("shows the server's message when the login fails", async () => {
    authApi.login.mockRejectedValue({ response: { status: 401, data: { message: "No active account found with the given credentials" } } });
    setup();
    await submit();
    expect(await screen.findByRole("alert")).toHaveTextContent(/no active account/i);
  });

  it("shows a rate-limit message after too many attempts", async () => {
    authApi.login.mockRejectedValue({ response: { status: 429, data: {} } });
    setup();
    await submit();
    expect(await screen.findByRole("alert")).toHaveTextContent(/too many attempts/i);
  });

  it("explains how to reset a forgotten password", async () => {
    setup();
    await userEvent.click(screen.getByRole("button", { name: /forgot password/i }));
    expect(screen.getByRole("note")).toHaveTextContent(/ask a super admin/i);
  });
});