import { describe, expect, it } from "vitest";

import { columnFormats, formatCell } from "./tableData";

describe("columnFormats", () => {
  it("treats a column as numeric only when every value is a number", () => {
    const rows = [
      ["Prague", 1, null],
      ["Brno", 2.5, "x"],
    ];
    expect(columnFormats(rows, 3).map((format) => format.numeric)).toEqual([false, true, false]);
  });

  it("does not call an all-empty column numeric", () => {
    expect(columnFormats([[null], [null]], 1)[0]!.numeric).toBe(false);
  });

  it("pads decimals so the column lines up", () => {
    const rows = [[1478.59], [1037.5], [53]];
    const [format] = columnFormats(rows, 1);
    expect(rows.map(([value]) => formatCell(value!, format))).toEqual([
      "1478.59",
      "1037.50",
      "53.00",
    ]);
  });

  it("caps float noise", () => {
    const [format] = columnFormats([[0.1 + 0.2], [1]], 1);
    expect(format!.decimals).toBe(6);
    expect(formatCell(1, format)).toBe("1.000000");
  });

  it("leaves integers and text alone", () => {
    const [ids, names] = columnFormats(
      [
        [1001, "a"],
        [1002, "b"],
      ],
      2,
    );
    expect(formatCell(1001, ids)).toBe("1001");
    expect(formatCell("a", names)).toBe("a");
  });
});
