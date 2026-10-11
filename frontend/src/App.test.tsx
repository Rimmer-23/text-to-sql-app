import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { apiError, mockFetch } from "./test/fetchMock";
import type { TableSchema } from "./types";

const WORKSPACE = "11111111-1111-1111-1111-111111111111";

const SALES: TableSchema = {
  name: "sales",
  row_count: 120,
  columns: [
    { name: "city", original_name: "City", type: "TEXT" },
    { name: "amount", original_name: "Amount ($)", type: "INTEGER" },
  ],
  sample_rows: [
    ["Prague", 100],
    ["Brno", null],
    ["Ostrava", 40],
  ],
};

const CUSTOMERS: TableSchema = {
  name: "customers",
  row_count: 1,
  columns: [{ name: "name", original_name: "Name", type: "TEXT" }],
  sample_rows: [["John"]],
};

const schema = (tables: TableSchema[]) => () => ({
  status: 200,
  body: { workspace_id: WORKSPACE, tables },
});

describe("App", () => {
  it("invites an upload when there is no workspace yet", () => {
    mockFetch({});
    render(<App />);
    expect(screen.getByRole("heading", { name: "Upload a CSV file to get started" })).toBeVisible();
  });

  it("creates a workspace on first upload, remembers it and previews the new table", async () => {
    const calls = mockFetch({
      "POST /workspaces": () => ({ status: 201, body: { workspace_id: WORKSPACE } }),
      [`POST /workspaces/${WORKSPACE}/files`]: () => ({
        status: 200,
        body: { tables: [{ ...SALES, source_file: "sales.csv" }] },
      }),
      [`GET /workspaces/${WORKSPACE}/schema`]: schema([SALES]),
    });
    render(<App />);

    await userEvent.upload(screen.getByTestId("file-input"), new File(["x"], "sales.csv"));

    expect(await screen.findByRole("heading", { name: "sales" })).toBeVisible();
    expect(localStorage.getItem("textToSql.workspaceId")).toBe(WORKSPACE);
    expect(calls.map((call) => `${call.method} ${call.path}`)).toEqual([
      "POST /workspaces",
      `POST /workspaces/${WORKSPACE}/files`,
      `GET /workspaces/${WORKSPACE}/schema`,
    ]);

    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: /Amount \(\$\)/ })).toBeVisible();
    expect(within(table).getAllByRole("row")).toHaveLength(4); // header + 3 sample rows
    expect(screen.getByText("Showing the first 3 rows of 120.")).toBeVisible();
  });

  it("restores the stored workspace and switches between tables", async () => {
    localStorage.setItem("textToSql.workspaceId", WORKSPACE);
    mockFetch({ [`GET /workspaces/${WORKSPACE}/schema`]: schema([CUSTOMERS, SALES]) });
    render(<App />);

    expect(await screen.findByRole("heading", { name: "customers" })).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: /^sales/ }));
    expect(screen.getByRole("heading", { name: "sales" })).toBeVisible();
  });

  it("forgets a workspace the server no longer has", async () => {
    localStorage.setItem("textToSql.workspaceId", WORKSPACE);
    mockFetch({
      [`GET /workspaces/${WORKSPACE}/schema`]: apiError("WORKSPACE_NOT_FOUND", "gone", 404),
    });
    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Upload a CSV file to get started" }),
    ).toBeVisible();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(localStorage.getItem("textToSql.workspaceId")).toBeNull();
  });

  it("shows the backend's message when an upload is rejected", async () => {
    localStorage.setItem("textToSql.workspaceId", WORKSPACE);
    mockFetch({
      [`GET /workspaces/${WORKSPACE}/schema`]: schema([]),
      [`POST /workspaces/${WORKSPACE}/files`]: apiError(
        "INVALID_FILE",
        "'report.csv': file must be UTF-8 encoded",
        400,
      ),
    });
    render(<App />);
    await waitFor(() => expect(screen.queryByText("Loading your data…")).not.toBeInTheDocument());

    await userEvent.upload(screen.getByTestId("file-input"), new File(["x"], "report.csv"));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "'report.csv': file must be UTF-8 encoded",
    );
  });

  it("removes a table only after confirmation", async () => {
    localStorage.setItem("textToSql.workspaceId", WORKSPACE);
    const calls = mockFetch({
      [`GET /workspaces/${WORKSPACE}/schema`]: schema([SALES, CUSTOMERS]),
      [`DELETE /workspaces/${WORKSPACE}/tables/sales`]: () => ({ status: 204 }),
    });
    render(<App />);
    await screen.findByRole("heading", { name: "sales" });

    await userEvent.click(screen.getByRole("button", { name: "Remove sales" }));
    await userEvent.click(screen.getByRole("button", { name: "Keep" }));
    expect(calls.some((call) => call.method === "DELETE")).toBe(false);

    await userEvent.click(screen.getByRole("button", { name: "Remove sales" }));
    await userEvent.click(screen.getByRole("button", { name: "Remove" }));

    expect(await screen.findByRole("heading", { name: "customers" })).toBeVisible();
    expect(screen.queryByRole("button", { name: /^sales/ })).not.toBeInTheDocument();
  });
});
