import { vi } from "vitest";

export interface MockCall {
  method: string;
  path: string;
  body?: BodyInit | null;
}

type Handler = (call: MockCall) => { status: number; body?: unknown };

/** Replaces global fetch with a tiny router over `METHOD /path` keys. Unknown routes fail loudly. */
export function mockFetch(routes: Record<string, Handler>) {
  const calls: MockCall[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const call: MockCall = {
      method: init?.method ?? "GET",
      path: String(input).replace(/^\/api/, ""),
      body: init?.body,
    };
    calls.push(call);
    const handler = routes[`${call.method} ${call.path}`];
    if (!handler) throw new Error(`Unexpected request: ${call.method} ${call.path}`);
    const { status, body } = handler(call);
    return new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

export const apiError = (code: string, message: string, status: number) => () => ({
  status,
  body: { error: { code, message } },
});
