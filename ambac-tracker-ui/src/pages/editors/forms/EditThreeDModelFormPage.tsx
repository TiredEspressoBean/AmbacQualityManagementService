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
import { useRetrieveSteps } from "@/hooks/useRetrieveSteps";

const formSchema = z.object({
    name: z
        .string()
        .min(1, "Model name is required")
        .max(255, "Model name must be 255 characters or less"),
    file: z
        .any()
        .refine(
            (file) => file instanceof File || (Array.isArray(file) && file.length > 0),
            "A 3D model file is required - please select a file to upload (GLB, STEP up to 50MB)"
        )
        .optional(),
    part_type: z.string().optional(),
    step: z.string().optional(),
});

export default function ThreeDModelFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const modelId = params.id ? parseInt(params.id, 10) : undefined;

    const [files, setFiles] = useState<File[] | null>(null);
    const [partTypeSearch, setPartTypeSearch] = useState("");
    const [rawPartTypeSearch, setRawPartTypeSearch] = useState("");
    const [stepSearch, setStepSearch] = useState("");
    const [rawStepSearch, setRawStepSearch] = useState("");

    const { data: model, isLoading: isLoadingModel } = useRetrieveThreeDModel(modelId!);

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

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            part_type: "",
            step: "",
        },
    });

    const selectedPartType = form.watch("part_type");

    const { data: partTypesData } = useRetrievePartTypes({
        queries: { limit: 1000, search: partTypeSearch },
    });

    const { data: stepsData } = useRetrieveSteps({
        queries: {
            limit: 1000,
            search: stepSearch,
            process__part_type: selectedPartType ? parseInt(selectedPartType) : undefined
        },
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
                form.setValue("step", undefined);
            }
        }
    }, [selectedPartType]);

    const createModel = useCreateThreeDModel();
    const updateModel = useUpdateThreeDModel();

    async function onSubmit(values: z.infer<typeof formSchema>) {
        try {
            // Validate file exists for create mode
            if (mode === "create" && (!values.file || !(values.file instanceof File))) {
                toast.error("Please select a valid 3D model file to upload");
                return;
            }

            // Build the payload according to API schema
            const payload: {
                name: string;
                file?: File;
                part_type?: number | null;
                step?: number | null;
            } = {
                name: values.name,
                part_type: values.part_type ? parseInt(values.part_type) : null,
                step: values.step ? parseInt(values.step) : null,
            };

            // Only include file if one was selected
            if (values.file && values.file instanceof File) {
                payload.file = values.file;
            }

            console.log("Submitting with payload:", payload);

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
                                <FormLabel>Model Name *</FormLabel>
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
                                <FormLabel>
                                    3D Model File {mode === "create" ? "*" : ""}
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
                            return (
                                <FormItem>
                                    <FormLabel>Part Type (Optional)</FormLabel>
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
                                                    {selected?.name ?? "Select part type"}
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
                                                                form.setValue("part_type", undefined);
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
                                                        {partTypesData?.results?.map((partType: any) => (
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
                                        Associate this model with a specific part type
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
                            return (
                                <FormItem>
                                    <FormLabel>Step (Optional)</FormLabel>
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
                                                    {selected?.name ?? "Select step"}
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
                                                                form.setValue("step", undefined);
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
                                                        {stepsData?.results?.map((step: any) => (
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
