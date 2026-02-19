"use client";

import {useEffect, useState} from "react";
import {toast} from "sonner";
import {FormProvider, useFieldArray, useForm} from "react-hook-form";
import {zodResolver} from "@hookform/resolvers/zod";
import {z} from "zod";
import {Button} from "@/components/ui/button";
import {Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage,} from "@/components/ui/form";
import {Input} from "@/components/ui/input";
import {Checkbox} from "@/components/ui/checkbox";
import {Popover, PopoverContent, PopoverTrigger,} from "@/components/ui/popover";
import {Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,} from "@/components/ui/command";
import {Check, ChevronsUpDown} from "lucide-react";
import {cn} from "@/lib/utils";
import {useParams} from "@tanstack/react-router";

import {useRetrieveProcessWithSteps} from "@/hooks/useRetrieveProcessWithSteps.ts";
import {useCreateProcessWithSteps} from "@/hooks/useCreateProcessWithSteps";
import {useUpdateProcess} from "@/hooks/useUpdateProcessWithSteps";
import {useRetrievePartTypes} from "@/hooks/useRetrievePartTypes";
import StepFields from "@/components/step-fields";
import {useDebounce} from "@/hooks/useDebounce.ts";
import {DocumentUploader} from "@/pages/editors/forms/DocumentUploader.tsx";
import {parseDurationToMinutes, formatMinutesToDuration} from "@/lib/duration-utils";
import {schemas} from "@/lib/api/generated";
import {isFieldRequired} from "@/lib/zod-config";

// Local schemas for nested form state (not directly in API schema)
const samplingRuleSchema = z.object({
    rule_type: z.string().min(1),
    value: z.union([z.string(), z.number(), z.null()]).optional(),
    order: z.number().min(1).optional(),
});

const stepSchema = z.object({
    id: z.number().optional(),
    name: z.string().min(1).max(255),
    description: z.string().min(1).max(1000),
    expected_duration: z.number().nullable().optional(),
    sampling_rules: z.array(samplingRuleSchema).optional(),
    fallback_rules: z.array(samplingRuleSchema).optional(),
    fallback_threshold: z.number().nullable().optional(),
    fallback_duration: z.number().nullable().optional(),
});

// Use generated schema for base process fields, extend with form-specific fields
// Note: API uses nodes/edges for process flow, but form uses steps array for simpler editing
const formSchema = schemas.ProcessWithStepsRequest.pick({
    name: true,
    is_remanufactured: true,
    part_type: true,
    is_batch_process: true,
}).extend({
    // Override part_type to be string (ID value from select)
    part_type: z.string(),
    // Form-specific: controls how many step forms to show
    num_steps: z.number().min(1).max(50),
    // Form-specific: linear step array (transformed to nodes/edges on submit)
    steps: z.array(stepSchema).min(1),
});

export type FormSchema = z.infer<typeof formSchema>;

const required = {
    name: isFieldRequired(formSchema.shape.name),
    part_type: isFieldRequired(formSchema.shape.part_type),
    num_steps: isFieldRequired(formSchema.shape.num_steps),
};

