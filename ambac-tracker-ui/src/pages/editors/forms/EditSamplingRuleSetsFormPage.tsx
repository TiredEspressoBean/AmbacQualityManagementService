"use client"

import { useCreateSamplingRuleSet } from "@/hooks/useCreateSamplingRuleSet"
import { useUpdateSamplingRuleSet } from "@/hooks/useUpdateSamplingRuleSet"
import { useRetrieveSamplingRuleSet } from "@/hooks/useRetrieveSamplingRuleSet"
import { useParams, useNavigate } from "@tanstack/react-router"
import { SamplingRuleRowsEditor } from "@/components/sampling/SamplingRuleRowsEditor"

import {useEffect, useState} from "react"
import { toast } from "sonner"
import { useForm, type Resolver } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
    Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies"
import {
    Popover, PopoverContent, PopoverTrigger,
} from "@/components/ui/popover"
import {
    Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command"
import { Check, ChevronsUpDown } from "lucide-react"

import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes"
import { useRetrieveProcesses } from "@/hooks/useRetrieveProcesses"
import { useRetrieveSteps } from "@/hooks/useRetrieveSteps"
import { useRetrieveApprovalTemplates } from "@/hooks/useRetrieveApprovalTemplates"
import { schemas } from "@/lib/api/generated"
import { isFieldRequired } from "@/lib/zod-config"

// Use generated schema, extending process to be required for this form
const formSchema = schemas.SamplingRuleSetRequest.pick({
    name: true,
    active: true,
    part_type: true,
    step: true,
    supplier: true,
    aql: true,
    inspection_level: true,
    severity: true,
    strategy: true,
    gate_metric: true,
    gate_threshold: true,
    gate_window: true,
    gate_window_n: true,
    gate_min_sample: true,
    gate_capa_type: true,
    gate_capa_severity: true,
    gate_approval_template: true,
}).extend({
    // Process is optional in API but required for this form
    process: z.string().min(1),
    // gate_actions is a JSON list in the API (unknown); constrain to string codes.
    gate_actions: z.array(z.string()).optional(),
})

const NONE = "__none__"

// Standard AQL series (Z1.4 / ISO 2859-1) — off-series values have no table row.
const AQL_SERIES = ["0.010", "0.015", "0.025", "0.040", "0.065", "0.10", "0.15",
    "0.25", "0.40", "0.65", "1.0", "1.5", "2.5", "4.0", "6.5", "10"]

// Gate actions are side-effects only. Routing (scrap/quarantine/rework/next) is the
// step's edges + decision type; tightening is the escalation/severity layer. So the
// gate triggers only a parallel record or a signoff.
const GATE_ACTIONS = [
    { value: "RAISE_CAPA_SCAR", label: "Raise CAPA / SCAR" },
    { value: "REQUIRE_APPROVAL", label: "Require approval" },
]

type FormValues = z.infer<typeof formSchema>;

const required = {
    name: isFieldRequired(formSchema.shape.name),
    part_type: isFieldRequired(formSchema.shape.part_type),
    process: isFieldRequired(formSchema.shape.process),
    step: isFieldRequired(formSchema.shape.step),
};

export default function SamplingRuleSetsFormPage() {
    const [partTypeSearch, setPartTypeSearch] = useState("")
    const [processSearch, setProcessSearch] = useState("")
    const [stepSearch, setStepSearch] = useState("")
    const [selectedPartTypeId, setSelectedPartTypeId] = useState<string | null>(null)
    const [selectedProcessId, setSelectedProcessId] = useState<string | null>(null)

    const { data: partTypes } = useRetrievePartTypes({ search: partTypeSearch })
    const { data: companies } = useRetrieveCompanies({ limit: 200 } as never)
    const { data: approvalTemplates } = useRetrieveApprovalTemplates({ limit: 200 } as never)
    const { data: processes } = useRetrieveProcesses({
        search: processSearch,
        ...(selectedPartTypeId !== null ? { part_type: selectedPartTypeId } : {}),
    })
    // Steps filter: use process_memberships__process (junction table) and part_type
    const { data: steps } = useRetrieveSteps({
        search: stepSearch,
        ...(selectedProcessId !== null ? { process_memberships__process: selectedProcessId } : {}),
        ...(selectedPartTypeId !== null ? { part_type: selectedPartTypeId } : {}),
    })

    const params = useParams({ strict: false })
    const navigate = useNavigate()
    const mode = params.id ? "edit" : "create"
    const ruleSetId = params.id

    const { data: ruleSet } = useRetrieveSamplingRuleSet(
        { params: { id: ruleSetId! } },
        { enabled: mode === "edit" && !!ruleSetId }
    )

    const createRuleSet = useCreateSamplingRuleSet()
    const updateRuleSet = useUpdateSamplingRuleSet()

    const form = useForm<FormValues, any, FormValues>({
        resolver: zodResolver(formSchema) as Resolver<FormValues, any, FormValues>,
    })

    // Sampling family — UI-only discriminator (no backend column yet). Streaming =
    // per-part rules; Lot acceptance = AQL/C=0 plan. Inferred from the ruleset's data.
    const [family, setFamily] = useState<"STREAMING" | "LOT_ACCEPTANCE">("STREAMING")

    useEffect(() => {
        if (mode === "edit" && ruleSet) {
            const isLot = !!(ruleSet.strategy || ruleSet.aql)
            setFamily(isLot ? "LOT_ACCEPTANCE" : "STREAMING")
            form.reset({
                name: ruleSet.name ?? "",
                active: ruleSet.active ?? true,
                part_type: ruleSet.part_type,
                process: ruleSet.process ?? "",
                step: ruleSet.step,
                supplier: ruleSet.supplier ?? null,
                aql: ruleSet.aql ?? null,
                inspection_level: ruleSet.inspection_level ?? "",
                severity: ruleSet.severity ?? "",
                strategy: ruleSet.strategy ?? "",
                gate_metric: ruleSet.gate_metric ?? "",
                gate_threshold: ruleSet.gate_threshold ?? null,
                gate_window: ruleSet.gate_window ?? "",
                gate_window_n: ruleSet.gate_window_n ?? null,
                gate_min_sample: ruleSet.gate_min_sample ?? null,
                gate_actions: (ruleSet.gate_actions as string[] | undefined) ?? [],
                gate_capa_type: ruleSet.gate_capa_type ?? "",
                gate_capa_severity: ruleSet.gate_capa_severity ?? "",
                gate_approval_template: ruleSet.gate_approval_template ?? null,
            } as FormValues)
            setSelectedPartTypeId(ruleSet.part_type)
            setSelectedProcessId(ruleSet.process ?? null)
        }
    }, [mode, ruleSet, form])

    async function onSubmit(values: FormValues) {
        try {
            if (mode === "edit" && ruleSetId) {
                await updateRuleSet.mutateAsync({ id: ruleSetId, data: values } as never)
                toast.success("Rule set updated")
            } else {
                const created = await createRuleSet.mutateAsync(values as never)
                toast.success("Rule set created — add sampling rules below")
                const newId = (created as { id?: string })?.id
                if (newId) navigate({ to: "/SamplingRuleSetForm/edit/$id", params: { id: newId } })
                else form.reset()
            }
        } catch (error) {
            console.error("Form submission error", error)
            toast.error("Failed to submit the form. Please try again.")
        }
    }

    return (
        <Form {...form}>
            <div className="max-w-3xl mx-auto py-6">
                <h1 className="text-2xl font-semibold tracking-tight">
                    {mode === "edit" ? "Edit Rule Set" : "Create New Rule Set"}
                </h1>
                <p className="text-muted-foreground text-sm mt-1">
                    {mode === "edit" ? `Update details for Part #${ruleSetId ?? ""}` : "Fill out the details below to create a new part."}
                </p>
            </div>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8 max-w-3xl mx-auto py-10">
                <FormField
                    control={form.control}
                    name="name"
                    render={({field}) => (
                        <FormItem>
                            <FormLabel required={required.name}>Name</FormLabel>
                            <FormControl>
                                <Input placeholder="Sampling rule set name" {...field} />
                            </FormControl>
                            <FormDescription>Name of this rule set for organization</FormDescription>
                            <FormMessage/>
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="active"
                    render={({field}) => (
                        <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                            <FormControl>
                                <Checkbox
                                    checked={field.value ?? false}
                                    onCheckedChange={field.onChange}
                                />
                            </FormControl>
                            <div className="space-y-1 leading-none">
                                <FormLabel>Active</FormLabel>
                                <FormDescription>Whether this rule set is still in use</FormDescription>
                            </div>
                            <FormMessage/>
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="part_type"
                    render={({field}) => {
                        const selected = partTypes?.results.find(pt => pt.id === field.value)
                        return (
                            <FormItem className="flex flex-col">
                                <FormLabel required={required.part_type}>Part Type</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button variant="outline" role="combobox"
                                                    className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}>
                                                {selected?.name ?? "Select a part type"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-[300px] p-0">
                                        <Command>
                                            <CommandInput value={partTypeSearch} onValueChange={setPartTypeSearch}
                                                          placeholder="Search part types..."/>
                                            <CommandList>
                                                <CommandEmpty>No part types found.</CommandEmpty>
                                                <CommandGroup>
                                                    {partTypes?.results.map((pt) => (
                                                        <CommandItem
                                                            key={pt.id}
                                                            value={`${pt.name}__${pt.id}`}
                                                            onSelect={() => {
                                                                form.setValue("part_type", pt.id)
                                                                form.setValue("process", "")
                                                                form.setValue("step", "")
                                                                setSelectedPartTypeId(pt.id)
                                                                setSelectedProcessId(null)
                                                                setPartTypeSearch("")
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn("mr-2 h-4 w-4", pt.id === field.value ? "opacity-100" : "opacity-0")}/>
                                                            {pt.name}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>Choose the part type this rule set is for</FormDescription>
                                <FormMessage/>
                            </FormItem>
                        )
                    }}
                />

                <FormField
                    control={form.control}
                    name="process"
                    render={({field}) => {
                        const selected = processes?.results.find(p => p.id === field.value)
                        return (
                            <FormItem className="flex flex-col">
                                <FormLabel required={required.process}>Process</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button variant="outline" role="combobox"
                                                    className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}>
                                                {selected?.name ?? "Select a process"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-[300px] p-0">
                                        <Command>
                                            <CommandInput value={processSearch} onValueChange={setProcessSearch}
                                                          placeholder="Search processes..."/>
                                            <CommandList>
                                                <CommandEmpty>No processes found.</CommandEmpty>
                                                <CommandGroup>
                                                    {processes?.results.map((p) => (
                                                        <CommandItem
                                                            key={p.id}
                                                            value={`${p.name}__${p.id}`}
                                                            onSelect={() => {
                                                                form.setValue("process", p.id)
                                                                form.setValue("step", "")
                                                                setSelectedProcessId(p.id)
                                                                setProcessSearch("")
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn("mr-2 h-4 w-4", p.id === field.value ? "opacity-100" : "opacity-0")}/>
                                                            {p.name}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>Choose the process this rule set is related to</FormDescription>
                                <FormMessage/>
                            </FormItem>
                        )
                    }}
                />

                <FormField
                    control={form.control}
                    name="step"
                    render={({field}) => {
                        const selected = steps?.results.find(s => s.id === field.value)
                        return (
                            <FormItem className="flex flex-col">
                                <FormLabel required={required.step}>Step</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button variant="outline" role="combobox"
                                                    className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}>
                                                {selected?.name ?? "Select a step"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-[300px] p-0">
                                        <Command>
                                            <CommandInput value={stepSearch} onValueChange={setStepSearch}
                                                          placeholder="Search steps..."/>
                                            <CommandList>
                                                <CommandEmpty>No steps found.</CommandEmpty>
                                                <CommandGroup>
                                                    {steps?.results.map((s) => (
                                                        <CommandItem
                                                            key={s.id}
                                                            value={`${s.name}__${s.id}`}
                                                            onSelect={() => {
                                                                form.setValue("step", s.id)
                                                                setStepSearch("")
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn("mr-2 h-4 w-4", s.id === field.value ? "opacity-100" : "opacity-0")}/>
                                                            {s.name}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>Select the step this rule set applies to</FormDescription>
                                <FormMessage/>
                            </FormItem>
                        )
                    }}
                />

                <div className="rounded-md border p-4 space-y-2">
                    <div className="text-sm font-medium">Sampling method</div>
                    <Select value={family} onValueChange={(v) => setFamily(v as "STREAMING" | "LOT_ACCEPTANCE")}>
                        <SelectTrigger className="w-[320px]"><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="STREAMING">Per-part streaming</SelectItem>
                            <SelectItem value="LOT_ACCEPTANCE">Lot acceptance</SelectItem>
                        </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                        {family === "LOT_ACCEPTANCE"
                            ? "Accept or reject a whole lot from a sample (n / Ac / Re). The scheme (C=0 / Z1.4) is set below."
                            : "Select individual parts from the flow to inspect (every-Nth, %, …)."}
                    </p>
                </div>

                {family === "STREAMING" && (
                <div className="rounded-md border p-4 space-y-4">
                    <div>
                        <div className="text-sm font-medium">Sampling rules</div>
                        <p className="text-xs text-muted-foreground">
                            The per-part streaming rules for this set (every-Nth, percentage, first/last-N, …).
                            Changes save immediately.
                        </p>
                    </div>
                    {mode === "edit" && ruleSetId ? (
                        <SamplingRuleRowsEditor rulesetId={ruleSetId} />
                    ) : (
                        <p className="text-sm text-muted-foreground">
                            Save the rule set first — you'll be taken to the edit view to add rules.
                        </p>
                    )}
                </div>
                )}

                {family === "LOT_ACCEPTANCE" && (
                <div className="rounded-md border p-4 space-y-4">
                    <div>
                        <div className="text-sm font-medium">Acceptance plan</div>
                        <p className="text-xs text-muted-foreground">
                            Resolves the incoming lot's sample plan (n / Ac / Re) from lot size + these parameters.
                        </p>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <FormField control={form.control} name="strategy" render={({ field }) => (
                            <FormItem>
                                <FormLabel>Strategy</FormLabel>
                                <Select onValueChange={field.onChange} value={field.value ?? ""}>
                                    <FormControl><SelectTrigger><SelectValue placeholder="—" /></SelectTrigger></FormControl>
                                    <SelectContent>
                                        <SelectItem value="C0">C=0 (Squeglia)</SelectItem>
                                        <SelectItem value="Z14">ANSI/ASQ Z1.4</SelectItem>
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )} />
                        <FormField control={form.control} name="aql" render={({ field }) => (
                            <FormItem>
                                <FormLabel>AQL</FormLabel>
                                <Select onValueChange={(v) => field.onChange(v === NONE ? null : v)} value={(field.value as string | null) || NONE}>
                                    <FormControl><SelectTrigger><SelectValue placeholder="—" /></SelectTrigger></FormControl>
                                    <SelectContent>
                                        <SelectItem value={NONE}>—</SelectItem>
                                        {AQL_SERIES.map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )} />
                        {form.watch("strategy") === "Z14" && (
                            <>
                                <FormField control={form.control} name="inspection_level" render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Inspection level</FormLabel>
                                        <Select onValueChange={field.onChange} value={field.value ?? ""}>
                                            <FormControl><SelectTrigger><SelectValue placeholder="—" /></SelectTrigger></FormControl>
                                            <SelectContent>
                                                <SelectItem value="I">I</SelectItem>
                                                <SelectItem value="II">II</SelectItem>
                                                <SelectItem value="III">III</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )} />
                                <FormField control={form.control} name="severity" render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Severity</FormLabel>
                                        <Select onValueChange={field.onChange} value={field.value ?? ""}>
                                            <FormControl><SelectTrigger><SelectValue placeholder="—" /></SelectTrigger></FormControl>
                                            <SelectContent>
                                                <SelectItem value="NORMAL">Normal</SelectItem>
                                                <SelectItem value="TIGHTENED">Tightened</SelectItem>
                                                <SelectItem value="REDUCED">Reduced</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )} />
                            </>
                        )}
                    </div>
                    <div className="rounded-md border p-3 space-y-1">
                        <div className="text-sm font-medium">Escalation (severity switching)</div>
                        <p className="text-xs text-muted-foreground">
                            {form.watch("strategy") === "Z14"
                                ? "Severity tightens after rejected lots and relaxes after a sustained good run, per Z1.4 switching rules."
                                : "Inspection escalates to 100% after a rejected lot (C=0 convention)."}
                            {" "}Switching is automatic from lot-acceptance history — engine wiring is a pending backend task.
                        </p>
                    </div>
                    <FormField control={form.control} name="supplier" render={({ field }) => (
                        <FormItem>
                            <FormLabel>Supplier</FormLabel>
                            <Select onValueChange={(v) => field.onChange(v === NONE ? null : v)} value={field.value ?? NONE}>
                                <FormControl><SelectTrigger className="w-[300px]"><SelectValue /></SelectTrigger></FormControl>
                                <SelectContent>
                                    <SelectItem value={NONE}>All suppliers</SelectItem>
                                    {companies?.results?.map((c) => (
                                        <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <FormDescription>Scope this plan to one supplier (e.g. tightened for a problem supplier), or leave "All suppliers".</FormDescription>
                            <FormMessage />
                        </FormItem>
                    )} />
                </div>
                )}

                <div className="rounded-md border p-4 space-y-4">
                    <div>
                        <div className="text-sm font-medium">Quality gate (automatic escalation)</div>
                        <p className="text-xs text-muted-foreground">
                            Watch an aggregate signal on this step; when it crosses the threshold, raise a
                            CAPA/SCAR or require approval. Routing (scrap / quarantine / next) is the step's
                            edges + decision type; tightening is the escalation layer — neither is a gate action.
                            Leave the metric blank for no gate.
                        </p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <FormField control={form.control} name="gate_metric" render={({ field }) => (
                            <FormItem>
                                <FormLabel>Metric</FormLabel>
                                <Select value={field.value || NONE} onValueChange={(v) => field.onChange(v === NONE ? "" : v)}>
                                    <FormControl><SelectTrigger><SelectValue placeholder="No gate" /></SelectTrigger></FormControl>
                                    <SelectContent>
                                        <SelectItem value={NONE}>No gate</SelectItem>
                                        <SelectItem value="CONSECUTIVE_FAILS">Consecutive failures</SelectItem>
                                        <SelectItem value="FAIL_RATE_PCT">Failure rate (%)</SelectItem>
                                        <SelectItem value="DEFECTIVE_COUNT">Defective count</SelectItem>
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )} />
                        <FormField control={form.control} name="gate_threshold" render={({ field }) => (
                            <FormItem>
                                <FormLabel>Threshold</FormLabel>
                                <FormControl>
                                    <Input placeholder="e.g. 2 (count) or 50 (%)" {...field} value={field.value ?? ""}
                                        onChange={(e) => field.onChange(e.target.value === "" ? null : e.target.value)} />
                                </FormControl>
                                <FormDescription>Percent for failure-rate; a count otherwise.</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )} />
                    </div>

                    {!!form.watch("gate_metric") && (
                        <>
                            <div className="grid grid-cols-2 gap-4">
                                <FormField control={form.control} name="gate_window" render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Window</FormLabel>
                                        <Select value={field.value || NONE} onValueChange={(v) => field.onChange(v === NONE ? "" : v)}>
                                            <FormControl><SelectTrigger><SelectValue placeholder="—" /></SelectTrigger></FormControl>
                                            <SelectContent>
                                                <SelectItem value={NONE}>—</SelectItem>
                                                <SelectItem value="WORK_ORDER">Whole work order at this step</SelectItem>
                                                <SelectItem value="ROLLING_N">Rolling last N inspections</SelectItem>
                                                <SelectItem value="LOT">Receiving lot sample</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )} />
                                {form.watch("gate_window") === "ROLLING_N" && (
                                    <FormField control={form.control} name="gate_window_n" render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>N (rolling window)</FormLabel>
                                            <FormControl>
                                                <Input type="number" min={1} value={field.value ?? ""}
                                                    onChange={(e) => field.onChange(e.target.value === "" ? null : Number(e.target.value))} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )} />
                                )}
                                {form.watch("gate_metric") === "FAIL_RATE_PCT" && (
                                    <FormField control={form.control} name="gate_min_sample" render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Min sample before firing</FormLabel>
                                            <FormControl>
                                                <Input type="number" min={1} value={field.value ?? ""}
                                                    onChange={(e) => field.onChange(e.target.value === "" ? null : Number(e.target.value))} />
                                            </FormControl>
                                            <FormDescription>Guards against firing on a tiny sample.</FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )} />
                                )}
                            </div>

                            <FormField control={form.control} name="gate_actions" render={({ field }) => {
                                const selected: string[] = field.value ?? []
                                const toggle = (v: string) =>
                                    field.onChange(selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v])
                                return (
                                    <FormItem>
                                        <FormLabel>Actions when tripped</FormLabel>
                                        <div className="space-y-2">
                                            {GATE_ACTIONS.map((a) => (
                                                <label key={a.value} className="flex items-center gap-2 text-sm">
                                                    <Checkbox checked={selected.includes(a.value)} onCheckedChange={() => toggle(a.value)} />
                                                    {a.label}
                                                </label>
                                            ))}
                                        </div>
                                        <FormDescription>
                                            Route-to-alternate also requires the step's decision type = "Quality Gate
                                            (aggregate signal)", set in the process editor.
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )
                            }} />

                            {(form.watch("gate_actions") ?? []).includes("RAISE_CAPA_SCAR") && (
                                <div className="grid grid-cols-2 gap-4">
                                    <FormField control={form.control} name="gate_capa_type" render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>CAPA type</FormLabel>
                                            <Select value={field.value || "CORRECTIVE"} onValueChange={field.onChange}>
                                                <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                                                <SelectContent>
                                                    <SelectItem value="CORRECTIVE">Corrective (CAPA)</SelectItem>
                                                    <SelectItem value="SUPPLIER">Supplier (SCAR)</SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )} />
                                    <FormField control={form.control} name="gate_capa_severity" render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Severity</FormLabel>
                                            <Select value={field.value || "MAJOR"} onValueChange={field.onChange}>
                                                <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                                                <SelectContent>
                                                    <SelectItem value="CRITICAL">Critical</SelectItem>
                                                    <SelectItem value="MAJOR">Major</SelectItem>
                                                    <SelectItem value="MINOR">Minor</SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )} />
                                </div>
                            )}

                            {(form.watch("gate_actions") ?? []).includes("REQUIRE_APPROVAL") && (
                                <FormField control={form.control} name="gate_approval_template" render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Approval template</FormLabel>
                                        <Select value={field.value ?? NONE} onValueChange={(v) => field.onChange(v === NONE ? null : v)}>
                                            <FormControl><SelectTrigger className="w-[300px]"><SelectValue placeholder="Select template…" /></SelectTrigger></FormControl>
                                            <SelectContent>
                                                <SelectItem value={NONE}>—</SelectItem>
                                                {(approvalTemplates?.results ?? []).map((t: any) => (
                                                    <SelectItem key={t.id} value={String(t.id)}>{t.name ?? t.title ?? t.id}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )} />
                            )}
                        </>
                    )}
                </div>

                <Button type="submit">Submit</Button>
            </form>
        </Form>
    )
}
