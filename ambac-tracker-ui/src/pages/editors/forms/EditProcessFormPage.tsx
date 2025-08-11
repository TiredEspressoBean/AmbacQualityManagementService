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
import {useUpdateProcess} from "@/hooks/useUpdateProcess";
import {useRetrievePartTypes} from "@/hooks/useRetrievePartTypes";
import StepFields from "@/components/step-fields";
import {useDebounce} from "@/hooks/useDebounce.ts";
import {DocumentUploader} from "@/pages/editors/forms/DocumentUploader.tsx";

const stepSchema = z.object({
    name: z
        .string()
        .min(1, "Step name is required - please enter a descriptive name for this step")
        .max(255, "Step name must be 255 characters or less"),
    description: z
        .string()
        .min(1, "Step description is required - please describe what happens in this step")
        .max(1000, "Step description must be 1000 characters or less"),
    expected_duration: z.number().nullable().optional(),
});

const formSchema = z.object({
    name: z
        .string()
        .min(1, "Process name is required - please enter a descriptive name for this process")
        .max(255, "Process name must be 255 characters or less"), is_remanufactured: z.boolean(),
    part_type: z
        .number()
        .int("Part type must be selected - please choose a valid part type for this process")
        .min(1, "Part type must be selected - please choose a valid part type for this process"),
    num_steps: z
        .number()
        .min(1, "Number of steps must be at least 1 - please specify how many steps this process requires")
        .max(50, "Number of steps cannot exceed 50 - please use a reasonable number of steps"),
    is_batch_process: z.boolean(),
    steps: z
        .array(stepSchema)
        .min(1, "At least one step is required - please define the steps for this process"),
});

export type FormSchema = z.infer<typeof formSchema>;

export default function ProcessFormPage() {
    const params = useParams({strict: false});
    const mode = params.id ? "edit" : "create";
    const processId = params.id ? parseInt(params.id, 10) : undefined;

    const {
        data, isLoading
    } = useRetrieveProcessWithSteps({params: {id: processId!}}, {enabled: mode === "edit" && !!processId});

    const [partTypeSearch, setPartTypeSearch] = useState("");
    const debouncedSearch = useDebounce(partTypeSearch, 300);
    const {data: partTypes} = useRetrievePartTypes({queries: {search: debouncedSearch}});

    const form = useForm<FormSchema>({
        resolver: zodResolver(formSchema), defaultValues: {
            name: "",
            is_remanufactured: false,
            part_type: undefined,
            num_steps: 5,
            is_batch_process: false,
            steps: Array.from({length: 5}, () => ({
                name: "", description: "", expected_duration: undefined,
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
        if (typeof debouncedNumSteps !== "number" || debouncedNumSteps < 1) return;

        const currentSteps = form.getValues("steps");
        const currentLength = currentSteps?.length;

        if (debouncedNumSteps !== currentLength) {
            form.setValue("steps", Array.from({length: debouncedNumSteps}, (_, i) => currentSteps[i] ?? {
                name: "", description: "", expected_duration: undefined,
            }));
        }
    }, [debouncedNumSteps, form, mode]);

    useEffect(() => {
        if (mode === 'edit' && processId && !isLoading && data && data?.id !== undefined) {
            const stepsData = Array.isArray(data.steps) ? data.steps : [];
            const numSteps = data.num_steps ?? (stepsData.length || 1);

            const formattedSteps = stepsData.length > 0 ? stepsData.map(step => ({
                name: step.name || "",
                description: step.description || "",
                expected_duration: step.expected_duration ?? null,
            })) : Array.from({length: numSteps}, () => ({
                name: "", description: "", expected_duration: null,
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
        const processed = {
            ...values, steps: values.steps.map((step, index) => ({
                ...step, order: index + 1,
            })),
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
                            <FormLabel>Name *</FormLabel>
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
                            <FormLabel>Part Type *</FormLabel>
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
                            <FormLabel>Number of Steps *</FormLabel>
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

                    {fields.map((field, index) => (<StepFields
                        key={field.id}
                        index={index}
                        control={control}
                        name="steps"
                    />))}

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