import type { CellValue } from "./types";

export interface ColumnFormat {
  /** All non-empty values are numbers (and there is at least one): aligned right. */
  numeric: boolean;
  /** Digits after the decimal point, the same for the whole column so decimals line up. */
  decimals: number;
}

// Beyond this, extra digits are float noise (0.1 + 0.2), not information.
const MAX_DECIMALS = 6;

export function columnFormats(rows: CellValue[][], columnCount: number): ColumnFormat[] {
  return Array.from({ length: columnCount }, (_, index) => {
    let sawNumber = false;
    let decimals = 0;
    for (const row of rows) {
      const value = row[index];
      if (value === null || value === undefined) continue;
      if (typeof value !== "number") return { numeric: false, decimals: 0 };
      sawNumber = true;
      decimals = Math.max(decimals, fractionDigits(value));
    }
    return { numeric: sawNumber, decimals: Math.min(decimals, MAX_DECIMALS) };
  });
}

export function formatCell(value: CellValue, format: ColumnFormat | undefined): string {
  if (typeof value === "number" && format?.numeric && Number.isFinite(value)) {
    // Exponent notation (1e21) has no fixed-point form worth forcing.
    return String(value).includes("e") ? String(value) : value.toFixed(format.decimals);
  }
  return String(value);
}

function fractionDigits(value: number): number {
  const text = String(value);
  if (text.includes("e")) return 0;
  const dot = text.indexOf(".");
  return dot === -1 ? 0 : text.length - dot - 1;
}
