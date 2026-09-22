import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { useRetrieveRepairCodes, repairCodesOptions } from "@/hooks/useRepairCodes";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";
import { Pencil } from "lucide-react";

const col = createColumnHelper<Schema<"RepairCode">>();

const DEFAULT_LIST_PARAMS = { offset: 0, limit: 25, search: "" };

export const prefetchRepairCodesEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(repairCodesOptions(DEFAULT_LIST_PARAMS));
};

// What raises a code, in the words an engineer would use rather than the enum.
const TRIGGER_LABEL: Record<string, string> = {
    RECONDITION: "Component needs work",
    REPLACE_POOL: "Filled from recovered stock",
    REPLACE_BUY: "Filled by a purchase",
    REUSE: "Component goes back as-is",
    ALWAYS: "Always",
    PRESET: "Only via a rebuild level",
};

function useRepairCodesList({
    offset, limit, ordering, search, filters,
}: {
    offset: number; limit: number; ordering?: string; search?: string;
    filters?: Record<string, string>;
}) {
    return useRetrieveRepairCodes({ offset, limit, ordering, search, ...filters });
}

export function RepairCodesEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Repair Codes"
            modelName="RepairCodes"
            useList={useRepairCodesList}
            sortOptions={[
                { label: "Code (A-Z)", value: "code" },
                { label: "Code (Z-A)", value: "-code" },
            ]}
            columns={[
                col({
                    header: "Code",
                    priority: 1,
                    renderCell: (item) => (
                        <span className="font-mono text-sm font-medium">{item.code}</span>
                    ),
                }),
                col({ header: "Name", priority: 1, renderCell: (item) => item.name }),
                col({
                    header: "Raised by",
                    priority: 2,
                    renderCell: (item) => (
                        <Badge variant={item.trigger === "ALWAYS" ? "default" : "secondary"}>
                            {TRIGGER_LABEL[item.trigger ?? ""] ?? item.trigger}
                        </Badge>
                    ),
                }),
                col({
                    header: "Component",
                    priority: 3,
                    // Blank means "whatever the component" — whole-unit work like a
                    // final test, raised by any slot taking that resolution.
                    renderCell: (item) => item.component_type_name || "Any component",
                }),
                col({
                    header: "Operations",
                    priority: 2,
                    renderCell: (item) => {
                        const names = item.step_names ?? [];
                        if (names.length === 0) {
                            return (
                                <span className="text-destructive text-sm">
                                    none — adds no work
                                </span>
                            );
                        }
                        return <span className="text-sm">{names.join(", ")}</span>;
                    },
                }),
            ]}
            renderActions={(item) => (
                <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => navigate({ to: `/editor/repair-codes/${item.id}/edit` })}
                    aria-label={`Edit ${item.code}`}
                >
                    <Pencil className="h-4 w-4" />
                </Button>
            )}
            onCreate={() => navigate({ to: "/editor/repair-codes/new" })}
        />
    );
}
