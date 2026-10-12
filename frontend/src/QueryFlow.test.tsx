import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { apiError, mockFetch } from "./test/fetchMock";
import type { MockCall } from "./test/fetchMock";
import type { QueryResponse, TableSchema } from "./types";

const WORKSPACE = "22222222-2222-2222-2222-222222222222";
const QUERY = `POST /workspaces/${WORKSPACE}/query`;

const SALES: TableSchema = {
  name: "sales",
  row_count: 120,
  columns: [
    { name: "city", original_name: "City", type: "TEXT" },
    { name: "amount", original_name: "Amount ($)", type: "REAL" },
  ],
  sample_rows: [["Prague", 100.5]],
};

function result(overrides: Partial<QueryResponse> = {}) {
  const rows = overrides.rows ?? [
    ["Brno", 310],
    ["Prague", 180.5],
  ];
  return {
    status: 200,
    body: {
      sql: "SELECT\n  city,\n  SUM(amount) AS total\nFROM sales\nGROUP BY\n  city\nLIMIT 1000",
      columns: ["city", "total"],
      rows,
      row_count: rows.length,
      truncated: false,
      ...overrides,
    },
  };
}

const questionOf = (call: MockCall) => JSON.parse(String(call.body)).question as string;

async function renderWithData(onQuery: (call: MockCall) => { status: number; body?: unknown }) {
  localStorage.setItem("textToSql.workspaceId", WORKSPACE);
  const calls = mockFetch({
    [`GET /workspaces/${WORKSPACE}/schema`]: () => ({
      status: 200,
      body: { workspace_id: WORKSPACE, tables: [SALES] },
    }),
    [QUERY]: onQuery,
  });
  render(<App />);
  await screen.findByRole("heading", { name: "sales" });
  return calls;
}

const questionBox = () => screen.getByRole("textbox", { name: "Question" });

async function ask(question: string) {
  await userEvent.clear(questionBox());
  await userEvent.type(questionBox(), question);
  await userEvent.click(screen.getByRole("button", { name: "Ask" }));
}

describe("asking questions", () => {
  it("is disabled until there is data", () => {
    mockFetch({});
    render(<App />);
    expect(questionBox()).toBeDisabled();
    expect(questionBox()).toHaveAttribute(
      "placeholder",
      "Upload a CSV file to ask questions about it",
    );
  });

  it("shows the answer as a table, with the SQL collapsed", async () => {
    const calls = await renderWithData(() => result());
    expect(questionBox()).toHaveAttribute("placeholder", "Ask a question about sales");

    await ask("  Total amount by city  ");

    expect(await screen.findByRole("heading", { name: "Total amount by city" })).toBeVisible();
    expect(questionOf(calls.at(-1)!)).toBe("Total amount by city");
    expect(screen.getByText("2 rows")).toBeVisible();

    const table = screen.getByRole("table", { name: "Query result" });
    expect(
      within(table)
        .getAllByRole("row")
        .map((row) => row.textContent),
    ).toEqual(["citytotal", "Brno310.0", "Prague180.5"]); // decimals padded per column

    const sql = screen.getByText(/GROUP BY/);
    expect(sql).not.toBeVisible();
    await userEvent.click(screen.getByText("SQL query"));
    expect(sql).toBeVisible();

    // The question stays in the box so it can be refined.
    expect(questionBox()).toHaveValue("  Total amount by city  ");
  });

  it("asks with Enter and adds a line with Shift+Enter", async () => {
    const calls = await renderWithData(() => result());
    await userEvent.type(questionBox(), "first line{Shift>}{Enter}{/Shift}second");
    expect(calls.filter((call) => call.method === "POST")).toHaveLength(0);

    await userEvent.type(questionBox(), "{Enter}");
    expect(await screen.findByRole("heading", { name: /first line\s+second/ })).toBeVisible();
  });

  it("goes back to the table preview when a table is picked", async () => {
    await renderWithData(() => result());
    await ask("Total amount by city");
    await screen.findByRole("table", { name: "Query result" });
    expect(screen.getByRole("button", { name: /^sales/ })).not.toHaveAttribute("aria-current");

    await userEvent.click(screen.getByRole("button", { name: /^sales/ }));
    expect(screen.getByRole("heading", { name: "sales" })).toBeVisible();
    expect(screen.getByRole("button", { name: /^sales/ })).toHaveAttribute("aria-current", "true");
  });

  it("pages through long results 50 rows at a time", async () => {
    const rows = Array.from({ length: 120 }, (_, i) => [`order ${i + 1}`, i + 1]);
    await renderWithData(() => result({ rows }));
    await ask("All orders");

    const table = await screen.findByRole("table", { name: "Query result" });
    expect(within(table).getAllByRole("row")).toHaveLength(51); // header + 50
    expect(screen.getByText("Rows 1–50 of 120")).toBeVisible();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Rows 101–120 of 120")).toBeVisible();
    expect(within(table).getAllByRole("row")).toHaveLength(21);
    expect(within(table).getAllByRole("row")[1]).toHaveTextContent("order 101");
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  it("starts a new answer on its first page", async () => {
    const rows = Array.from({ length: 60 }, (_, i) => [`row ${i}`, i]);
    await renderWithData(() => result({ rows }));
    await ask("first");
    await screen.findByText("Rows 1–50 of 60");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));

    await ask("second");
    expect(await screen.findByRole("heading", { name: "second" })).toBeVisible();
    expect(screen.getByText("Rows 1–50 of 60")).toBeVisible();
  });

  it("says when the result was cut off", async () => {
    const rows = Array.from({ length: 1000 }, (_, i) => [`row ${i}`, i]);
    await renderWithData(() => result({ rows, truncated: true }));
    await ask("Everything");

    expect(await screen.findByText("First 1,000 rows")).toBeVisible();
    expect(screen.getByText(/Only the first 1,000 rows are shown/)).toBeVisible();
  });

  it("says when nothing matches", async () => {
    await renderWithData(() => result({ rows: [] }));
    await ask("Sales in Vienna");
    expect(await screen.findByText("No rows match this question.")).toBeVisible();
  });

  it("explains a failed query and shows the SQL that failed", async () => {
    await renderWithData(() => ({
      status: 400,
      body: {
        error: {
          code: "SQL_EXECUTION_ERROR",
          message: "no such column: town",
          sql: "SELECT town FROM sales",
        },
      },
    }));
    await ask("Sales by town");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The generated query failed");
    expect(alert).toHaveTextContent("no such column: town");
    expect(alert).toHaveTextContent("Try rephrasing the question.");
    expect(screen.getByText("SELECT town FROM sales")).toBeVisible(); // opened for the failure
  });

  it("passes on the AI's reason when the data can't answer", async () => {
    await renderWithData(apiError("AI_ERROR", "The data has no weather information", 422));
    await ask("Will it rain tomorrow?");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("This question can't be answered from your data");
    expect(alert).toHaveTextContent("The data has no weather information");
  });

  it("explains an AI setup problem", async () => {
    await renderWithData(apiError("AI_ERROR", "AI_API_KEY is not set in backend/.env", 500));
    await ask("Total amount by city");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The AI service didn't answerAI_API_KEY is not set in backend/.env",
    );
  });

  it("points to the backend terminal when the server crashes", async () => {
    await renderWithData(() => ({ status: 500, body: "Internal Server Error" }));
    await ask("how many customers live in prague?");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The server hit an unexpected error");
    expect(alert).toHaveTextContent("Details are in the terminal where the backend runs.");
  });
});
