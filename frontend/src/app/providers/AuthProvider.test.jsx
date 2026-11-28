import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AuthProvider from "./AuthProvider";
import { useAuth } from "./auth-context";
import * as authApi from "../../services/api/auth";

vi.mock("../../services/api/auth", () => ({ login: vi.fn(), fetchMe: vi.fn(), logout: vi.fn() }));

function Probe() {
  const { user, login, logout } = useAuth();
  return (
    <>
      <p>{user ? user.username : "signed out"}</p>
      <button onClick={() => login("admin", "x")}>sign in</button>
      <button onClick={() => logout()}>sign out</button>
    </>
  );
}

function setup() {
  const client = new QueryClient();
  render(<QueryClientProvider client={client}><AuthProvider><Probe /></AuthProvider></QueryClientProvider>);
  return client;
}

describe("AuthProvider and cached data", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    authApi.login.mockResolvedValue({ username: "admin", roles: ["super_admin"], branches: [] });
    authApi.logout.mockResolvedValue();
  });

  it("clears cached data on sign-out, so the next user never sees it", async () => {
    const client = setup();
    await userEvent.click(screen.getByText("sign in"));
    expect(await screen.findByText("admin")).toBeInTheDocument();
    client.setQueryData(["/employees/", {}], { results: ["admin-only data"] });
    await userEvent.click(screen.getByText("sign out"));
    expect(await screen.findByText("signed out")).toBeInTheDocument();
    expect(client.getQueryData(["/employees/", {}])).toBeUndefined();
  });

  it("starts every sign-in with an empty cache", async () => {
    const client = setup();
    client.setQueryData(["/employees/", {}], { results: ["left over"] });
    await userEvent.click(screen.getByText("sign in"));
    expect(await screen.findByText("admin")).toBeInTheDocument();
    expect(client.getQueryData(["/employees/", {}])).toBeUndefined();
  });
});