export default function ProcessFormPage() {
    const params = useParams({strict: false});
    const mode = params.id ? "edit" : "create";
    const processId = params.id;

    const {
        data, isLoading
    } = useRetrieveProcessWithSteps({params: {id: processId!}}, {enabled: mode === "edit" && !!processId});

    const [partTypeSearch, setPartTypeSearch] = useState("");
    const debouncedSearch = useDebounce(partTypeSearch, 300);
    const {data: partTypes} = useRetrievePartTypes({search: debouncedSearch});

    const form = useForm<FormSchema>({
        resolver: zodResolver(formSchema), defaultValues: {
            name: "",
            is_remanufactured: false,
            part_type: undefined,
            num_steps: 5,
            is_batch_process: false,
            steps: Array.from({length: 5}, () => ({
                name: "", 
                description: "", 
                expected_duration: undefined,
                sampling_rules: [],
                fallback_rules: [],
                fallback_threshold: undefined,
                fallback_duration: undefined,
            })),
        },
    });

    const {control} = form;

    const {fields, replace} = useFieldArray({
        control: form.control, name: "steps",
    });

    const watchedNumSteps = form.watch("num_steps");
    const debouncedNumSteps = useDebounce(watchedNumSteps, 300);

    useEffect(() => {
        if (mode !== "create") return;
        if (debouncedNumSteps < 1) return;

        const currentSteps = form.getValues("steps");
        const currentLength = currentSteps?.length;

        if (debouncedNumSteps !== currentLength) {
            form.setValue("steps", Array.from({length: debouncedNumSteps}, (_, i) => currentSteps[i] ?? {
                name: "", 
                description: "", 
                expected_duration: undefined,
                sampling_rules: [],
                fallback_rules: [],
                fallback_threshold: undefined,
                fallback_duration: undefined,
            }));
        }
    }, [debouncedNumSteps, form, mode]);

    useEffect(() => {
        if (mode === 'edit' && processId && !isLoading && data && data?.id !== undefined) {
            // Use process_steps (new structure) - each has a nested step object
            const processSteps = Array.isArray(data.process_steps) ? data.process_steps : [];
            const numSteps = data.num_steps ?? (processSteps.length || 1);

            // Sort by order and extract step data
            const sortedProcessSteps = [...processSteps].sort((a, b) => (a.order || 0) - (b.order || 0));
            const formattedSteps = sortedProcessSteps.length > 0 ? sortedProcessSteps.map(ps => {
                // Convert duration string to minutes for form
                const durationMinutes = parseDurationToMinutes(ps.step?.expected_duration);
                return {
                    id: ps.step?.id, // Preserve step ID for updates
                    name: ps.step?.name || "",
                    description: ps.step?.description || "",
                    expected_duration: durationMinutes === '' ? null : durationMinutes,
                    sampling_rules: [],
                    fallback_rules: [],
                    fallback_threshold: null,
                    fallback_duration: null,
                };
            }) : Array.from({length: numSteps}, () => ({
                id: undefined,
                name: "",
                description: "",
                expected_duration: null,
                sampling_rules: [],
                fallback_rules: [],
                fallback_threshold: null,
                fallback_duration: null,
            }));

            const resetData: Omit<FormSchema, "steps"> = {
                name: data.name ?? "",
                is_remanufactured: data.is_remanufactured ?? false,
                part_type: data.part_type,
                is_batch_process: data.is_batch_process ?? false,
                num_steps: numSteps,
            };

            // Validate before applying
            const fullDataToValidate = {...resetData, steps: formattedSteps};
            const validationResult = formSchema.safeParse(fullDataToValidate);
            if (!validationResult.success) {
                console.error("Validation errors during reset:", validationResult.error.issues);
                return;
            }

            form.reset({...resetData, steps: []});  // clear steps first
            replace(formattedSteps);                  // then replace safely
        }
    }, [mode, processId, isLoading, data, form, replace]);


    const createProcess = useCreateProcessWithSteps();
    const updateProcess = useUpdateProcess();

    function onSubmit(values: FormSchema) {
        // Convert form steps to backend graph format (nodes + edges)
        // Backend expects: nodes (step data with IDs) and edges (connections)
        // Positive ID = existing step to update, negative ID = new step to create
        const nodes = values.steps.map((step, index) => ({
            id: step.id ?? -(index + 1), // Use real ID or negative temp ID for new steps
            name: step.name,
            description: step.description,
            order: index + 1,
            expected_duration: step.expected_duration ? formatMinutesToDuration(step.expected_duration) : null,
        }));

        // Create sequential edges for linear process (step1 → step2 → step3...)
        const edges = values.steps.slice(0, -1).map((_, index) => ({
            from_step: nodes[index].id,
            to_step: nodes[index + 1].id,
            edge_type: 'default',
        }));

        const processed = {
            name: values.name,
            is_remanufactured: values.is_remanufactured,
            part_type: values.part_type,
            num_steps: values.num_steps,
            is_batch_process: values.is_batch_process,
            nodes,
            edges,
        };

        if (mode === "edit" && processId) {
            updateProcess.mutate({id: processId, data: processed}, {
                onSuccess: () => toast.success("Process updated successfully!"), onError: (error) => {
                    console.error("Failed to update process:", error);
                    toast.error("Failed to update the process.");
                },
            });
        } else {
            createProcess.mutate(processed, {
                onSuccess: () => {
                    toast.success("Process created successfully!");
                    form.reset();
                }, onError: (error) => {
                    console.error("Failed to create process:", error);
                    toast.error("Failed to create the process.");
                },
            });
        }
    }

    return (<FormProvider {...form}>
        <div>
            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8 max-w-3xl mx-auto py-10">
                    <h1 className="text-3xl font-bold tracking-tight">{mode === "edit" ? "Edit Process" : "Create Process"}</h1>
                    <FormField
                        control={form.control}
                        name="name"
                        render={({field}) => (<FormItem>
                            <FormLabel required={required.name}>Name</FormLabel>
                            <FormControl>
                                <Input placeholder="e.g. Assembly Line 1" {...field} />
                            </FormControl>
                            <FormDescription>Name of the process to make a part</FormDescription>
                            <FormMessage/>
                        </FormItem>)}
                    />

                    <FormField
                        control={form.control}
                        name="is_remanufactured"
                        render={({field}) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                <FormControl>
                                    <Checkbox checked={field.value} onCheckedChange={field.onChange}/>
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel>Remanufacturing Process</FormLabel>
                                    <FormDescription>Is this process for remanufacturing parts?</FormDescription>
                                </div>
                                <FormMessage/>
                            </FormItem>)}
                    />

                    <FormField
                        control={form.control}
                        name="part_type"
                        render={({field}) => (<FormItem className="flex flex-col">
                            <FormLabel required={required.part_type}>Part Type</FormLabel>
                            <Popover>
                                <PopoverTrigger asChild>
                                    <FormControl>
                                        <Button
                                            variant="outline"
                                            role="combobox"
                                            className={cn("w-[200px] justify-between", !field.value && "text-muted-foreground")}
                                        >
                                            {field.value ? partTypes?.results.find((pt) => pt.id === field.value)?.name : "Select part type"}
                                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                        </Button>
                                    </FormControl>
                                </PopoverTrigger>
                                <PopoverContent className="w-[200px] p-0">
                                    <Command>
                                        <CommandInput
                                            placeholder="Search part type..."
                                            onValueChange={setPartTypeSearch}
                                        />
                                        <CommandList>
                                            <CommandEmpty>No part type found.</CommandEmpty>
                                            <CommandGroup>
                                                {partTypes?.results.map((pt) => (<CommandItem
                                                    key={pt.id}
                                                    value={pt.name}
                                                    onSelect={() => form.setValue("part_type", pt.id)}
                                                >
                                                    <Check
                                                        className={cn("mr-2 h-4 w-4", pt.id === field.value ? "opacity-100" : "opacity-0")}
                                                    />
                                                    {pt.name}
                                                </CommandItem>))}
                                            </CommandGroup>
                                        </CommandList>
                                    </Command>
                                </PopoverContent>
                            </Popover>
                            <FormDescription>Select the part type this process is associated with.</FormDescription>
                            <FormMessage/>
                        </FormItem>)}
                    />

                    <FormField
                        control={form.control}
                        name="num_steps"
                        render={({field}) => (<FormItem>
                            <FormLabel required={required.num_steps}>Number of Steps</FormLabel>
                            <FormControl>
                                <Input
                                    type="number"
                                    placeholder="e.g. 10"
                                    min={1}
                                    {...field}
                                    onChange={(e) => field.onChange(parseInt(e.target.value || "0", 10))}
                                />
                            </FormControl>
                            <FormDescription>How many steps should this process have?</FormDescription>
                            <FormMessage/>
                        </FormItem>)}
                    />

                    <FormField
                        control={form.control}
                        name="is_batch_process"
                        render={({field}) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                <FormControl>
                                    <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel>
                                        Batched Process
                                    </FormLabel>
                                    <FormDescription>
                                        For this process, are we tracking for the batch instead of tracking each individual part?
                                    </FormDescription>
                                </div>
                            </FormItem>)}
                    />

                    {fields.map((field, index) => {
                        // Get existing step from process_steps (sorted by order)
                        const sortedProcessSteps = mode === 'edit' && data?.process_steps
                            ? [...data.process_steps].sort((a, b) => (a.order || 0) - (b.order || 0))
                            : [];
                        const existingProcessStep = sortedProcessSteps[index];
                        const existingStep = existingProcessStep?.step;
                        return (
                            <StepFields
                                key={field.id}
                                index={index}
                                control={control}
                                name="steps"
                                existingStepId={existingStep?.id}
                                existingStepName={existingStep?.name}
                            />
                        );
                    })}

                    <Button
                        type="submit"
                        disabled={createProcess.isPending || updateProcess.isPending}
                    >
                        {mode === "edit" ? updateProcess.isPending ? "Saving..." : "Save Changes" : createProcess.isPending ? "Creating..." : "Create Process"}
                    </Button>
                </form>
            </Form>
            {mode === "edit" && processId && (

                <div className="max-w-3xl mx-auto py-6">
                    <h3 className="text-lg font-semibold">Attach Documents</h3>
                    <DocumentUploader objectId={processId} contentType="processes"/>
                </div>)}
        </div>
    </FormProvider>);
}