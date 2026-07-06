import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";
import type { components } from "@/lib/api/generated-types";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PackagePlus, Settings } from "lucide-react";
import { useCreateReceivingPlan } from "@/hooks/useReceivingPlans";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";

const col = createColumnHelper<Schema<"Steps">>();

/**
 * Receiving Inspection Plans (RIPs) — purchased-material incoming inspection, by
 * part type, process-free. Each row is a standalone RECEIVING step; configuring it
 * opens the same characteristics + sampling editors as the flow canvas. In-process
 * RECEIVING steps belong to their process and are excluded server-side.
 *
 * Lists via the paginated `Steps/receiving_plans` endpoint through ModelEditorPage,
 * so paging / search / sort behave like every other list in the app.
 */
function useReceivingPlansList(params: { offset: number; limit: number; ordering?: string; search?: string }) {
  // Standalone (process-free) RECEIVING steps via the standard, auto-paginated Steps
  // list endpoint — `standalone=true` + `step_type=RECEIVING` (no custom action).
  const queries: Record<string, unknown> = {
    offset: params.offset, limit: params.limit, step_type: "RECEIVING", standalone: true,
  };
  if (params.ordering) queries.ordering = params.ordering;
  if (params.search) queries.search = params.search;
  return useQuery({
    queryKey: ["receiving-plans", queries] as const,
    queryFn: () =>
      api.api_Steps_list({ queries } as never) as Promise<components["schemas"]["PaginatedStepsList"]>,
  });
}

export function ReceivingInspectionPlansPage() {
  const navigate = useNavigate();
  const createPlan = useCreateReceivingPlan();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [partType, setPartType] = useState<string>("");
  const { data: partTypes } = useRetrievePartTypes({ limit: 200 } as never);

  const handleCreate = () => {
    if (!partType) return;
    createPlan.mutate(
      { part_type: partType },
      {
        onSuccess: (step: { id?: string }) => {
          toast.success("Receiving plan created");
          setDialogOpen(false);
          setPartType("");
          if (step?.id) navigate({ to: "/production/receiving-plans/$stepId", params: { stepId: String(step.id) } });
        },
        onError: () => toast.error("Could not create receiving plan"),
      },
    );
  };

  return (
    <>
      <ModelEditorPage
        title="Receiving Inspection Plans"
        modelName="Steps"
        useList={useReceivingPlansList}
        extraToolbarContent={
          <Button size="sm" onClick={() => setDialogOpen(true)}>
            <PackagePlus className="h-4 w-4 mr-1" /> New Plan
          </Button>
        }
        sortOptions={[
          { label: "Name (A–Z)", value: "name" },
          { label: "Part type", value: "part_type__name" },
        ]}
        columns={[
          col({ header: "Plan", renderCell: (s) => <span className="font-medium">{s.name}</span> }),
        ]}
        renderActions={(s) => (
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate({ to: "/production/receiving-plans/$stepId", params: { stepId: String(s.id) } })}
          >
            <Settings className="h-4 w-4 mr-1" /> Configure
          </Button>
        )}
        showDetailsLink={false}
        // The list is hard-scoped to standalone RECEIVING steps in useList, so the
        // generic Steps filter dropdowns (step_type / standalone) would be redundant
        // and confusing — suppress the metadata-driven filter UI.
        disableMetadata
      />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New Receiving Inspection Plan</DialogTitle>
            <DialogDescription>Pick the part type this plan inspects on receipt.</DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5 py-1">
            <Label>Part type</Label>
            <Select value={partType} onValueChange={setPartType}>
              <SelectTrigger><SelectValue placeholder="Choose a part type…" /></SelectTrigger>
              <SelectContent>
                {(partTypes?.results ?? []).map((pt) => (
                  <SelectItem key={pt.id} value={String(pt.id)}>{pt.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button disabled={!partType || createPlan.isPending} onClick={handleCreate}>
              {createPlan.isPending ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
