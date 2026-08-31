// "Materials consumed here" — the operation-view of the BOM allocation, shown in the flow
// step editor. Lists the part type's BOM lines consumed at THIS step (BOMLine.consumed_at_step)
// and lets you assign/unassign lines to it. Same data the Part Type BOM panel edits, from the
// op's perspective. Editing requires a DRAFT BOM (released BOMs are immutable — revise them
// on the Part Type); otherwise it's read-only.
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { api } from "@/lib/api/generated";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";
import { useEffectiveBom, useUpdateBomLine } from "@/hooks/useBom";

const lineLabel = (l: any) =>
  (l.source === "BUY" ? l.material_name : l.component_type_name) || "component";

export function StepBomSection({
  stepId, processId, editable,
}: {
  stepId: string;
  processId?: string | null;
  editable: boolean;
}) {
  const [addOpen, setAddOpen] = useState(false);

  const { data: proc } = useQuery({
    queryKey: ["process", "part-type", processId] as const,
    enabled: !!processId,
    queryFn: () => api.api_Processes_retrieve({ params: { id: processId } } as never) as Promise<any>,
  });
  const partTypeId = (proc as any)?.part_type ?? null;
  const { bom, isDraft, isLoading } = useEffectiveBom(partTypeId);
  const updateLine = useUpdateBomLine();

  if (!partTypeId) return null; // unsaved process / no part type — nothing to allocate

  const lines: any[] = bom?.lines ?? [];
  const here = lines.filter((l) => String(l.consumed_at_step) === stepId);
  const assignable = lines.filter((l) => String(l.consumed_at_step) !== stepId);
  const canEdit = editable && isDraft;

  const assign = (id: string) => updateLine.mutate({ id, consumed_at_step: stepId });
  const unassign = (id: string) => updateLine.mutate({ id, consumed_at_step: null });

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">Materials consumed here</Label>
        {bom && (
          <Badge variant={isDraft ? "secondary" : "outline"} className="text-[10px]">
            Rev {bom.revision} · {bom.status}
          </Badge>
        )}
      </div>

      {isLoading ? (
        <p className="text-xs text-muted-foreground">Loading BOM…</p>
      ) : !bom ? (
        <p className="text-xs text-muted-foreground">
          No BOM for this part type yet — author one on the Part Type.
        </p>
      ) : (
        <>
          {here.length === 0 ? (
            <p className="text-xs text-muted-foreground">Nothing consumed at this step.</p>
          ) : (
            <div className="space-y-1">
              {here.map((l) => (
                <div key={l.id} className="flex items-center gap-2 rounded border px-2 py-1 text-sm">
                  <Badge variant={l.source === "BUY" ? "outline" : "secondary"} className="text-[10px]">
                    {l.source === "BUY" ? "Buy" : "Make"}
                  </Badge>
                  <span className="min-w-0 flex-1 truncate">{lineLabel(l)}</span>
                  <span className="text-xs text-muted-foreground">×{l.quantity}</span>
                  {canEdit && (
                    <button
                      type="button"
                      onClick={() => unassign(String(l.id))}
                      className="rounded p-0.5 text-muted-foreground hover:text-destructive"
                      title="Remove from this step"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {canEdit ? (
            <Popover open={addOpen} onOpenChange={setAddOpen}>
              <PopoverTrigger asChild>
                <Button variant="outline" size="sm" disabled={assignable.length === 0}>
                  <Plus className="mr-1 h-4 w-4" /> Add material to this step
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-72 p-0" align="start">
                <Command>
                  <CommandInput placeholder="Search BOM lines…" />
                  <CommandList>
                    <CommandEmpty>No other BOM lines.</CommandEmpty>
                    <CommandGroup>
                      {assignable.map((l) => (
                        <CommandItem
                          key={l.id}
                          value={lineLabel(l)}
                          onSelect={() => { assign(String(l.id)); setAddOpen(false); }}
                        >
                          <Badge variant={l.source === "BUY" ? "outline" : "secondary"} className="mr-2 text-[10px]">
                            {l.source === "BUY" ? "Buy" : "Make"}
                          </Badge>
                          <span className="min-w-0 flex-1 truncate">{lineLabel(l)}</span>
                          {l.consumed_at_step_name && (
                            <span className="ml-2 shrink-0 text-xs text-muted-foreground">at {l.consumed_at_step_name}</span>
                          )}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          ) : !isDraft ? (
            <p className="text-xs text-muted-foreground">
              Released BOM (Rev {bom.revision}) is read-only — start a new revision on the Part Type to re-allocate.
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}

export default StepBomSection;
