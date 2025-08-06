"use client";

import {useEffect, useState} from "react";
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
import {
    FileInput,
    FileUploader,
    FileUploaderContent,
    FileUploaderItem,
} from "@/components/ui/file-upload";
import { CloudUpload, Paperclip } from "lucide-react";
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
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useRetrieveParts } from "@/hooks/useRetrieveParts";
import { useRetrieveProcesses } from "@/hooks/useRetrieveProcesses";
import { useRetrieveSteps } from "@/hooks/useRetrieveSteps";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { useRetrieveOrders } from "@/hooks/useRetrieveOrders";
import { useRetrieveWorkOrders } from "@/hooks/useRetrieveWorkOrders";
import {useRetrieveDocument} from "@/hooks/useRetrieveDocument.ts";
import {useCreateDocument} from "@/hooks/useCreateDocument.ts";
import {useParams} from "@tanstack/react-router";
import {schemas} from "@/lib/api/generated.ts";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {useUpdateDocument} from "@/hooks/useUpdateDocument.ts";


// {
//     "id": 3,
//     "is_image": true,
//     "file_name": "example.txt",
//     "file": "http://localhost:8000/parts_docs/2025-07-08/example_fh3RrGp.txt.txt",
//     "file_url": "/parts_docs/2025-07-08/example_fh3RrGp.txt.txt",
//     "content_type": 12,
//     "content_type_model": "parts",
//     "object_id": 6,
//     "version": 1
// },

const DOCUMENT_CLASSIFICATION = schemas.ClassificationEnum.options;

const formSchema = z.object({
    file: z
        .any()
        .refine(
            (file) => file instanceof File || (Array.isArray(file) && file.length > 0), 
            "A file is required - please select a document to upload (PDF, DOCX, or image up to 10MB)"
        ),
    classification_level: z
        .string()
        .min(1, "Classification level is required - please select the security level for this document"),
    content_type: z.string().optional(),
    object_id: z.number().optional(),
});

type FormValues = z.infer<typeof formSchema>;

const contentTypeOptions = [
    { label: "Part Type", value: "tracker.parttype" },
    { label: "Part", value: "tracker.part" },
    { label: "Order", value: "tracker.order" },
    { label: "Work Order", value: "tracker.workorder" },
    { label: "Process", value: "tracker.process" },
    { label: "Step", value: "tracker.step" },
];

