"use client"

import { useCreateSamplingRuleSet } from "@/hooks/useCreateSamplingRuleSet"
import { useUpdateSamplingRuleSet } from "@/hooks/useUpdateSamplingRuleSet"
import { useRetrieveSamplingRuleSet } from "@/hooks/useRetrieveSamplingRuleSet"
import { useParams } from "@tanstack/react-router"

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
}).extend({
    // Process is optional in API but required for this form
    process: z.string().min(1),
})

const NONE = "__none__"

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

    useEffect(() => {
        if (mode === "edit" && ruleSet) {
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
                await createRuleSet.mutateAsync(values as never)
                toast.success("Rule set created")
                form.reset() // optional: reset after create
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

                <div className="rounded-md border p-4 space-y-4">
                    <div>
                        <div className="text-sm font-medium">Acceptance sampling</div>
                        <p className="text-xs text-muted-foreground">
                            Used when this rule set is on a RECEIVING step — resolves the incoming lot's
                            sample plan (n / Ac / Re). Leave blank for ordinary in-process sampling.
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
                                <FormControl><Input placeholder="1.0" {...field} value={field.value ?? ""} /></FormControl>
                                <FormDescription>Acceptable Quality Limit (e.g. 1.0, 0.65).</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )} />
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

                <Button type="submit">Submit</Button>
            </form>
        </Form>
    )
}
