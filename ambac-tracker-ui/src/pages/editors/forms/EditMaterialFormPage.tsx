"use client";

import { Combobox } from "@/components/ui/combobox";
import { RecordHistoryCard } from "@/components/data-management/RecordHistoryCard";
import { RecordArchiveCard } from "@/components/data-management/RecordArchiveCard";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useParams, useNavigate } from "@tanstack/react-router";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";
import {
  useRetrieveMaterial,
  useCreateMaterial,
  useUpdateMaterial,
} from "@/hooks/useMaterials";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import type { Schema } from "@/lib/api/types";
import {
    DEFAULT_RECEIVING_CONTROLS, ReceivingControlsFields, receivingControlsOf, type ReceivingControls,
} from "@/components/receiving/ReceivingControlsFields";

const formSchema = schemas.MaterialRequest.pick({
  name: true,
  part_number: true,
  description: true,
  unit_of_measure: true,
  purchase_lead_time_days: true,
  safety_stock: true,
  is_active: true,
});
type FormValues = z.infer<typeof formSchema>;

const required = {
  name: isFieldRequired(formSchema.shape.name),
};

export default function EditMaterialFormPage() {
  const params = useParams({ strict: false });
  const navigate = useNavigate();
  const mode = params.id ? "edit" : "create";
  const materialId = params.id;

  const { data: material, isLoading, isError } = useRetrieveMaterial(
    mode === "edit" ? materialId : undefined
  );
  const create = useCreateMaterial();
  const update = useUpdateMaterial();

  // Preferred-supplier combobox (nullable FK) — kept out of RHF like the fixture form.
  const [supplierId, setSupplierId] = useState<string | null>(null);
  // Receiving controls (buying unit, CoC / heat-number holds) — also kept out of RHF.
  const [receiving, setReceiving] = useState<ReceivingControls>(DEFAULT_RECEIVING_CONTROLS);
  const { data: companiesData } = useRetrieveCompanies({ limit: 500, ordering: "name" });
  const suppliers = useMemo(
    () => (companiesData?.results ?? []).map((c) => ({ id: String(c.id), name: c.name })),
    [companiesData]
  );

  const loadedValues = useMemo<FormValues | undefined>(() => {
    if (mode === "edit" && material) {
      const m = material as Schema<"Material">;
      return {
        name: m.name ?? "",
        part_number: m.part_number ?? "",
        description: m.description ?? "",
        unit_of_measure: m.unit_of_measure ?? "EA",
        purchase_lead_time_days: m.purchase_lead_time_days ?? null,
        safety_stock: m.safety_stock ?? null,
        is_active: m.is_active ?? true,
      };
    }
    return undefined;
  }, [mode, material]);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      part_number: "",
      description: "",
      unit_of_measure: "EA",
      purchase_lead_time_days: null,
      safety_stock: null,
      is_active: true,
    },
    values: loadedValues,
  });

  useEffect(() => {
    if (mode === "edit" && material) {
      const m = material as Schema<"Material">;
      setSupplierId(m.preferred_supplier != null ? String(m.preferred_supplier) : null);
      setReceiving(receivingControlsOf(m));
    }
  }, [mode, material]);

  function onSubmit(values: FormValues) {
    const body = {
      ...values,
      preferred_supplier: supplierId,
      ...receiving,
    };
    const done = () => navigate({ to: "/editor/materials" });
    if (mode === "edit" && materialId) {
      update.mutate({ id: materialId, ...body }, {
        onSuccess: () => { toast.success("Material updated"); done(); },
        onError: () => toast.error("Failed to update material"),
      });
    } else {
      create.mutate(body, {
        onSuccess: () => { toast.success("Material created"); done(); },
        onError: () => toast.error("Failed to create material"),
      });
    }
  }

  if (mode === "edit" && isLoading) {
    return <div className="max-w-2xl p-6"><div className="h-40 animate-pulse rounded bg-muted" /></div>;
  }

  if (mode === "edit" && isError) {
    return (
      <div className="mx-auto max-w-2xl py-10 text-center">
        <h1 className="text-2xl font-semibold">Material not found</h1>
        <p className="mt-2 text-muted-foreground">
          This material doesn't exist — it may have been deleted.
        </p>
        <Button className="mt-4" onClick={() => navigate({ to: "/editor/materials" })}>
          Back to Materials
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">{mode === "edit" ? "Edit Material" : "New Material"}</h1>
        <p className="text-muted-foreground">
          A purchased component (O-ring, seal, coil, fastener). Its lead time drives the
          sourcing report's order-by dates; BOM lines that <em>buy</em> a component point here.
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required={required.name}>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. Seal & O-Ring Kit" {...field} value={field.value ?? ""} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="part_number"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Part number</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g. CRI-SEAL" {...field} value={field.value ?? ""} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="unit_of_measure"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Unit of measure</FormLabel>
                      <FormControl>
                        <Input placeholder="EA" {...field} value={field.value ?? ""} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="purchase_lead_time_days"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Purchase lead time (days)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={0}
                        placeholder="e.g. 14"
                        {...field}
                        value={field.value ?? ""}
                        onChange={(e) =>
                          field.onChange(e.target.value === "" ? null : parseInt(e.target.value))
                        }
                      />
                    </FormControl>
                    <FormDescription>
                      Days from PO to on-dock. Drives the sourcing report's order-by date.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="safety_stock"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Safety stock</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={0}
                        step="any"
                        placeholder="None"
                        {...field}
                        value={field.value ?? ""}
                        onChange={(e) => field.onChange(e.target.value === "" ? null : e.target.value)}
                      />
                    </FormControl>
                    <FormDescription>
                      Held back from planning: the requirements report nets demand against stock
                      above this, and flags a shortage before it's reached.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Preferred supplier combobox (optional) */}
              <FormItem>
                <FormLabel>Preferred supplier</FormLabel>
                <Combobox
                  value={supplierId}
                  onChange={setSupplierId}
                  options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
                  clearLabel="None"
                  placeholder="None"
                  searchPlaceholder="Search suppliers…"
                  emptyText="No companies found."
                />
                <FormDescription>Where this is normally bought (optional).</FormDescription>
              </FormItem>

              <ReceivingControlsFields value={receiving} onChange={setReceiving}
                stockUnit={form.watch("unit_of_measure") || "EA"} />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea rows={2} {...field} value={field.value ?? ""} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex items-center justify-between rounded-md border p-3">
                    <div>
                      <FormLabel>Active</FormLabel>
                      <FormDescription>Inactive materials are hidden from pickers.</FormDescription>
                    </div>
                    <FormControl>
                      <Switch checked={field.value ?? true} onCheckedChange={field.onChange} />
                    </FormControl>
                  </FormItem>
                )}
              />

              <div className="flex gap-3">
                <Button type="submit" disabled={create.isPending || update.isPending} className="flex-1">
                  {mode === "edit"
                    ? update.isPending ? "Saving…" : "Save Changes"
                    : create.isPending ? "Creating…" : "Create Material"}
                </Button>
                <Button type="button" variant="outline" onClick={() => navigate({ to: "/editor/materials" })}>
                  Cancel
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
        {mode === "edit" && materialId && (
            <div className="max-w-3xl mx-auto py-6">
                <div className="space-y-6"><RecordHistoryCard endpoint="Materials" id={materialId} model="material" /><RecordArchiveCard endpoint="Materials" id={materialId} model="material" /></div>
            </div>
        )}
    </div>
  );
}
