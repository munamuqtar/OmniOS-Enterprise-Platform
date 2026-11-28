import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DataTable from "./DataTable";

const columns = [{ key: "name", header: "Name" }];

describe("DataTable", () => {
  it("shows a loading state", () => {
    render(<DataTable columns={columns} rows={[]} loading />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
  it("shows an empty state", () => {
    render(<DataTable columns={columns} rows={[]} emptyTitle="No leads yet" />);
    expect(screen.getByText("No leads yet")).toBeInTheDocument();
  });
  it("shows an error with a retry button", async () => {
    const retry = vi.fn();
    render(<DataTable columns={columns} rows={[]} error="Server error" onRetry={retry} />);
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(retry).toHaveBeenCalled();
  });
  it("renders rows and pages through results", async () => {
    const onPage = vi.fn();
    render(<DataTable columns={columns} rows={[{ id: "1", name: "Acme" }]}
                      pagination={{ page: 1, pageSize: 20, count: 45, onPage }} />);
    expect(screen.getByText("Acme")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(onPage).toHaveBeenCalledWith(2);
  });
});