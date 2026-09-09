"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { cn } from "@/lib/utils";
import { useMaterialOptions } from "@/hooks/useMaterials";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { useCreateBomLine, useUpdateBomLine } from "@/hooks/useBom";

type Source = "MAKE" | "BUY";

/** A BOM line, as returned nested on the BOM detail. */
export type BomLine = {
  id: string | number;
  source?: string | null;
  component_type?: string | number | null;
  material?: string | number | null;
  quantity?: number | string | null;
  unit_of_measure?: string | null;
  find_number?: string | null;
  reference_designator?: string | null;
  is_optional?: boolean | null;
  consumed_at_step?: string | number | null;
};

const NO_STEP = "__none__";

export function BomLineDialog({
  open,
  onOpenChange,
  bomId,
  line,
  steps,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  bomId: string;
  /** null → create a new line; otherwise edit this one. */
  line: BomLine | null;
  /** The assembly's process steps — the ops a line can be consumed at. */
  steps: { id: string; name: string }[];
}) {
  const isEdit = !!line;
  const create = useCreateBomLine();
  const update = useUpdateBomLine();

  const [source, setSource] = useState<Source>("BUY");
  const [componentId, setComponentId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [uom, setUom] = useState("EA");
  const [findNumber, setFindNumber] = useState("");
  const [refDes, setRefDes] = useState("");
  const [optional, setOptional] = useState(false);
  const [consumedStepId, setConsumedStepId] = useState<string>(NO_STEP);
  const [pickerOpen, setPickerOpen] = useState(false);

  // Hydrate on open (create → defaults; edit → the line's values).
  useEffect(() => {
    if (!open) return;
    if (line) {
      const src = (line.source as Source) ?? (line.material != null ? "BUY" : "MAKE");
      setSource(src);
      // Which column the line carries is independent of MAKE/BUY — a BUY line can point
      // at either — so read the component off whichever is set, not off the source.
      setComponentId(
        line.material != null
          ? `MATERIAL:${line.material}`
          : line.component_type != null
            ? `PART_TYPE:${line.component_type}`
            : null
      );
      setQuantity(String(line.quantity ?? "1"));
      setUom(line.unit_of_measure ?? "EA");
      setFindNumber(line.find_number ?? "");
      setRefDes(line.reference_designator ?? "");
      setOptional(!!line.is_optional);
      setConsumedStepId(line.consumed_at_step != null ? String(line.consumed_at_step) : NO_STEP);
    } else {
      setSource("BUY");
      setComponentId(null);
      setQuantity("1");
      setUom("EA");
      setFindNumber("");
      setRefDes("");
      setOptional(false);
      setConsumedStepId(NO_STEP);
    }
  }, [open, line]);

  const { data: materialsData } = useMaterialOptions();
  const { data: partTypesData } = useRetrievePartTypes({ limit: 500 } as never);

  const options = useMemo(() => {
    // A component lives in one of two tables, so the picker's value carries which one
    // ("PART_TYPE:<id>" / "MATERIAL:<id>") rather than a bare id.
    //
    // MAKE is always a part type. BUY is *both*: a raw material (seals, adhesives —
    // never made here) or a part we're sourcing outside this time. That second case is
    // the one worth offering, because only a part type carries a receiving-inspection
    // plan, supplier qualification and part approval — buying a part as a "material"
    // is what sends it to stock with no quality gate.
    if (source === "MAKE") {
      return (partTypesData?.results ?? [])
        .filter((r) => r.name)
        .map((r) => ({ key: `PART_TYPE:${r.id}`, name: r.name as string, hint: "" }));
    }
    const materials = (materialsData?.results ?? [])
      .filter((r) => r.name)
      .map((r) => ({ key: `MATERIAL:${r.id}`, name: r.name as string, hint: "Material" }));
    const boughtParts = (partTypesData?.results ?? [])
      .filter((r) => r.name && (r as { can_buy?: boolean }).can_buy)
      .map((r) => ({ key: `PART_TYPE:${r.id}`, name: r.name as string, hint: "Part" }));
    return [...materials, ...boughtParts];
  }, [source, materialsData, partTypesData]);

  const selected = options.find((o) => o.key === componentId);

  // Switching Make/Buy clears the component (the eligible set changes).
  function pickSource(s: Source) {
    setSource(s);
    setComponentId(null);
  }

  function onSubmit() {
    const [kind, id] = (componentId ?? "").split(":");
    const body: Record<string, unknown> = {
      bom: bomId,
      source,
      component_type: kind === "PART_TYPE" ? id : null,
      material: kind === "MATERIAL" ? id : null,
      // A string, not a number: quantity is a DecimalField, so the generated client
      // types it as a string and rejects a numeric body before it ever leaves the
      // browser. Sending a number silently failed every save this dialog attempted.
      quantity: String(Number(quantity) || 0),
      unit_of_measure: uom,
      find_number: findNumber,
      reference_designator: refDes,
      is_optional: optional,
      consumed_at_step: consumedStepId === NO_STEP ? null : consumedStepId,
    };
    const done = () => onOpenChange(false);
    if (isEdit && line) {
      update.mutate({ id: String(line.id), ...body }, { onSuccess: done });
    } else {
      create.mutate(body, { onSuccess: done });
    }
  }

  const saving = create.isPending || update.isPending;
  const canSave = !!componentId && Number(quantity) > 0 && !saving;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit BOM line" : "Add BOM line"}</DialogTitle>
          <DialogDescription>
            A line is a component you <strong>make</strong> in-house, or one you{" "}
            <strong>buy</strong> &mdash; either a raw material or a part flagged as
            purchasable.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Source toggle */}
          <div className="grid gap-1.5">
            <Label>Source</Label>
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant={source === "MAKE" ? "default" : "outline"}
                onClick={() => pickSource("MAKE")}
              >
                Make (Part Type)
              </Button>
              <Button
                type="button"
                variant={source === "BUY" ? "default" : "outline"}
                onClick={() => pickSource("BUY")}
              >
                Buy
              </Button>
            </div>
          </div>

          {/* Component picker (list depends on source) */}
          <div className="grid gap-1.5">
            <Label>{source === "BUY" ? "Purchased component" : "Part Type"}</Label>
            <Popover open={pickerOpen} onOpenChange={setPickerOpen}>
              <PopoverTrigger asChild>
                <Button variant="outline" role="combobox" className="justify-between">
                  {selected ? selected.name : `Select a ${source === "BUY" ? "component to buy" : "part type"}…`}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                <Command>
                  <CommandInput placeholder="Search…" />
                  <CommandList>
                    <CommandEmpty>Nothing found.</CommandEmpty>
                    <CommandGroup>
                      {options.map((o) => (
                        <CommandItem
                          key={o.key}
                          value={o.name}
                          onSelect={() => { setComponentId(o.key); setPickerOpen(false); }}
                        >
                          <Check className={cn("mr-2 h-4 w-4", o.key === componentId ? "opacity-100" : "opacity-0")} />
                          <span className="flex-1">{o.name}</span>
                          {o.hint && (
                            <span className="ml-2 text-xs text-muted-foreground">{o.hint}</span>
                          )}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="grid gap-1.5">
              <Label>Quantity</Label>
              <Input
                type="number"
                min={0}
                step="any"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
            </div>
            <div className="grid gap-1.5">
              <Label>UoM</Label>
              <Input value={uom} onChange={(e) => setUom(e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label>Find #</Label>
              <Input value={findNumber} onChange={(e) => setFindNumber(e.target.value)} />
            </div>
          </div>

          <div className="grid gap-1.5">
            <Label>Reference designator</Label>
            <Input value={refDes} onChange={(e) => setRefDes(e.target.value)} placeholder="optional" />
          </div>

          {/* Component allocation: the operation that consumes this line. When set, the
              scheduler gates only that step on the component; when unset, the whole
              parent waits. Feeds the sourcing report's need-by date. */}
          <div className="grid gap-1.5">
            <Label>Consumed at step</Label>
            <Select value={consumedStepId} onValueChange={setConsumedStepId}>
              <SelectTrigger>
                <SelectValue placeholder="Whole assembly (no specific step)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_STEP}>Whole assembly (no specific step)</SelectItem>
                {steps.map((s) => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={optional} onCheckedChange={(v) => setOptional(!!v)} />
            Optional line
          </label>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={onSubmit} disabled={!canSave}>
            {saving ? "Saving…" : isEdit ? "Save line" : "Add line"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default BomLineDialog;
