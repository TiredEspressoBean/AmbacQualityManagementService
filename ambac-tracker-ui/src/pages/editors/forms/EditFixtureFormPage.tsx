"use client";

import { RecordHistoryCard } from "@/components/data-management/RecordHistoryCard";
import { RecordArchiveCard } from "@/components/data-management/RecordArchiveCard";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useParams, useNavigate } from "@tanstack/react-router";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";
import {
  useRetrieveFixture,
  useCreateFixture,
  useUpdateFixture,
} from "@/hooks/useScheduling";
import { useRetrieveEquipmentTypes } from "@/hooks/useRetrieveEquipmentTypes";

const KIND_OPTIONS = [
  { value: "FIXTURE", label: "Fixture" },
  { value: "TOOL", label: "Cutting tool" },
  { value: "DIE", label: "Die / mold" },
  { value: "PROGRAM", label: "NC program" },
  { value: "OTHER", label: "Other" },
];

const formSchema = schemas.FixtureRequest.pick({
  name: true, kind: true, quantity: true, lead_time_days: true,
});
type FormValues = z.infer<typeof formSchema>;

const required = {
  name: isFieldRequired(formSchema.shape.name),
  quantity: isFieldRequired(formSchema.shape.quantity),
};

export default function EditFixtureFormPage() {
  const params = useParams({ strict: false });
  const navigate = useNavigate();
  const mode = params.id ? "edit" : "create";
  const fixtureId = params.id;

  const { data: fixture, isLoading, isError } = useRetrieveFixture(
    mode === "edit" ? fixtureId : undefined
  );
  const create = useCreateFixture();
  const update = useUpdateFixture();

  // Tracked tooling: with an equipment type, capacity is that type's items in service
  // and within life, and the typed quantity isn't used.
  const [equipmentType, setEquipmentType] = useState<string>("none");
  const { data: typesResp } = useRetrieveEquipmentTypes({ limit: 500 });
  const equipmentTypes = typesResp?.results ?? [];

  // RHF `values` reactively syncs the form (incl. controlled Radix Selects) once the
  // fixture loads — a `reset()` effect fails to propagate to the Kind Select on edit.
  const loadedValues = useMemo<FormValues | undefined>(() => {
    if (mode === "edit" && fixture) {
      const f = fixture;
      return {
        name: f.name ?? "", kind: f.kind ?? "FIXTURE", quantity: f.quantity ?? 1,
        lead_time_days: f.lead_time_days ?? null,
      };
    }
    return undefined;
  }, [mode, fixture]);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { name: "", kind: "FIXTURE", quantity: 1, lead_time_days: null },
    values: loadedValues,
  });

  useEffect(() => {
    if (mode === "edit" && fixture) {
      const f = fixture;
      setEquipmentType(f.equipment_type ? String(f.equipment_type) : "none");
    }
  }, [mode, fixture, form]);

  function onSubmit(values: FormValues) {
    const chosenType = equipmentType === "none" ? null : equipmentType;
    // An edit sends the tracked type only when the user changed it, so a picker that
    // failed to show the saved type can never clear it (P3 walk, 2026-11-12).
    const savedType = fixture?.equipment_type ? String(fixture.equipment_type) : null;
    const typeChanged = mode !== "edit" || chosenType !== savedType;
    const body = {
      name: values.name,
      kind: values.kind,
      quantity: values.quantity,
      lead_time_days: values.lead_time_days ?? null,
      ...(typeChanged ? { equipment_type: chosenType } : {}),
    };
    const done = () => navigate({ to: "/editor/tooling" });
    if (mode === "edit" && fixtureId) {
      update.mutate({ id: fixtureId, ...body }, {
        onSuccess: () => { toast.success("Resource updated"); done(); },
        onError: () => toast.error("Failed to update resource"),
      });
    } else {
      create.mutate(body, {
        onSuccess: () => { toast.success("Resource created"); done(); },
        onError: () => toast.error("Failed to create resource"),
      });
    }
  }

  if (mode === "edit" && isLoading) {
    return <div className="max-w-2xl p-6"><div className="h-40 animate-pulse rounded bg-muted" /></div>;
  }

  if (mode === "edit" && isError) {
    return (
      <div className="mx-auto max-w-2xl py-10 text-center">
        <h1 className="text-2xl font-semibold">Resource not found</h1>
        <p className="mt-2 text-muted-foreground">
          This tooling resource doesn't exist — it may have been deleted.
        </p>
        <Button className="mt-4" onClick={() => navigate({ to: "/editor/tooling" })}>
          Back to Tooling
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">{mode === "edit" ? "Edit Resource" : "New Tooling Resource"}</h1>
        <p className="text-muted-foreground">
          A shared, quantity-limited resource (fixture / cutting tool / die / NC program). The
          scheduler serializes the operations that require it against the quantity available.
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
                  <Input placeholder="e.g. Broach #3, Fixture Plate A" {...field} value={field.value ?? ""} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <FormField
              control={form.control}
              name="kind"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Kind</FormLabel>
                  <Select value={field.value ?? "FIXTURE"} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger className="w-full"><SelectValue placeholder="Select kind" /></SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {KIND_OPTIONS.map((k) => (
                        <SelectItem key={k.value} value={k.value}>{k.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="quantity"
              render={({ field }) => (
                <FormItem>
                  <FormLabel required={required.quantity}>Quantity</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      {...field}
                      value={field.value ?? 1}
                      onChange={(e) => field.onChange(parseInt(e.target.value) || 1)}
                    />
                  </FormControl>
                  <FormDescription>
                    {equipmentType === "none"
                      ? "How many exist (concurrency limit)."
                      : "Not used: the tracked items below decide how many are available."}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="fixture-eqtype">Tracked as equipment</Label>
            <Select value={equipmentType} onValueChange={setEquipmentType}>
              {/* The label is given, not looked up from the items: the saved type was set
                  before the type list loaded and the trigger rendered blank. */}
              <SelectTrigger id="fixture-eqtype" className="w-full">
                <SelectValue>
                  {equipmentType === "none"
                    ? "Not tracked — use the quantity"
                    : (equipmentTypes.find((t) => String(t.id) === equipmentType)?.name
                       ?? "Loading…")}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Not tracked — use the quantity</SelectItem>
                {equipmentTypes.map((t) => (
                  <SelectItem key={t.id} value={String(t.id)}>{t.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              {equipmentType === "none"
                ? "For tooling recorded item by item (each die, each fixture), pick its equipment type: the scheduler then counts those in service and within their life."
                : `Available now: ${fixture?.capacity ?? "—"} in service and within life.`}
            </p>
          </div>

          <FormField
            control={form.control}
            name="lead_time_days"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Procurement lead time (days)</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min={0}
                    placeholder="e.g. 30"
                    {...field}
                    value={field.value ?? ""}
                    onChange={(e) =>
                      field.onChange(e.target.value === "" ? null : parseInt(e.target.value))
                    }
                  />
                </FormControl>
                <FormDescription>
                  Days to procure/build this resource. Drives the sourcing report's order-by date
                  for tooling not yet on hand (quantity 0).
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* The steps that need it are authored on the step ("Tooling this step needs",
              in the process flow editor), under change control (10b): shown here only. */}
          <FormItem>
            <FormLabel>Required at</FormLabel>
            {(fixture?.step_names ?? []).length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {(fixture?.step_names ?? []).map((name, i) => (
                  <Badge key={`${name}-${i}`} variant="secondary">{name}</Badge>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                No step needs it yet.
              </p>
            )}
            <FormDescription>
              A step says which tooling it needs, in the process flow editor ("Tooling this step
              needs"), as part of the process — so a change goes through a process change.
            </FormDescription>
          </FormItem>

          <div className="flex gap-3">
            <Button type="submit" disabled={create.isPending || update.isPending} className="flex-1">
              {mode === "edit"
                ? update.isPending ? "Saving…" : "Save Changes"
                : create.isPending ? "Creating…" : "Create Resource"}
            </Button>
            <Button type="button" variant="outline" onClick={() => navigate({ to: "/editor/tooling" })}>
              Cancel
            </Button>
          </div>
        </form>
      </Form>
        </CardContent>
      </Card>
        {mode === "edit" && fixtureId && (
            <div className="max-w-3xl mx-auto py-6">
                <div className="space-y-6"><RecordHistoryCard endpoint="Fixtures" id={fixtureId} model="fixture" /><RecordArchiveCard endpoint="Fixtures" id={fixtureId} model="fixture" /></div>
            </div>
        )}
    </div>
  );
}
