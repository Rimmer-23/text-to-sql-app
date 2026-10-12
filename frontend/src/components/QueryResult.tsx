import type { ApiError } from "../api/client";
import { plural } from "../format";
import type { QueryState } from "../hooks/useQuery";
import { ResultTable } from "./ResultTable";
import { SqlPreview } from "./SqlPreview";

export function QueryResult({ state }: { state: Exclude<QueryState, { status: "idle" }> }) {
  return (
    <section
      className="result"
      aria-labelledby="result-question"
      aria-busy={state.status === "loading"}
    >
      <header className="result-header">
        <h1 id="result-question" className="result-question">
          {state.question}
        </h1>
        <p className="result-meta" aria-live="polite">
          {state.status === "loading" && "Writing and running the query…"}
          {state.status === "success" &&
            resultSummary(state.result.row_count, state.result.truncated)}
        </p>
      </header>

      {state.status === "error" && (
        <>
          <QueryError error={state.error} />
          {state.error.sql && <SqlPreview sql={state.error.sql} initiallyOpen />}
        </>
      )}

      {state.status === "success" && (
        <>
          <SqlPreview sql={state.result.sql} />
          <ResultTable key={state.id} result={state.result} />
        </>
      )}
    </section>
  );
}

function resultSummary(rowCount: number, truncated: boolean): string {
  return truncated ? `First ${plural(rowCount, "row")}` : plural(rowCount, "row");
}

function QueryError({ error }: { error: ApiError }) {
  const { title, detail, hint } = describeError(error);
  return (
    <div className="query-error" role="alert">
      <p className="query-error-title">{title}</p>
      {detail && <p className="query-error-detail">{detail}</p>}
      {hint && <p className="query-error-hint">{hint}</p>}
    </div>
  );
}

interface ErrorCopy {
  title: string;
  detail?: string;
  hint?: string;
}

function describeError(error: ApiError): ErrorCopy {
  switch (error.code) {
    case "AI_ERROR":
      // 422 is the model saying the data can't answer the question; the message is its reason.
      return error.status === 422
        ? { title: "This question can't be answered from your data", detail: error.message }
        : { title: "The AI service didn't answer", detail: error.message };
    case "SQL_NOT_ALLOWED":
      return {
        title: "The generated query was blocked",
        detail: error.message,
        hint: "Only read-only queries can run. Try rephrasing the question.",
      };
    case "SQL_EXECUTION_ERROR":
      return error.message === "Query timed out"
        ? { title: "The query took too long", hint: "Try a narrower question." }
        : {
            title: "The generated query failed",
            detail: error.message,
            hint: "Try rephrasing the question.",
          };
    case "WORKSPACE_NOT_FOUND":
      return {
        title: "Your data is no longer on the server",
        hint: "Upload your files again to continue.",
      };
    case "NETWORK_ERROR":
      return { title: "Can't reach the server", detail: error.message };
    case "INVALID_REQUEST":
      return { title: "Can't ask this question", detail: error.message };
    default:
      return { title: "Something went wrong", detail: error.message };
  }
}
