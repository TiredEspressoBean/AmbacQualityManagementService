// Minimal client-side CSV export — builds a CSV from rows and triggers a download.
// Opens directly in Excel/Google Sheets. For the aggregate report pages whose data is
// already in the browser; model-editor bulk exports use the server-side Excel endpoint.

type Cell = string | number | null | undefined;

// A text cell Excel would run as a formula when the file is opened: starting with =, +, -,
// @, tab or carriage return (CSV / formula injection). These cells carry names and notes
// people type, so they get the standard guard — a leading apostrophe, which Excel reads
// as "this is text". Numbers are left alone: a number cell is never a formula, and a
// numeric string like "-5" is a number, not an attack.
const FORMULA_START = /^[=+\-@\t\r]/;
const PLAIN_NUMBER = /^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$/;

function escape(cell: Cell): string {
  let s = cell == null ? "" : String(cell);
  if (typeof cell === "string" && FORMULA_START.test(s) && !PLAIN_NUMBER.test(s)) {
    s = `'${s}`;
  }
  // Quote if it contains a comma, quote, CR or LF; double embedded quotes. A bare CR
  // was left unquoted before, which splits the row in some readers.
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** Download `rows` as a CSV file. `headers` are the column titles; each row is an array of
 *  cells in the same order. */
export function downloadCsv(filename: string, headers: string[], rows: Cell[][]): void {
  const lines = [headers.map(escape).join(","), ...rows.map((r) => r.map(escape).join(","))];
  // BOM so Excel reads UTF-8 correctly.
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
