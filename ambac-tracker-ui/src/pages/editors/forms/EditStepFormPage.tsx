"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"
import { Check, ChevronsUpDown } from "lucide-react"
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes"
import { useRetrieveProcesses } from "@/hooks/useRetrieveProcesses"
import { useCreateStep } from "@/hooks/useCreateStep"
import { useRetrieveStepWithSamplingRules } from "@/hooks/useRetrieveStepWithSamplingRules"
import { useUpdateStep } from "@/hooks/useUpdateStep"
import { useParams } from "@tanstack/react-router"
import SamplingRulesEditor from "@/components/SamplingRulesEditor.tsx";
import {useUpdateStepSamplingRules} from "@/hooks/useUpdateStepSamplingRules.ts";
import {DocumentUploader} from "@/pages/editors/forms/DocumentUploader.tsx";

const samplingRuleSchema = z.object({
    rule_type: z.string().min(1),
    value: z.union([z.string(), z.number(), z.null()]),
    order: z.number().min(0),
})

const formSchema = z.object({
    name: z.string().min(1),
    order: z.number().min(1),
    description: z.string(),
    part_type: z.number(),
    process: z.number(),
    rules: z.array(samplingRuleSchema),
    fallback_rules: z.array(samplingRuleSchema).optional(),
    fallback_threshold: z.number().optional(),
    fallback_duration: z.number().optional(),
})

