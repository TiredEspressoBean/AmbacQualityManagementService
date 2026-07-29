import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";

// Full-report view of the MeasurementResult rows linked to a QualityReport.
// Populated by the DWI inline-capture path (Tier 2 writes: one QR per
// inspection-point substep, results accumulate). The QR view page used to
// stop at the free-text description; inspectors reviewing an inspection-point
// substep capture had no way to see the actual numeric evidence without
// grepping the DB.
export function QRMeasurementsSection({ modelData }: { modelData: Record<string, unknown> }) {
    const measurements = (modelData?.measurements as MeasurementRow[] | undefined) ?? [];
    if (measurements.length === 0) return null;

    return (
        <>
            <Separator />
            <section className="space-y-3">
                <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                        Measurements
                    </h3>
                    <Badge variant="secondary">{measurements.length}</Badge>
                </div>
                <div className="rounded-md border overflow-x-auto">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Characteristic</TableHead>
                                <TableHead>Value</TableHead>
                                <TableHead>Spec</TableHead>
                                <TableHead>Result</TableHead>
                                <TableHead className="text-right">Captured</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {measurements.map((m) => (
                                <TableRow key={String(m.id)}>
                                    <TableCell className="font-medium">
                                        {m.definition_info?.label ?? "—"}
                                        {m.sample_number != null && (
                                            <span className="ml-2 text-xs text-muted-foreground">
                                                #{m.sample_number}
                                            </span>
                                        )}
                                    </TableCell>
                                    <TableCell>{formatValue(m)}</TableCell>
                                    <TableCell className="text-muted-foreground">{formatSpec(m)}</TableCell>
                                    <TableCell>
                                        <SpecBadge inSpec={m.is_within_spec} type={m.definition_info?.type} />
                                    </TableCell>
                                    <TableCell className="text-right text-xs text-muted-foreground">
                                        {m.created_at ? new Date(m.created_at).toLocaleString() : "—"}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            </section>
        </>
    );
}

type MeasurementRow = {
    id: number | string;
    value_numeric: number | null;
    value_pass_fail: "PASS" | "FAIL" | null;
    is_within_spec: boolean;
    sample_number: number | null;
    created_at: string | null;
    definition_info: {
        id: number;
        label: string;
        type: "NUMERIC" | "PASS_FAIL" | string;
        unit: string;
        nominal: string | null;
        upper_tol: string | null;
        lower_tol: string | null;
    } | null;
};

function formatValue(m: MeasurementRow): string {
    if (m.definition_info?.type === "PASS_FAIL") {
        return m.value_pass_fail ?? "—";
    }
    if (m.value_numeric == null) return "—";
    const unit = m.definition_info?.unit ?? "";
    return unit ? `${m.value_numeric} ${unit}` : String(m.value_numeric);
}

function formatSpec(m: MeasurementRow): string {
    const d = m.definition_info;
    if (!d) return "—";
    if (d.type === "PASS_FAIL") return "Pass / Fail";
    if (d.nominal == null) return "—";
    const nominal = trimTrailingZeros(d.nominal);
    const upper = d.upper_tol != null ? trimTrailingZeros(d.upper_tol) : null;
    const lower = d.lower_tol != null ? trimTrailingZeros(d.lower_tol) : null;
    const unit = d.unit ? ` ${d.unit}` : "";
    if (upper && lower && upper === lower) {
        return `${nominal} ± ${upper}${unit}`;
    }
    if (upper || lower) {
        return `${nominal} +${upper ?? "0"} / -${lower ?? "0"}${unit}`;
    }
    return `${nominal}${unit}`;
}

function trimTrailingZeros(s: string): string {
    if (!s.includes(".")) return s;
    return s.replace(/0+$/, "").replace(/\.$/, "");
}

function SpecBadge({ inSpec, type }: { inSpec: boolean; type?: string }) {
    const label = type === "PASS_FAIL" ? (inSpec ? "PASS" : "FAIL") : inSpec ? "IN SPEC" : "OUT OF SPEC";
    const tone = inSpec
        ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
        : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300";
    return <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${tone}`}>{label}</span>;
}
