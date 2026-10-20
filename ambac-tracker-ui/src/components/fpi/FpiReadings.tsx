/**
 * The first piece's readings at the FPI's step — what a buy-off attests to. Shown in
 * every pass / fail / waive dialog so nobody attests "the first piece conforms" without
 * seeing the numbers. Out-of-spec readings are marked; no readings says so plainly.
 */
import { queryOptions, useQuery } from "@tanstack/react-query";
import { format } from "date-fns";

import { api } from "@/lib/api/generated";

export const fpiRecordOptions = (id: string) =>
    queryOptions({
        queryKey: ["fpi-records", "detail", id] as const,
        queryFn: () => api.api_FPIRecords_retrieve({ params: { id } }),
    });

/** Decimal strings arrive at storage precision ("15.0000", "12.000000"); show the
 *  number, not the padding. Non-numeric values (a pass/fail reading) pass through. */
const num = (v: string | null) => {
    if (v == null) return null;
    const n = Number(v);
    return Number.isFinite(n) ? String(n) : v;
};

const limits = (lo: string | null, hi: string | null) => {
    const l = num(lo), h = num(hi);
    return l != null && h != null ? `${l} – ${h}` : l != null ? `≥ ${l}` : h != null ? `≤ ${h}` : "—";
};

export function FpiReadings({ fpiId }: { fpiId: string }) {
    const { data, isLoading } = useQuery(fpiRecordOptions(fpiId));
    const readings = data?.first_piece_readings ?? [];
    const outOfSpec = readings.filter((r) => r.within_spec === false).length;

    return (
        <div className="space-y-1.5">
            <div className="text-sm font-medium">
                First piece readings{data?.designated_part_info?.erp_id ? ` · ${data.designated_part_info.erp_id}` : ""}
            </div>
            {isLoading ? (
                <p className="text-xs text-muted-foreground">Loading readings…</p>
            ) : readings.length === 0 ? (
                <p className="rounded-md border border-dashed p-2 text-xs text-muted-foreground">
                    No readings were recorded on the first piece at this step. Check the part
                    before attesting.
                </p>
            ) : (
                <>
                    <div className="max-h-48 overflow-y-auto rounded-md border">
                        <table className="w-full text-xs">
                            <thead className="bg-muted/40 text-left text-muted-foreground">
                                <tr>
                                    <th className="p-1.5">Characteristic</th>
                                    <th className="p-1.5 text-right">Reading</th>
                                    <th className="p-1.5 text-right">Limits</th>
                                    <th className="p-1.5">By</th>
                                </tr>
                            </thead>
                            <tbody>
                                {readings.map((r) => (
                                    <tr key={r.id} className={`border-t ${r.within_spec === false ? "bg-destructive/10 text-destructive" : ""}`}>
                                        <td className="p-1.5">{r.label}</td>
                                        <td className="p-1.5 text-right font-medium tabular-nums">
                                            {num(r.value) ?? "—"}{r.unit ? ` ${r.unit}` : ""}
                                            {r.within_spec === false && " · out of spec"}
                                        </td>
                                        <td className="p-1.5 text-right tabular-nums text-muted-foreground">{limits(r.lower_limit, r.upper_limit)}</td>
                                        <td className="p-1.5 text-muted-foreground">
                                            {r.recorded_by_name || "—"} · {format(new Date(r.recorded_at), "PP p")}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {outOfSpec > 0 && (
                        <p className="text-xs text-destructive">
                            {outOfSpec} reading{outOfSpec === 1 ? " is" : "s are"} out of spec.
                        </p>
                    )}
                </>
            )}
        </div>
    );
}
