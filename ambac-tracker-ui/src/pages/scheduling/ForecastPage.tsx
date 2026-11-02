/** Volume forecast (/production/forecast).
 *
 * Expected new builds by part type and month: the demand nobody has ordered yet. Part
 * types down, months across, edited in place or by re-importing the sheet. Firm orders
 * and RFI deals due in a month use up its forecast, so each cell shows what orders
 * already claim beside it; planning adds only the unclaimed rest (capacity and
 * material outlook on Capacity Planning).
 */
import { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { Download, Plus, Upload } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { blobErrorMessage, downloadBlob } from "@/lib/download";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import {
  type ForecastImportResult, useForecastGrid, useImportForecast, useSetForecastCells,
} from "@/hooks/useVolumeForecast";

type Cell = {
  forecast: number; firm: number; tentative: number; unclaimed: number;
  /** Wholly inside the demand time fence: shown, not planned. */
  fenced?: boolean;
  /** Of `unclaimed`: held back by the fence (a straddling month, pro-rated by days),
   *  and planned. */
  fenced_quantity?: number;
  planned?: number;
  /** Claims that spilled in from a neighbouring month's orders. */
  claimed_from?: { band: string; quantity: number; from_month: string }[];
  /** Orders DUE this month, in full — the true total ordered. */
  ordered_firm?: number;
  ordered_tentative?: number;
};

const FENCE_TIP = "Inside the demand time fence: only orders are planned.";

const monthLabel = (m: string) => {
  const [y, mo] = m.split("-").map(Number);
  return new Date(y, mo - 1, 1).toLocaleString(undefined, { month: "short", year: "2-digit" });
};

/** One editable cell. Saves on blur or Enter when the value changed; blank or 0 clears. */
function ForecastCell({ partTypeId, month, cell, canEdit, fenced }: {
  partTypeId: string; month: string; cell?: Cell; canEdit: boolean; fenced: boolean;
}) {
  const save = useSetForecastCells();
  const initial = cell?.forecast ? String(cell.forecast) : "";
  const [value, setValue] = useState(initial);
  // The TRUE total ordered for this month — orders due in it, firm and RFI — which may
  // exceed the forecast. What the forecast lost (and from which months) is the tooltip's.
  const ordered = (cell?.ordered_firm ?? 0) + (cell?.ordered_tentative ?? 0);
  const over = cell ? ordered - cell.forecast : 0;
  const spilled = (cell?.claimed_from ?? [])
    .map((c) => `${c.band === "tentative" ? "RFI" : "Firm"} ${c.quantity} (from ${monthLabel(c.from_month)})`);
  const title = cell
    ? `Forecast ${cell.forecast}\nOrdered this month: firm ${cell.ordered_firm ?? 0} · RFI ${cell.ordered_tentative ?? 0}`
      + `\nForecast used up by orders: firm ${cell.firm} · RFI ${cell.tentative}`
      + (spilled.length ? `\nof which ${spilled.join(", ")}` : "")
      + (fenced ? `\n${FENCE_TIP}`
        : cell.fenced_quantity
          ? `\nPlanned on top of orders: ${cell.planned} — ${cell.fenced_quantity} of the ${cell.unclaimed} unclaimed fall inside the demand time fence (days before it are pro-rated out)`
          : `\nPlanned on top of orders: ${cell.unclaimed}`)
    : fenced ? FENCE_TIP : undefined;

  const commit = () => {
    const trimmed = value.trim();
    if (trimmed === initial) return;
    const qty = trimmed === "" ? null : Number(trimmed);
    if (qty != null && (!Number.isInteger(qty) || qty < 0)) {
      toast.error("A forecast is a whole number of units.");
      setValue(initial);
      return;
    }
    save.mutate([{ part_type: partTypeId, month, quantity: qty }], {
      onError: (e) => { toast.error(apiErrorMessage(e) ?? "Couldn't save."); setValue(initial); },
    });
  };

  return (
    <td className={`p-0.5 align-top ${fenced ? "bg-muted/50 opacity-70" : ""}`} title={title}>
      {canEdit ? (
        <Input
          value={value}
          inputMode="numeric"
          aria-label={`Forecast for ${month}`}
          className="h-7 w-16 px-1.5 text-right text-xs tabular-nums"
          onChange={(e) => setValue(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }}
        />
      ) : (
        <div className="h-7 w-16 px-1.5 py-1 text-right text-xs tabular-nums">{initial || "—"}</div>
      )}
      {ordered > 0 && (
        <div className={`px-1.5 text-right text-[10px] tabular-nums ${
          over > 0 ? "text-amber-700 dark:text-amber-400"
            : cell && cell.unclaimed === 0 ? "text-green-700 dark:text-green-400" : "text-muted-foreground"}`}>
          {ordered} ordered{over > 0 ? ` · ${over} over forecast` : ""}
        </div>
      )}
    </td>
  );
}

function ImportForecastDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ForecastImportResult | null>(null);
  const upload = useImportForecast();

  const downloadTemplate = async () => {
    try {
      const resp = await api.axios.get("/api/VolumeForecasts/import-sheet-template/", { responseType: "blob" });
      downloadBlob(resp.data, "volume_forecast_template.csv");
    } catch (e) {
      toast.error(await blobErrorMessage(e, "Couldn't download the template."));
    }
  };

  const close = (o: boolean) => {
    if (!o) { setFile(null); setResult(null); }
    onOpenChange(o);
  };

  const errors = (result?.rows ?? []).filter((r) => r.outcome === "ERROR" || r.detail);

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Import forecast</DialogTitle>
          <DialogDescription>
            One row per part type and month. Each row replaces the forecast for the month it
            names; months the sheet leaves out keep what they have. A blank or 0 quantity
            clears that month.
          </DialogDescription>
        </DialogHeader>
        {!result ? (
          <div className="space-y-3">
            <Button variant="outline" size="sm" onClick={downloadTemplate}>
              <Download className="mr-1.5 h-4 w-4" /> Template (.csv)
            </Button>
            <p className="text-xs text-muted-foreground">
              Columns: Item (the part type&rsquo;s ERP id, or its exact name), Month
              (YYYY-MM), Quantity.
            </p>
            <Input type="file" accept=".csv,.xlsx" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </div>
        ) : (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap gap-2">
              <Badge>{result.created} added</Badge>
              <Badge variant="secondary">{result.updated} updated</Badge>
              <Badge variant="outline">{result.unchanged} no change</Badge>
              {result.cleared > 0 && <Badge variant="outline">{result.cleared} cleared</Badge>}
              {result.errors > 0 && <Badge variant="destructive">{result.errors} not imported</Badge>}
            </div>
            {errors.length > 0 && (
              <ul className="space-y-1 text-xs">
                {errors.map((r) => (
                  <li key={r.row}>
                    <span className="font-medium">Row {r.row}</span>
                    {r.item ? ` (${r.item}${r.month ? ` ${r.month}` : ""})` : ""}: {r.detail}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        <DialogFooter>
          {!result ? (
            <Button disabled={!file || upload.isPending}
                    onClick={() => file && upload.mutate(file, {
                      onSuccess: (r) => setResult(r as ForecastImportResult),
                      onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't read that file."),
                    })}>
              <Upload className="mr-1.5 h-4 w-4" /> Import
            </Button>
          ) : (
            <Button onClick={() => close(false)}>Done</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ForecastPage() {
  const { data, isLoading } = useForecastGrid(24);
  // Months inside the demand time fence: editable, but only orders are planned there.
  const fenced = new Set<string>(data?.fenced_months ?? []);
  const { has } = usePermissionSet();
  const canEdit = has("add_volumeforecast") && has("change_volumeforecast");
  const { data: partTypesData } = useRetrievePartTypes({ limit: 500 });
  const [added, setAdded] = useState<string[]>([]);
  const [importOpen, setImportOpen] = useState(false);

  // Rows: every part type with a forecast in the window, plus any added here to fill in.
  const rows = useMemo(() => {
    const have = new Map((data?.rows ?? []).map((r) => [r.part_type_id, r]));
    const extra = added
      .filter((id) => !have.has(id))
      .map((id) => {
        const pt = (partTypesData?.results ?? []).find((p) => p.id === id);
        return { part_type_id: id, part_type: pt?.name ?? id, erp_id: pt?.ERP_id ?? "", cells: {} };
      });
    return [...(data?.rows ?? []), ...extra];
  }, [data, added, partTypesData]);

  const addable = (partTypesData?.results ?? []).filter((p) => !rows.some((r) => r.part_type_id === p.id));

  return (
    <div className="space-y-6 p-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Volume forecast</h1>
          <p className="max-w-3xl text-sm text-muted-foreground">
            New builds you expect by part type and month, beyond firm orders. Orders due in a
            month use up its forecast — firm and RFI alike — so only the rest is planned on
            top. The load it adds shows on{" "}
            <Link to="/production/capacity" search={{}} className="underline underline-offset-2">Capacity planning</Link>.
          </p>
        </div>
        {canEdit && (
          <Button variant="outline" onClick={() => setImportOpen(true)}>
            <Upload className="mr-1.5 h-4 w-4" /> Import forecast
          </Button>
        )}
      </header>

      <div className="overflow-x-auto rounded-lg border">
        {isLoading ? (
          <p className="p-4 text-sm text-muted-foreground">Loading forecast…</p>
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-muted/40">
                <th className="sticky left-0 z-10 bg-muted/40 px-3 py-2 text-left text-xs font-medium">Part type</th>
                {(data?.months ?? []).map((m) => (
                  <th key={m} title={fenced.has(m) ? FENCE_TIP : undefined}
                      className={`px-1.5 py-2 text-right text-xs font-medium whitespace-nowrap ${fenced.has(m) ? "text-muted-foreground" : ""}`}>
                    {monthLabel(m)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td colSpan={(data?.months.length ?? 0) + 1} className="p-4 text-sm text-muted-foreground">
                    No forecast yet. {canEdit ? "Add a part type below, or import a sheet." : ""}
                  </td>
                </tr>
              )}
              {rows.map((r) => (
                <tr key={r.part_type_id} className="border-t">
                  <th scope="row" className="sticky left-0 z-10 bg-background px-3 py-1.5 text-left text-xs font-medium">
                    <div className="truncate">{r.part_type}</div>
                    {r.erp_id && <div className="text-[10px] font-normal text-muted-foreground">{r.erp_id}</div>}
                  </th>
                  {(data?.months ?? []).map((m) => (
                    <ForecastCell key={`${m}:${(r.cells as Record<string, Cell>)[m]?.forecast ?? ""}`}
                                  partTypeId={r.part_type_id} month={m}
                                  cell={(r.cells as Record<string, Cell>)[m]} canEdit={canEdit}
                                  fenced={fenced.has(m)} />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {canEdit && addable.length > 0 && (
        <div className="flex items-center gap-2">
          <Plus className="h-4 w-4 text-muted-foreground" />
          <Select value="" onValueChange={(id) => setAdded((a) => [...a, id])}>
            <SelectTrigger className="w-72"><SelectValue placeholder="Add a part type…" /></SelectTrigger>
            <SelectContent>
              {addable.map((p) => (
                <SelectItem key={p.id} value={p.id}>{p.ERP_id ? `${p.ERP_id} — ${p.name}` : p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <ImportForecastDialog open={importOpen} onOpenChange={setImportOpen} />
    </div>
  );
}
