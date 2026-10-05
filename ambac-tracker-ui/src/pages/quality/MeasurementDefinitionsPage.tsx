/**
 * Every measurement definition across all steps, in one read-mostly list.
 *
 * Editing stays in the step editor's measurement dialogs (a definition belongs to a
 * step and versions with it), so each row links to its step's editor. The list data
 * carries the step name but not its process, so the Step column shows the step alone;
 * the Process filter narrows the list server-side (`step__process`).
 *
 * Import / Export come from DataIOButtons rather than ModelEditorPage's built-in pair
 * so the export carries the process filter.
 */
import { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { DataIOButtons } from "@/components/data-io-buttons";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { useRetrieveMeasurementDefinitions } from "@/hooks/useRetrieveMeasurementDefinitions";
import { useRetrieveProcesses } from "@/hooks/useRetrieveProcesses";
import type { components } from "@/lib/api/generated-types";
import { useAllows } from "@/pages/scheduling/setup/shared";

type MeasurementDefinition = components["schemas"]["MeasurementDefinition"];
const col = createColumnHelper<MeasurementDefinition>();
const LIST_KEY = "measurementDefinitions";

const num = (v: string | null | undefined) => (v == null || v === "" ? null : String(Number(v)));

function tolerance(m: MeasurementDefinition) {
    const up = num(m.upper_tol);
    const low = num(m.lower_tol);
    if (up == null && low == null) return <span className="text-muted-foreground">—</span>;
    return <span className="tabular-nums">+{up ?? "0"} / -{low ?? "0"}</span>;
}

function gauges(m: MeasurementDefinition) {
    if (!m.default_equipment_name && !m.backup_equipment_name) {
        return <span className="text-muted-foreground">—</span>;
    }
    return (
        <div className="flex flex-col text-sm">
            {m.default_equipment_name && <span>{m.default_equipment_name}</span>}
            {m.backup_equipment_name && (
                <span className="text-muted-foreground">Backup: {m.backup_equipment_name}</span>
            )}
        </div>
    );
}

function useMeasurementsListFor(processId: string | null) {
    return function useMeasurementsList({ offset, limit, ordering, search, filters }: {
        offset: number; limit: number; ordering?: string; search?: string;
        filters?: Record<string, string>;
    }) {
        return useRetrieveMeasurementDefinitions({
            ...filters,
            offset, limit,
            ...(ordering ? { ordering } : {}),
            ...(search ? { search } : {}),
            ...(processId ? { step__process: processId } : {}),
        });
    };
}

export function MeasurementDefinitionsPage() {
    const allows = useAllows();
    const canImport = allows("add_measurementdefinition") || allows("change_measurementdefinition");
    const [processId, setProcessId] = useState<string | null>(null);

    const { data: processesPage } = useRetrieveProcesses({ limit: 500, ordering: "name" });
    const processes = useMemo(
        () => (processesPage?.results ?? []).map((p) => ({
            id: String(p.id),
            label: p.part_type_name ? `${p.name} · ${p.part_type_name}` : p.name,
        })),
        [processesPage],
    );

    const processFilter = (
        <div className="flex items-center gap-1">
            <Select value={processId ?? "__all__"} onValueChange={(v) => setProcessId(v === "__all__" ? null : v)}>
                <SelectTrigger className="w-[220px]" aria-label="Filter by process">
                    <SelectValue placeholder="All processes" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="__all__">All processes</SelectItem>
                    {processes.map((p) => (
                        <SelectItem key={p.id} value={p.id}>{p.label}</SelectItem>
                    ))}
                </SelectContent>
            </Select>
            {processId && (
                <Button variant="ghost" size="icon" aria-label="Clear process filter" onClick={() => setProcessId(null)}>
                    <X className="h-4 w-4" />
                </Button>
            )}
        </div>
    );

    return (
        <ModelEditorPage
            title="Measurement Definitions"
            modelName="MeasurementDefinitions"
            listQueryKey={[LIST_KEY]}
            useList={useMeasurementsListFor(processId)}
            disableExport
            showDetailsLink={false}
            sortOptions={[
                { label: "Label (A-Z)", value: "label" },
                { label: "Label (Z-A)", value: "-label" },
                { label: "Step (A-Z)", value: "step__name" },
                { label: "Step (Z-A)", value: "-step__name" },
            ]}
            headerContent={
                <p className="text-sm text-muted-foreground">
                    Every measurement taken at every step. To change one, open its step: definitions
                    are edited, and versioned, in the step editor.
                </p>
            }
            extraToolbarContent={
                <>
                    {processFilter}
                    <DataIOButtons
                        endpoint="MeasurementDefinitions"
                        displayName="Measurement Definitions"
                        invalidateKeys={[[LIST_KEY]]}
                        allowImport={canImport}
                        {...(processId ? { queryParams: { step__process: processId } } : {})}
                    />
                </>
            }
            columns={[
                col({
                    header: "Label",
                    priority: 1,
                    renderCell: (m) => (
                        <div className="flex flex-wrap items-center gap-2">
                            {m.characteristic_number && (
                                <Badge variant="outline" className="font-mono">#{m.characteristic_number}</Badge>
                            )}
                            <span className="font-medium">{m.label}</span>
                            {!m.is_current_version && <Badge variant="secondary">Superseded v{m.version}</Badge>}
                        </div>
                    ),
                }),
                col({
                    header: "Step",
                    priority: 1,
                    renderCell: (m) => (
                        <Link to="/editor/steps/$id/edit" params={{ id: String(m.step) }}
                            className="text-primary hover:underline">
                            {m.step_name}
                        </Link>
                    ),
                }),
                col({
                    header: "Type",
                    priority: 2,
                    renderCell: (m) => (
                        <Badge variant="secondary">{m.type === "PASS_FAIL" ? "Pass / fail" : "Numeric"}</Badge>
                    ),
                }),
                col({ header: "Unit", priority: 2, renderCell: (m) => m.unit || <span className="text-muted-foreground">—</span> }),
                col({
                    header: "Nominal",
                    priority: 1,
                    renderCell: (m) => num(m.nominal) ?? <span className="text-muted-foreground">—</span>,
                }),
                col({ header: "Tolerance", priority: 2, renderCell: tolerance }),
                col({ header: "Gauges", priority: 3, renderCell: gauges }),
                col({
                    header: "Flags",
                    priority: 3,
                    renderCell: (m) => (
                        <div className="flex gap-1">
                            {m.required && <Badge variant="outline">Required</Badge>}
                            {m.spc_enabled && <Badge variant="outline">SPC</Badge>}
                        </div>
                    ),
                }),
            ]}
        />
    );
}
