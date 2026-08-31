// Minimal client-side CSV export — builds a CSV from rows and triggers a download.
// Opens directly in Excel/Google Sheets. For the aggregate report pages whose data is
// already in the browser; model-editor bulk exports use the server-side Excel endpoint.

type Cell = string | number | null | undefined;

function escape(cell: Cell): string {
  const s = cell == null ? "" : String(cell);
  // Quote if it contains a comma, quote, or newline; double embedded quotes.
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
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
