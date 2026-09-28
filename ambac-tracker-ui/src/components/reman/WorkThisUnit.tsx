import { Play, CheckCircle, Wrench, PackageOpen } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useStartTeardownBatch } from "@/hooks/useStartTeardownBatch";
import { useWorkUnit } from "@/hooks/useWorkUnit";
import { useReleaseCore } from "@/hooks/useReleaseCore";

type WorkableCore = {
    id: string | number;
    status?: string;
    part?: string | number | null;
    work_order?: string | null;
    fulfilment_mode?: string;
};

function errorDetail(err: unknown, fallback: string) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    return detail ?? fallback;
}

/** Teardown and rebuild are run in the DWI operator runtime — the directions for the
 *  step and the capture for it — like any part's work. A core IS a part (see
 *  Documents/CORE_AS_PART_DESIGN.md); this opens its unit there. */
export function WorkThisUnit({ core }: { core: WorkableCore }) {
    const { workUnit, pending } = useWorkUnit();
    const startTeardown = useStartTeardownBatch();
    const release = useReleaseCore();
    const partId = core.part != null ? String(core.part) : null;
    const woId = core.work_order ?? null;

    // On a work order and mid-flow: open the unit at the step it is at.
    const label: Record<string, string> = {
        RECEIVED: "Start teardown",
        IN_DISASSEMBLY: "Continue teardown",
        IN_REBUILD: "Continue rebuild",
    };
    const status = core.status ?? "";
    if (partId && woId && label[status]) {
        return (
            <Button variant="default" disabled={pending} onClick={() => workUnit(partId, woId)}>
                {status === "IN_REBUILD"
                    ? <Wrench className="mr-2 h-4 w-4" />
                    : status === "RECEIVED"
                        ? <Play className="mr-2 h-4 w-4" />
                        : <CheckCircle className="mr-2 h-4 w-4" />}
                {label[status]}
            </Button>
        );
    }

    // Received and on no work order yet: start its teardown (one-core batch on the core
    // type's default teardown process), then open it. If the process is ambiguous the
    // server says so and the Cores list's teardown action lets you pick one.
    if (partId && !woId && core.status === "RECEIVED") {
        return (
            <Button
                variant="default"
                disabled={startTeardown.isPending || pending}
                onClick={() =>
                    startTeardown.mutate(
                        { core_ids: [String(core.id)] },
                        {
                            onSuccess: (res) => workUnit(partId, String(res.work_order_id)),
                            onError: (err: unknown) => {
                                const detail = (err as { response?: { data?: { detail?: string } } })
                                    ?.response?.data?.detail;
                                toast.error(detail ?? "Could not start the teardown.");
                            },
                        },
                    )
                }
            >
                <Play className="mr-2 h-4 w-4" />
                Start teardown
            </Button>
        );
    }
    // Torn down: the teardown's own exit, by fulfilment mode (enforced by the server).
    // Repair-and-return goes into its rebuild, opening there at its first in-scope
    // operation. Exchange is the shop's unit: normally rebuilt to stock, keeping its
    // identity; harvested for parts when its body fails or cores are surplus.
    if (partId && woId && core.status === "DISASSEMBLED") {
        const rebuildIt = () =>
            release.mutate(
                { id: String(core.id), to: "rebuild" },
                {
                    onSuccess: () => { toast.success("Released into rebuild"); workUnit(partId, woId); },
                    onError: (err) => toast.error(errorDetail(err, "Could not release this unit.")),
                },
            );
        const harvestIt = () =>
            release.mutate(
                { id: String(core.id), to: "inventory" },
                {
                    onSuccess: () => toast.success("Harvested — its usable components are stock now"),
                    onError: (err) => toast.error(errorDetail(err, "Could not release this unit.")),
                },
            );
        const busy = release.isPending || pending;
        if (core.fulfilment_mode === "REPAIR_RETURN") {
            return (
                <Button variant="default" disabled={busy} onClick={rebuildIt}>
                    <Wrench className="mr-2 h-4 w-4" /> Release to rebuild
                </Button>
            );
        }
        return (
            <span className="inline-flex gap-2">
                <Button variant="default" disabled={busy} onClick={rebuildIt}>
                    <Wrench className="mr-2 h-4 w-4" /> Rebuild to stock
                </Button>
                <Button variant="outline" disabled={busy} onClick={harvestIt}>
                    <PackageOpen className="mr-2 h-4 w-4" /> Harvest for parts
                </Button>
            </span>
        );
    }
    return null;
}