export default function DocumentFormPage() {
    const [files, setFiles] = useState<File[] | null>(null);
    const [contentTypeSearch, setContentTypeSearch] = useState("");
    const [objectSearch, setObjectSearch] = useState("");

    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const documentId = params.id ? parseInt(params.id, 10) : undefined;

    const { data: document } = useRetrieveDocument({ params: { id: documentId! } }, { enabled: mode === "edit" && !!documentId });
    const createDocument = useCreateDocument();
    const updateDocument = useUpdateDocument();

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            file: undefined,
            classification_level: "",
            content_type: undefined,
            object_id: undefined,
        },
    });

    useEffect(() => {
        if (mode === "edit" && document) {
            form.reset({
                classification_level: document.classification ?? "",
                content_type: document.content_type_model ? `tracker.${document.content_type_model}` : undefined,
                object_id: document.object_id ?? undefined,
                file: undefined,
            });
        }
    }, [mode, document, form]);

    const selectedContentType = form.watch("content_type");

    const { data: parts } = useRetrieveParts({ queries: { search: objectSearch } }, { enabled: selectedContentType === "tracker.part" });
    const { data: partTypes } = useRetrievePartTypes({ queries: { search: objectSearch } }, { enabled: selectedContentType === "tracker.parttype" });
    const { data: orders } = useRetrieveOrders({ queries: { search: objectSearch } }, { enabled: selectedContentType === "tracker.order" });
    const { data: workOrders } = useRetrieveWorkOrders({ queries: { search: objectSearch } }, { enabled: selectedContentType === "tracker.workorder" });
    const { data: processes } = useRetrieveProcesses({ queries: { search: objectSearch } }, { enabled: selectedContentType === "tracker.process" });
    const { data: steps } = useRetrieveSteps({ queries: { search: objectSearch } }, { enabled: selectedContentType === "tracker.step" });

    const objects = selectedContentType === "tracker.part" ? parts?.results
        : selectedContentType === "tracker.parttype" ? partTypes?.results
            : selectedContentType === "tracker.order" ? orders?.results
                : selectedContentType === "tracker.workorder" ? workOrders?.results
                    : selectedContentType === "tracker.process" ? processes?.results
                        : selectedContentType === "tracker.step" ? steps?.results
                            : [];

    const [rawObjectSearch, setRawObjectSearch] = useState("");

    useEffect(() => {
        const timeout = setTimeout(() => {
            setObjectSearch(rawObjectSearch); // this triggers your TanStack Query
        }, 300); // adjust delay as needed

        return () => clearTimeout(timeout);
    }, [rawObjectSearch]);

    async function onSubmit(values: FormValues) {
        try {
            const payload = new FormData();
            payload.append("file", values.file);
            payload.append("classification_level", values.classification_level);
            if (values.content_type) payload.append("content_type", values.content_type);
            if (values.object_id) payload.append("object_id", values.object_id.toString());

            if (mode === "edit" && documentId) {
                await updateDocument.mutateAsync({ id: documentId, data: payload });
                toast.success("Document updated successfully!");
            } else {
                await createDocument.mutateAsync(payload);
                toast.success("Document created successfully!");
                form.reset();
                setFiles(null);
            }
        } catch (error) {
            console.error("Form submission error", error);
            toast.error("Failed to submit the form. Please try again.");
        }
    }

    return (
        <Form {...form}>
            <h1 className="text-3xl font-bold tracking-tight">{mode === "edit" ? "Edit Document" : "Create Document"}</h1>
            <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-8 max-w-3xl mx-auto py-10"
            >
                <FormField
                    control={form.control}
                    name="file"
                    render={() => (
                        <FormItem>
                            <FormLabel>Select File *</FormLabel>
                            <FormControl>
                                <FileUploader
                                    value={files}
                                    onValueChange={(newFiles) => {
                                        setFiles(newFiles);
                                        form.setValue("file", newFiles?.[0]);
                                    }}
                                    dropzoneOptions={{maxFiles: 1, maxSize: 1024 * 1024 * 10}}
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
                                                PDF, DOCX, Images up to 10MB
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
                            <FormDescription>Attach the document file.</FormDescription>
                            <FormMessage/>
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="classification_level"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Classification Level *</FormLabel>
                            <Select
                                value={field.value}
                                onValueChange={field.onChange}
                                defaultValue={field.value}
                            >
                                <FormControl>
                                    <SelectTrigger className="w-[300px]">
                                        <SelectValue placeholder="Select a level" />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                    {DOCUMENT_CLASSIFICATION.map((level) => (
                                        <SelectItem key={level} value={level}>
                                            {level}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <FormDescription>The security level for this document.</FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="content_type"
                    render={({field}) => {
                        const selected = contentTypeOptions.find((opt) => opt.value === field.value);
                        return (
                            <FormItem>
                                <FormLabel>Attach To</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                            >
                                                {selected?.label ?? "Select model"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-[300px] p-0">
                                        <Command>
                                            <CommandInput
                                                value={contentTypeSearch}
                                                onValueChange={setContentTypeSearch}
                                                placeholder="Search models..."
                                            />
                                            <CommandList>
                                                <CommandEmpty>No models found.</CommandEmpty>
                                                <CommandGroup>
                                                    {contentTypeOptions.map((opt) => (
                                                        <CommandItem
                                                            key={opt.value}
                                                            value={opt.label}
                                                            onSelect={() => {
                                                                form.setValue("content_type", opt.value);
                                                                form.setValue("object_id", undefined);
                                                                setContentTypeSearch("");
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn(
                                                                    "mr-2 h-4 w-4",
                                                                    opt.value === field.value ? "opacity-100" : "opacity-0"
                                                                )}
                                                            />
                                                            {opt.label}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>Select the model this document should be attached to.</FormDescription>
                                <FormMessage/>
                            </FormItem>
                        );
                    }}
                />

                {selectedContentType && (
                    <FormField
                        control={form.control}
                        name="object_id"
                        render={({ field }) => {
                            const selected = objects?.find((obj) => obj.id === field.value);
                            return (
                                <FormItem>
                                    <FormLabel>Attach To Object</FormLabel>
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
                                                    {selected
                                                        ? selectedContentType === "tracker.step"
                                                            ? `${selected.name} (${selected.process_name})`
                                                            : selected.ERP_id || selected.name || selected.erp_id || `#${selected.id}`
                                                        : "Select instance"}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-[300px] p-0">
                                            <Command shouldFilter={false}>
                                                <CommandInput
                                                    value={rawObjectSearch}
                                                    onValueChange={setRawObjectSearch}
                                                    placeholder="Search..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No items found.</CommandEmpty>
                                                    <CommandGroup>
                                                        {objects?.map((obj) => (
                                                            <CommandItem
                                                                key={obj.id}
                                                                value={obj.id.toString()} // Not used for filtering
                                                                onSelect={() => {
                                                                    form.setValue("object_id", obj.id);
                                                                    setObjectSearch("");
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn(
                                                                        "mr-2 h-4 w-4",
                                                                        obj.id === field.value ? "opacity-100" : "opacity-0"
                                                                    )}
                                                                />
                                                                {selectedContentType === "tracker.step"
                                                                    ? `${obj.name} (${obj.process_name})`
                                                                    : obj.ERP_id || obj.name || obj.erp_id || `#${obj.id}`}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                    <FormDescription>
                                        Select the specific record to attach the document to.
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            );
                        }}
                    />
                )}


                <Button type="submit">Submit</Button>
            </form>
        </Form>
    );
}
