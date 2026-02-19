import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { Button } from "@/components/ui/button";
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
    FileInput,
    FileUploader,
    FileUploaderContent,
    FileUploaderItem,
} from "@/components/ui/file-upload";
import { CloudUpload, Paperclip, Check, ChevronsUpDown } from "lucide-react";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command";
import { cn } from "@/lib/utils";
import { useParams } from "@tanstack/react-router";

import { useRetrieveThreeDModel } from "@/hooks/useRetrieveThreeDModel";
import { useCreateThreeDModel } from "@/hooks/useCreateThreeDModel";
import { useUpdateThreeDModel } from "@/hooks/useUpdateThreeDModel";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { useRetrievePartType } from "@/hooks/useRetrievePartType";
import { useRetrieveSteps } from "@/hooks/useRetrieveSteps";
import { useRetrieveStep } from "@/hooks/useRetrieveStep";
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";

// Use generated schema with custom file handling
const formSchema = schemas.ThreeDModelRequest.pick({
    name: true,
    part_type: true,
    step: true,
}).extend({
    // Override file to be optional for edit mode
    file: z.any().optional(),
});

type FormValues = z.infer<typeof formSchema>;

// Pre-compute required fields for labels
const required = {
    name: isFieldRequired(formSchema.shape.name),
    part_type: isFieldRequired(formSchema.shape.part_type),
    step: isFieldRequired(formSchema.shape.step),
};

