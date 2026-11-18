/**
 * The defects found on an inspection record: error type, severity, location, count,
 * notes — one row each. The one editor for every place a failed record is made: the
 * DWI's defect field, Record Inspection, Raise NCR / Add parts, and a finding added
 * later on an NCR. They all write through services/qms/quality_report.record_defects,
 * so what's found here reaches defect analysis, the Pareto and the heat map, and an
 * undecided NCR takes its worst defect's severity.
 */
import { Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRetrieveErrorTypes } from "@/hooks/useRetrieveErrorTypes";

export type DefectSeverity = "MINOR" | "MAJOR" | "CRITICAL";

export type DefectRow = {
    // QualityErrorsList id (a UUID string).
    error_type_id: string;
    severity: DefectSeverity;
    location?: string;
    notes?: string;
    count: number;
};

const SEVERITY_LABELS: Record<DefectSeverity, string> = { MINOR: "Minor", MAJOR: "Major", CRITICAL: "Critical" };
const SEVERITIES: DefectSeverity[] = ["MINOR", "MAJOR", "CRITICAL"];
const SEVERITY_CLS: Record<DefectSeverity, string> = {
    MINOR: "text-blue-600",
    MAJOR: "text-amber-600",
    CRITICAL: "text-destructive",
};

/** The rows as the API's `defect_rows` takes them. */
export const toDefectRowsPayload = (rows: DefectRow[]) => rows.map((r) => ({
    error_type: r.error_type_id,
    severity: r.severity,
    count: r.count || 1,
    location: r.location ?? "",
    notes: r.notes ?? "",
}));

/** The worst severity among the rows, or null — what an NCR raised over them would read. */
export const worstSeverity = (rows: DefectRow[]): DefectSeverity | null =>
    rows.reduce<DefectSeverity | null>((w, r) =>
        w == null || SEVERITIES.indexOf(r.severity) > SEVERITIES.indexOf(w) ? r.severity : w, null);

export function DefectRowsEditor({
    rows, onChange, disabled = false, defaultSeverity = "MAJOR", emptyText = "No defects recorded.",
}: {
    rows: DefectRow[];
    onChange: (rows: DefectRow[]) => void;
    disabled?: boolean;
    defaultSeverity?: DefectSeverity;
    emptyText?: string;
}) {
    const { data: errorTypesResp } = useRetrieveErrorTypes();
    const errorTypes = (errorTypesResp?.results ?? []) as { id: string; error_name: string }[];

    const addRow = () => {
        const first = errorTypes[0];
        if (!first) return;
        onChange([...rows, { error_type_id: first.id, severity: defaultSeverity, count: 1 }]);
    };
    const setRow = (i: number, patch: Partial<DefectRow>) => {
        const next = rows.slice();
        next[i] = { ...next[i]!, ...patch };
        onChange(next);
    };
    const removeRow = (i: number) => onChange(rows.filter((_, j) => j !== i));

    return (
        <div className="space-y-1.5">
            {rows.map((row, i) => (
                <div key={i} className="space-y-1 rounded border bg-background p-1.5">
                    <div className="flex items-center gap-1">
                        <select
                            aria-label="Defect type"
                            disabled={disabled}
                            value={row.error_type_id}
                            onChange={(e) => setRow(i, { error_type_id: e.target.value })}
                            className="h-7 flex-1 rounded border bg-background px-2 text-xs"
                        >
                            {errorTypes.map((et) => (
                                <option key={et.id} value={et.id}>{et.error_name}</option>
                            ))}
                        </select>
                        <select
                            aria-label="Severity"
                            disabled={disabled}
                            value={row.severity}
                            onChange={(e) => setRow(i, { severity: e.target.value as DefectSeverity })}
                            className={`h-7 w-24 rounded border bg-background px-1 text-xs font-medium ${SEVERITY_CLS[row.severity]}`}
                        >
                            {SEVERITIES.map((s) => <option key={s} value={s}>{SEVERITY_LABELS[s]}</option>)}
                        </select>
                        {!disabled && (
                            <Button type="button" variant="ghost" size="sm" onClick={() => removeRow(i)}
                                    className="h-7 w-7 p-0" aria-label="Remove defect">
                                <X className="h-3 w-3" />
                            </Button>
                        )}
                    </div>
                    <div className="flex items-center gap-1">
                        <Input
                            type="text"
                            disabled={disabled}
                            value={row.location ?? ""}
                            placeholder="Location (e.g. near bore #3)"
                            onChange={(e) => setRow(i, { location: e.target.value })}
                            className="h-7 flex-1 text-xs"
                            aria-label="Location"
                        />
                        <Input
                            type="number"
                            min={1}
                            disabled={disabled}
                            value={String(row.count ?? 1)}
                            onChange={(e) => setRow(i, { count: Math.max(1, Number(e.target.value) || 1) })}
                            className="h-7 w-14 text-xs"
                            title="Count"
                            aria-label="Count"
                        />
                    </div>
                    <Input
                        type="text"
                        disabled={disabled}
                        value={row.notes ?? ""}
                        placeholder="Notes"
                        onChange={(e) => setRow(i, { notes: e.target.value })}
                        className="h-7 text-xs"
                        aria-label="Notes"
                    />
                </div>
            ))}
            {rows.length === 0 && <div className="text-xs italic text-muted-foreground">{emptyText}</div>}
            {!disabled && (
                <Button type="button" variant="ghost" size="sm" onClick={addRow}
                        className="h-7 w-full justify-start text-xs text-muted-foreground">
                    <Plus className="mr-1 h-3 w-3" /> Add defect
                </Button>
            )}
        </div>
    );
}
