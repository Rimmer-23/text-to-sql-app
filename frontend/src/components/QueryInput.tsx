import { useId, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";

// Matches the backend's limit on QueryRequest.question.
const MAX_QUESTION_LENGTH = 2000;

interface QueryInputProps {
  tableNames: string[];
  busy: boolean;
  onAsk: (question: string) => void;
}

export function QueryInput({ tableNames, busy, onAsk }: QueryInputProps) {
  const inputId = useId();
  const [question, setQuestion] = useState("");
  const noData = tableNames.length === 0;
  const canAsk = !noData && !busy && question.trim().length > 0;

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (canAsk) onAsk(question.trim());
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter asks, Shift+Enter adds a line. Never interrupt an IME composition.
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form className="ask" onSubmit={submit}>
      <label htmlFor={inputId} className="visually-hidden">
        Question
      </label>
      <textarea
        id={inputId}
        className="ask-input"
        rows={1}
        maxLength={MAX_QUESTION_LENGTH}
        value={question}
        disabled={noData}
        placeholder={placeholder(tableNames)}
        onChange={(event) => setQuestion(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <button type="submit" className="button ask-button" disabled={!canAsk}>
        {busy ? "Asking…" : "Ask"}
      </button>
    </form>
  );
}

function placeholder(tableNames: string[]): string {
  if (tableNames.length === 0) return "Upload a CSV file to ask questions about it";
  if (tableNames.length > 3) return `Ask a question about your ${tableNames.length} tables`;
  const names =
    tableNames.length === 1
      ? tableNames[0]
      : `${tableNames.slice(0, -1).join(", ")} and ${tableNames.at(-1)}`;
  return `Ask a question about ${names}`;
}