export default function StepFormPage() {
    const params = useParams({ strict: false })
    const mode = params.id ? "edit" : "create"
    const stepId = params.id ? parseInt(params.id, 10) : undefined

    const [partTypeSearch, setPartTypeSearch] = useState("")
    const [processSearch, setProcessSearch] = useState("")
    const [selectedPartTypeId, setSelectedPartTypeId] = useState<number | null>(null)

    const { data: partTypes } = useRetrievePartTypes({ queries: { search: partTypeSearch } })
    const { data: processes } = useRetrieveProcesses({ queries: { search: processSearch, part_type: selectedPartTypeId ?? undefined } })
    const { data: step } = useRetrieveStepWithSamplingRules(
        { params: { id: stepId! } },
        { enabled: mode === "edit" && !!stepId }
    )

    const createStep = useCreateStep()
    const updateStep = useUpdateStep()
    const updateSamplingRules = useUpdateStepSamplingRules()

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            order: 1,
            description: "",
            part_type: undefined,
            process: undefined,
            rules: [],
            fallback_rules: [],
            fallback_threshold: undefined,
            fallback_duration: undefined,
        }
    })

    useEffect(() => {
        if (mode === "edit" && step) {
            form.reset({
                name: step.name ?? "",
                order: step.order ?? 1,
                description: step.description ?? "",
                part_type: step.part_type,
                process: step.process,
                rules: step.active_ruleset?.rules ?? [],
                fallback_rules: step.fallback_ruleset?.rules ?? [],
                fallback_threshold: step.active_ruleset?.fallback_threshold ?? undefined,
                fallback_duration: step.active_ruleset?.fallback_duration ?? undefined,
            })
            setSelectedPartTypeId(step.part_type)
        }
    }, [mode, step, form])

    function normalizeRules(
        rules: { rule_type: string; value: string | number | null | undefined }[]
    ): { rule_type: string; value: string | number | null; order: number }[] {
        return rules.map((rule, index) => ({
            rule_type: rule.rule_type,
            value: rule.value ?? null, // prevent undefined
            order: index + 1,          // 1-based indexing
        }));
    }

    function onSubmit(values: z.infer<typeof formSchema>) {
        const {
            rules,
            fallback_rules,
            fallback_threshold,
            fallback_duration,
            ...stepData
        } = values;

        const normalizedRules = normalizeRules(rules);
        const normalizedFallbackRules = normalizeRules(fallback_rules ?? []);

        if (mode === "edit" && stepId) {
            updateStep.mutate(
                { id: stepId, data: stepData },
                {
                    onSuccess: () => {
                        updateSamplingRules.mutate(
                            {
                                id: stepId,
                                data: {
                                    rules: normalizedRules,
                                    fallback_rules: normalizedFallbackRules,
                                    fallback_threshold,
                                    fallback_duration,
                                },
                            },
                            {
                                onSuccess: () => toast.success("Step + rules updated."),
                                onError: (err) => {
                                    console.error("❌ updateSamplingRules failed:", err);
                                    toast.error("Step updated, but rules failed.");
                                },
                            }
                        );
                    },
                    onError: (err) => {
                        console.error("❌ updateStep failed:", err);
                        toast.error("Failed to update step.");
                    },
                }
            );
        } else {
            createStep.mutate(stepData, {
                onSuccess: (createdStep) => {
                    toast.success("Step created.");

                    if (createdStep?.id) {
                        updateSamplingRules.mutate(
                            {
                                id: createdStep.id,
                                data: {
                                    rules: normalizedRules,
                                    fallback_rules: normalizedFallbackRules,
                                    fallback_threshold,
                                    fallback_duration,
                                },
                            },
                            {
                                onError: (err) => {
                                    console.error("❌ updateSamplingRules (after create) failed:", err);
                                    toast.error("Step created, but rules failed.");
                                },
                            }
                        );
                    }

                    form.reset();
                },
                onError: (err) => {
                    console.error("❌ createStep failed:", err);
                    toast.error("Failed to create step.");
                },
            });
        }
    }



    return (
        <div>
            <Form {...form}>
                <h1 className="text-3xl font-bold tracking-tight">{mode === "edit" ? "Edit Step" : "Create Step"}</h1>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8 max-w-3xl mx-auto py-10">

                    <FormField
                        control={form.control}
                        name="order"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel>Step Number</FormLabel>
                                <FormControl>
                                    <Input type="number" {...field} />
                                </FormControl>
                                <FormDescription>Position of the step in the process</FormDescription>
                                <FormMessage/>
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="description"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel>Description</FormLabel>
                                <FormControl>
                                    <Textarea className="resize-none" {...field} />
                                </FormControl>
                                <FormDescription>Details about what happens in this step</FormDescription>
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
                                    <FormLabel>Part Type</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                                >
                                                    {selected?.name ?? "Select a part type"}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-[300px] p-0">
                                            <Command>
                                                <CommandInput
                                                    value={partTypeSearch}
                                                    onValueChange={setPartTypeSearch}
                                                    placeholder="Search part types..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No part types found.</CommandEmpty>
                                                    <CommandGroup>
                                                        {partTypes?.results.map((pt) => (
                                                            <CommandItem
                                                                key={pt.id}
                                                                value={pt.name}
                                                                onSelect={() => {
                                                                    form.setValue("part_type", pt.id)
                                                                    setSelectedPartTypeId(pt.id)
                                                                    setPartTypeSearch("")
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn("mr-2 h-4 w-4", pt.id === field.value ? "opacity-100" : "opacity-0")}
                                                                />
                                                                {pt.name}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                    <FormDescription>Choose the part type this step belongs to</FormDescription>
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
                                    <FormLabel>Process</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                                >
                                                    {selected?.name ?? "Select a process"}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-[300px] p-0">
                                            <Command>
                                                <CommandInput
                                                    value={processSearch}
                                                    onValueChange={setProcessSearch}
                                                    placeholder="Search processes..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No processes found.</CommandEmpty>
                                                    <CommandGroup>
                                                        {processes?.results.map((p) => (
                                                            <CommandItem
                                                                key={p.id}
                                                                value={p.name}
                                                                onSelect={() => {
                                                                    form.setValue("process", p.id)
                                                                    setProcessSearch("")
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn("mr-2 h-4 w-4", p.id === field.value ? "opacity-100" : "opacity-0")}
                                                                />
                                                                {p.name}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                    <FormDescription>Choose the process this step is part of</FormDescription>
                                    <FormMessage/>
                                </FormItem>
                            )
                        }}
                    />

                    <div className="space-y-4">
                        <FormLabel>Sampling Rules</FormLabel>
                        <FormDescription>
                            Define rules for when quality checks should occur during this step.
                        </FormDescription>
                        <SamplingRulesEditor name="rules"/>
                    </div>

                    <SamplingRulesEditor name="fallback_rules" label="Fallback Rules"/>

                    <FormField
                        control={form.control}
                        name="fallback_threshold"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel>Fallback Threshold</FormLabel>
                                <FormControl>
                                    <Input
                                        type="number"
                                        value={field.value ?? ""}
                                        onChange={(e) => {
                                            const parsed = parseInt(e.target.value);
                                            field.onChange(isNaN(parsed) ? null : parsed);
                                        }}
                                    />
                                </FormControl>
                                <FormMessage/>
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="fallback_duration"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel>Fallback Duration (number of correct parts)</FormLabel>
                                <FormControl>
                                    <Input
                                        type="number"
                                        value={field.value ?? ""}
                                        onChange={(e) => {
                                            const parsed = parseInt(e.target.value);
                                            field.onChange(isNaN(parsed) ? null : parsed);
                                        }}
                                    />
                                </FormControl>
                                <FormMessage/>
                            </FormItem>
                        )}
                    />

                    <Button type="submit" disabled={createStep.isPending || updateStep.isPending}>
                        {mode === "edit"
                            ? updateStep.isPending
                                ? "Saving..."
                                : "Save Changes"
                            : createStep.isPending
                                ? "Creating..."
                                : "Create Step"}
                    </Button>
                </form>
            </Form>

            {mode === "edit" && stepId && (
                <div className="max-w-3xl mx-auto py-6">
                    <h3 className="text-lg font-semibold">Attach Documents</h3>
                    <DocumentUploader objectId={stepId} contentType="steps"/>
                </div>)}
        </div>
    )
}
