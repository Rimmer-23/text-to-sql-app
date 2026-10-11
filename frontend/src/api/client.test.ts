import { describe, expect, it, vi } from "vitest";

import { mockFetch } from "../test/fetchMock";
import { ApiError, api } from "./client";

describe("api client", () => {
  it("turns the backend error format into an ApiError", async () => {
    mockFetch({
      "GET /workspaces/abc/schema": () => ({
        status: 404,
        body: { error: { code: "WORKSPACE_NOT_FOUND", message: "Workspace 'abc' not found" } },
      }),
    });

    const error = await api.getSchema("abc").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      code: "WORKSPACE_NOT_FOUND",
      message: "Workspace 'abc' not found",
      status: 404,
    });
  });

  it("falls back to a generic error when the body is not ours", async () => {
    vi.stubGlobal("fetch", async () => new Response("<html>Bad gateway</html>", { status: 502 }));
    await expect(api.getSchema("abc")).rejects.toMatchObject({
      code: "UNKNOWN_ERROR",
      status: 502,
    });
  });

  it("reports an unreachable server as NETWORK_ERROR", async () => {
    vi.stubGlobal("fetch", async () => {
      throw new TypeError("Failed to fetch");
    });
    await expect(api.createWorkspace()).rejects.toMatchObject({ code: "NETWORK_ERROR" });
  });

  it("returns nothing for 204 responses", async () => {
    mockFetch({ "DELETE /workspaces/abc/tables/sales": () => ({ status: 204 }) });
    await expect(api.deleteTable("abc", "sales")).resolves.toBeUndefined();
  });

  it("sends every file under the `files` field", async () => {
    const calls = mockFetch({
      "POST /workspaces/abc/files": () => ({ status: 200, body: { tables: [] } }),
    });
    const files = [new File(["a"], "a.csv"), new File(["b"], "b.csv")];

    await api.uploadFiles("abc", files);

    const form = calls[0]!.body as FormData;
    expect(form.getAll("files").map((file) => (file as File).name)).toEqual(["a.csv", "b.csv"]);
  });
});
