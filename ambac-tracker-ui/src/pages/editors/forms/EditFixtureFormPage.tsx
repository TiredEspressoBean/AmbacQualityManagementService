"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Check, ChevronsUpDown, X } from "lucide-react";
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
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";
import {
  useRetrieveFixture,
  useCreateFixture,
  useUpdateFixture,
  useProcesses,
  useProcessDetail,
} from "@/hooks/useScheduling";

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

type SelStep = { id: string; label: string };

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

  // Cascading Process → Step picker state.
  const [procOpen, setProcOpen] = useState(false);
  const [stepOpen, setStepOpen] = useState(false);
  const [processId, setProcessId] = useState<string | undefined>();
  const [selected, setSelected] = useState<SelStep[]>([]);

  const { data: processesData } = useProcesses();
  const processes = useMemo(
    () => (((processesData as any)?.results ?? []) as any[]).map((p) => ({ id: String(p.id), name: p.name })),
    [processesData]
  );
  const selectedProcess = processes.find((p) => p.id === processId);
  const { data: processDetail } = useProcessDetail(processId);
  const processSteps = useMemo(
    () =>
      (((processDetail as any)?.process_steps ?? []) as any[])
        .filter((ps) => ps.step)
        .map((ps) => ({ id: String(ps.step.id), name: ps.step.name as string, order: ps.order })),
    [processDetail]
  );

  // RHF `values` reactively syncs the form (incl. controlled Radix Selects) once the
  // fixture loads — a `reset()` effect fails to propagate to the Kind Select on edit.
  const loadedValues = useMemo<FormValues | undefined>(() => {
    if (mode === "edit" && fixture) {
      const f = fixture as any;
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
      const f = fixture as any;
      // Radix Select doesn't reflect an RHF `values`-driven update, so set kind explicitly.
      form.setValue("kind", (f.kind ?? "FIXTURE") as FormValues["kind"], { shouldDirty: false });
      const ids: string[] = (f.steps ?? []).map(String);
      const names: string[] = f.step_names ?? [];
      setSelected(ids.map((id, i) => ({ id, label: names[i] ?? "Step" })));
    }
  }, [mode, fixture, form]);

  const addStep = (s: { id: string; name: string }) => {
    if (selected.some((x) => x.id === s.id)) return;
    const label = selectedProcess ? `${selectedProcess.name} · ${s.name}` : s.name;
    setSelected((xs) => [...xs, { id: s.id, label }]);
  };
  const removeStep = (id: string) => setSelected((xs) => xs.filter((x) => x.id !== id));

  function onSubmit(values: FormValues) {
    const body = {
      name: values.name,
      kind: values.kind,
      quantity: values.quantity,
      lead_time_days: values.lead_time_days ?? null,
      steps: selected.map((s) => s.id),
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
                  <Select
                    // Key by the value so the Select remounts when the value changes — a
                    // controlled Radix Select won't reflect an RHF value set after mount, but
                    // it reads the value correctly on a fresh mount.
                    key={field.value ?? "FIXTURE"}
                    value={field.value ?? "FIXTURE"}
                    onValueChange={field.onChange}
                  >
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
                  <FormDescription>How many exist (concurrency limit).</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
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

          {/* Cascading Process → Step picker: pick a process, then a step within it. */}
          <FormItem>
            <FormLabel>Required at steps</FormLabel>
            <FormDescription>
              Pick a process, then the step within it that needs this resource. Add as many as
              you like — step names repeat across processes, so choosing the process first keeps
              it unambiguous.
            </FormDescription>

            <div className="space-y-3 rounded-md border p-3">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {/* Process combobox */}
              <Popover open={procOpen} onOpenChange={setProcOpen}>
                <PopoverTrigger asChild>
                  <Button variant="outline" role="combobox" className="justify-between">
                    {selectedProcess ? selectedProcess.name : "Select a process…"}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                  <Command>
                    <CommandInput placeholder="Search processes…" />
                    <CommandList>
                      <CommandEmpty>No processes found.</CommandEmpty>
                      <CommandGroup>
                        {processes.map((p) => (
                          <CommandItem
                            key={p.id}
                            value={p.name}
                            onSelect={() => { setProcessId(p.id); setProcOpen(false); }}
                          >
                            <Check className={cn("mr-2 h-4 w-4", p.id === processId ? "opacity-100" : "opacity-0")} />
                            {p.name}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>

              {/* Step combobox (steps of the chosen process) */}
              <Popover open={stepOpen} onOpenChange={setStepOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    className="justify-between"
                    disabled={!processId}
                  >
                    {processId ? "Add a step…" : "Pick a process first"}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                  <Command>
                    <CommandInput placeholder="Search steps…" />
                    <CommandList>
                      <CommandEmpty>No steps in this process.</CommandEmpty>
                      <CommandGroup>
                        {processSteps.map((s) => (
                          <CommandItem
                            key={s.id}
                            value={s.name}
                            onSelect={() => { addStep(s); setStepOpen(false); }}
                          >
                            <Check
                              className={cn("mr-2 h-4 w-4", selected.some((x) => x.id === s.id) ? "opacity-100" : "opacity-0")}
                            />
                            {s.order}. {s.name}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>

            {selected.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {selected.map((s) => (
                  <Badge key={s.id} variant="secondary" className="gap-1">
                    {s.label}
                    <button type="button" onClick={() => removeStep(s.id)} className="ml-0.5 rounded hover:text-destructive">
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                No steps selected — this resource won't constrain the schedule until you add some.
              </p>
            )}
            </div>
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
    </div>
  );
}