export default function ThreeDModelFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const modelId = params.id;

    const [files, setFiles] = useState<File[] | null>(null);
    const [partTypeSearch, setPartTypeSearch] = useState("");
    const [rawPartTypeSearch, setRawPartTypeSearch] = useState("");
    const [stepSearch, setStepSearch] = useState("");
    const [rawStepSearch, setRawStepSearch] = useState("");

    const { data: model, isLoading: isLoadingModel } = useRetrieveThreeDModel(modelId!);

    // Fetch the specific part type and step if they exist on the model
    const { data: selectedPartTypeData } = useRetrievePartType(
        { params: { id: model?.part_type ?? 0 } },
        { enabled: !!model?.part_type }
    );
    const { data: selectedStepData } = useRetrieveStep(
        { params: { id: model?.step ?? 0 } },
        { enabled: !!model?.step }
    );

    // Debounce part type search
    useEffect(() => {
        const timeout = setTimeout(() => {
            setPartTypeSearch(rawPartTypeSearch);
        }, 300);
        return () => clearTimeout(timeout);
    }, [rawPartTypeSearch]);

    // Debounce step search
    useEffect(() => {
        const timeout = setTimeout(() => {
            setStepSearch(rawStepSearch);
        }, 300);
        return () => clearTimeout(timeout);
    }, [rawStepSearch]);

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            part_type: "",
            step: "",
        },
    });

    const selectedPartType = form.watch("part_type");

    const { data: partTypesData } = useRetrievePartTypes({
        limit: 1000, search: partTypeSearch,
    });

    const { data: stepsData } = useRetrieveSteps({
        limit: 1000,
        search: stepSearch,
        process__part_type: selectedPartType || undefined
    });

    // Reset form when model data loads
    useEffect(() => {
        if (mode === "edit" && model) {
            form.reset({
                name: model.name || "",
                part_type: model.part_type ? String(model.part_type) : "",
                step: model.step ? String(model.step) : "",
            });
        }
    }, [mode, model, form]);

    // Clear step selection when part type changes
    useEffect(() => {
        if (selectedPartType) {
            // Only clear if there's a current step selected
            const currentStep = form.getValues("step");
            if (currentStep) {
                form.setValue("step", "");
            }
        }
    }, [selectedPartType]);

    const createModel = useCreateThreeDModel();
    const updateModel = useUpdateThreeDModel();

    async function onSubmit(values: FormValues) {
        try {
            // Validate file exists for create mode
            if (mode === "create" && (!values.file || !(values.file instanceof File))) {
                toast.error("Please select a valid 3D model file to upload");
                return;
            }

            // Build payload as plain object - zodios converts to form-data
            const payload: any = {
                name: values.name,
                part_type: values.part_type,
                ...(values.step && values.step.trim() !== "" && { step: values.step }),
            };

            // Only include file if one was selected
            if (values.file && values.file instanceof File) {
                payload.file = values.file;
            }

            if (mode === "edit" && modelId) {
                await updateModel.mutateAsync({ id: modelId, data: payload });
                toast.success("3D Model updated successfully!");
            } else {
                await createModel.mutateAsync(payload);
                toast.success("3D Model created successfully!");
                form.reset();
                setFiles(null);
            }
        } catch (error) {
            console.error("Form submission error", error);
            toast.error("Failed to submit the form. Please try again.");
        }
    }

    // Show loading state
    if (mode === "edit" && isLoadingModel) {
        return (
            <div className="max-w-3xl mx-auto py-10">
                <div className="animate-pulse">
                    <div className="h-8 bg-gray-200 rounded mb-4"></div>
                    <div className="h-4 bg-gray-200 rounded mb-8"></div>
                    <div className="h-32 bg-gray-200 rounded"></div>
                </div>
            </div>
        );
    }

    return (
        <Form {...form}>
            <h1 className="text-3xl font-bold tracking-tight">
                {mode === "edit" ? "Edit 3D Model" : "Upload 3D Model"}
            </h1>
            <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-8 max-w-3xl mx-auto py-10"
            >
                    <FormField
                        control={form.control}
                        name="name"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.name}>Model Name</FormLabel>
                                <FormControl>
                                    <Input
                                        placeholder="e.g. Part Assembly v1.0"
                                        {...field}
                                    />
                                </FormControl>
                                <FormDescription>
                                    A descriptive name for this 3D model
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="file"
                        render={() => (
                            <FormItem>
                                <FormLabel required={mode === "create"}>
                                    3D Model File
                                </FormLabel>
                                <FormControl>
                                    <FileUploader
                                        value={files}
                                        onValueChange={(newFiles) => {
                                            setFiles(newFiles);
                                            if (newFiles && newFiles.length > 0) {
                                                form.setValue("file", newFiles[0]);
                                            } else {
                                                form.setValue("file", undefined);
                                            }
                                        }}
                                        dropzoneOptions={{
                                            maxFiles: 1,
                                            maxSize: 1024 * 1024 * 50,
                                            accept: {
                                                'model/gltf-binary': ['.glb'],
                                                'application/step': ['.step', '.stp'],
                                                'application/x-step': ['.step', '.stp']
                                            }
                                        }}
                                        className="relative bg-background rounded-lg p-2"
                                    >
                                        <FileInput
                                            id="fileInput"
                                            className="outline-dashed outline-1 outline-slate-500"
                                        >
                                            <div className="flex items-center justify-center flex-col p-8 w-full">
                                                <CloudUpload className="text-gray-500 w-10 h-10"/>
                                                <p className="mb-1 text-sm text-gray-500 dark:text-gray-400">
                                                    <span className="font-semibold">Click to upload</span> or drag and drop
                                                </p>
                                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                                    GLB, STEP up to 50MB
                                                </p>
                                            </div>
                                        </FileInput>
                                        <FileUploaderContent>
                                            {files?.map((file, i) => (
                                                <FileUploaderItem key={i} index={i}>
                                                    <Paperclip className="h-4 w-4 stroke-current"/>
                                                    <span>{file.name}</span>
                                                </FileUploaderItem>
                                            ))}
                                        </FileUploaderContent>
                                    </FileUploader>
                                </FormControl>
                                <FormDescription>
                                    {mode === "edit"
                                        ? "Upload a new file to replace the current model (optional)"
                                        : "Attach your 3D model file."}
                                </FormDescription>
                                {mode === "edit" && model?.file && (
                                    <p className="text-sm text-muted-foreground">
                                        Current file: {model.file.split("/").pop()}
                                    </p>
                                )}
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="part_type"
                        render={({ field }) => {
                            const selected = partTypesData?.results?.find(
                                (pt: any) => String(pt.id) === field.value
                            );
                            // Use fetched part type data if not found in search results
                            const displayName = selected?.name
                                || (field.value && selectedPartTypeData?.name)
                                || "Select part type";
                            return (
                                <FormItem>
                                    <FormLabel required={required.part_type}>Part Type</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    className={cn(
                                                        "w-[300px] justify-between",
                                                        !field.value && "text-muted-foreground"
                                                    )}
                                                >
                                                    {displayName}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-[300px] p-0">
                                            <Command shouldFilter={false}>
                                                <CommandInput
                                                    value={rawPartTypeSearch}
                                                    onValueChange={setRawPartTypeSearch}
                                                    placeholder="Search part types..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No part types found.</CommandEmpty>
                                                    <CommandGroup>
                                                        <CommandItem
                                                            value="none"
                                                            onSelect={() => {
                                                                form.setValue("part_type", "");
                                                                setPartTypeSearch("");
                                                                setRawPartTypeSearch("");
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn(
                                                                    "mr-2 h-4 w-4",
                                                                    !field.value ? "opacity-100" : "opacity-0"
                                                                )}
                                                            />
                                                            None
                                                        </CommandItem>
                                                        {partTypesData?.results?.map((partType: { id: string | number }) => (
                                                            <CommandItem
                                                                key={partType.id}
                                                                value={partType.id.toString()}
                                                                onSelect={() => {
                                                                    form.setValue("part_type", String(partType.id));
                                                                    setPartTypeSearch("");
                                                                    setRawPartTypeSearch("");
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn(
                                                                        "mr-2 h-4 w-4",
                                                                        String(partType.id) === field.value
                                                                            ? "opacity-100"
                                                                            : "opacity-0"
                                                                    )}
                                                                />
                                                                {partType.name}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                    <FormDescription>
                                        Required for traceability - links this 3D model to a part type for quality inspection
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            );
                        }}
                    />

                    <FormField
                        control={form.control}
                        name="step"
                        render={({ field }) => {
                            const selected = stepsData?.results?.find(
                                (s: any) => String(s.id) === field.value
                            );
                            // Use fetched step data if not found in search results
                            const displayName = selected?.name
                                || (field.value && selectedStepData?.name)
                                || "Select step";
                            return (
                                <FormItem>
                                    <FormLabel required={required.step}>Step</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    className={cn(
                                                        "w-[300px] justify-between",
                                                        !field.value && "text-muted-foreground"
                                                    )}
                                                >
                                                    {displayName}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-[300px] p-0">
                                            <Command shouldFilter={false}>
                                                <CommandInput
                                                    value={rawStepSearch}
                                                    onValueChange={setRawStepSearch}
                                                    placeholder="Search steps..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No steps found.</CommandEmpty>
                                                    <CommandGroup>
                                                        <CommandItem
                                                            value="none"
                                                            onSelect={() => {
                                                                form.setValue("step", "");
                                                                setStepSearch("");
                                                                setRawStepSearch("");
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn(
                                                                    "mr-2 h-4 w-4",
                                                                    !field.value ? "opacity-100" : "opacity-0"
                                                                )}
                                                            />
                                                            None
                                                        </CommandItem>
                                                        {stepsData?.results?.map((step: { id: string | number }) => (
                                                            <CommandItem
                                                                key={step.id}
                                                                value={step.id.toString()}
                                                                onSelect={() => {
                                                                    form.setValue("step", String(step.id));
                                                                    setStepSearch("");
                                                                    setRawStepSearch("");
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn(
                                                                        "mr-2 h-4 w-4",
                                                                        String(step.id) === field.value
                                                                            ? "opacity-100"
                                                                            : "opacity-0"
                                                                    )}
                                                                />
                                                                {step.name}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                    <FormDescription>
                                        Associate this model with a specific step in a process
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            );
                        }}
                    />

                    <Button
                        type="submit"
                        disabled={createModel.isPending || updateModel.isPending}
                    >
                        {mode === "edit"
                            ? updateModel.isPending
                                ? "Saving..."
                                : "Save Changes"
                            : createModel.isPending
                                ? "Uploading..."
                                : "Upload Model"}
                    </Button>
                </form>
            </Form>
    );
}
