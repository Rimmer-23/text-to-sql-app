import { useId, useRef, useState } from "react";
import type { DragEvent } from "react";

import { ApiError } from "../api/client";

interface FileUploadProps {
  onUpload: (files: File[]) => Promise<void>;
}

export function FileUpload({ onUpload }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const hintId = useId();
  const [dragging, setDragging] = useState(false);
  const [uploadingCount, setUploadingCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const busy = uploadingCount > 0;

  async function handleFiles(list: FileList | null) {
    const files = list ? Array.from(list) : [];
    if (files.length === 0 || busy) return;

    setError(null);
    setUploadingCount(files.length);
    try {
      await onUpload(files);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed. Try again.");
    } finally {
      setUploadingCount(0);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    if (!busy) setDragging(true);
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    // Moving between child elements fires dragleave too; only reset when leaving the zone.
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    void handleFiles(event.dataTransfer.files);
  }

  return (
    <div
      className="dropzone"
      data-dragging={dragging || undefined}
      data-busy={busy || undefined}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        multiple
        hidden
        data-testid="file-input"
        onChange={(event) => void handleFiles(event.target.files)}
      />
      <p className="dropzone-title" aria-live="polite">
        {busy
          ? `Uploading ${uploadingCount} ${uploadingCount === 1 ? "file" : "files"}…`
          : "Drop CSV files here"}
      </p>
      <button
        type="button"
        className="button"
        disabled={busy}
        aria-describedby={hintId}
        onClick={() => inputRef.current?.click()}
      >
        Choose files
      </button>
      <p className="dropzone-hint" id={hintId}>
        Each file becomes a table. Files must be UTF-8 encoded.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
