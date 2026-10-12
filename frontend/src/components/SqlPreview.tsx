import { useEffect, useState } from "react";

interface SqlPreviewProps {
  sql: string;
  /** Open by default, e.g. when the query failed and the SQL explains why. */
  initiallyOpen?: boolean;
}

/** The generated SQL, collapsed by default: there for trust and debugging, not in the way. */
export function SqlPreview({ sql, initiallyOpen = false }: SqlPreviewProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(timer);
  }, [copied]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
    } catch {
      // Clipboard can be unavailable (insecure context, denied permission); the SQL stays
      // selectable by hand.
    }
  }

  return (
    <details className="sql" open={initiallyOpen}>
      <summary className="sql-summary">SQL query</summary>
      <div className="sql-body">
        <pre className="sql-code">
          <code>{sql}</code>
        </pre>
        <button type="button" className="link-button sql-copy" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </details>
  );
}
