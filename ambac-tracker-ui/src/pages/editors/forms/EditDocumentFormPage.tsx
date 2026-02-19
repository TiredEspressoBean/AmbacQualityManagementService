"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "@tanstack/react-router";
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
import { Checkbox } from "@/components/ui/checkbox";
import {
    FileInput,
    FileUploader,
    FileUploaderContent,
    FileUploaderItem,
} from "@/components/ui/file-upload";
import { CloudUpload, Paperclip, Check, ChevronsUpDown, Loader2, FileType, Download, Eye } from "lucide-react";
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
import { useRetrieveParts } from "@/hooks/useRetrieveParts";
import { useRetrieveProcesses } from "@/hooks/useRetrieveProcesses";
import { useRetrieveSteps } from "@/hooks/useRetrieveSteps";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { useRetrieveOrders } from "@/hooks/useRetrieveOrders";
import { useRetrieveWorkOrders } from "@/hooks/useRetrieveWorkOrders";
import { useRetrieveEquipments } from "@/hooks/useRetrieveEquipments";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { useRetrieveErrorTypes } from "@/hooks/useRetrieveErrorTypes";
import { useRetrieveQuarantineDispositions } from "@/hooks/useRetrieveQuarantineDispositions";
import { useListCapas } from "@/hooks/useListCapas";
import { useRetrieveThreeDModels } from "@/hooks/useRetrieveThreeDModels";
import { useRetrieveDocument } from "@/hooks/useRetrieveDocument";
import { useCreateDocument } from "@/hooks/useCreateDocument";
import { useParams } from "@tanstack/react-router";
import { schemas } from "@/lib/api/generated";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { useUpdateDocument } from "@/hooks/useUpdateDocument";
import { useRetrieveContentTypes } from "@/hooks/useRetrieveContentTypes";
import { useRetrieveDocumentTypes } from "@/hooks/useRetrieveDocumentTypes";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { isFieldRequired } from "@/lib/zod-config";

const DOCUMENT_CLASSIFICATION = schemas.ClassificationEnum.options;

// Create form schema dynamically based on mode
const createFormSchema = (mode: "create" | "edit") => z.object({
    file: mode === "edit"
        ? z.any().optional()
        : z
            .any()
            .refine(
                (file) => file instanceof File || (Array.isArray(file) && file.length > 0),
                "A file is required - please select a document to upload (PDF, DOCX, or image up to 10MB)"
            ),
    classification: z
        .string()
        .min(1, "Classification level is required - please select the security level for this document"),
    document_type: z.string().nullable().optional(),
    content_type: z.string().optional(),
    object_id: z.string().optional(),
    ai_readable: z.boolean().optional(),
});

type FormValues = z.infer<ReturnType<typeof createFormSchema>>;

// Required field detection for create mode (file required)
const createModeSchema = createFormSchema("create");
const required = {
    classification: isFieldRequired(createModeSchema.shape.classification),
};

// Document Preview Component
function DocumentPreviewCard({ document }: { document: any }) {
    const isImage = document.is_image;
    const isPdf = document.file_name?.toLowerCase().endsWith('.pdf');

    // Build preview URL
    const fileUrl = document.file ?
        (document.file.startsWith('http') ? document.file : `/media/${document.file}`) :
        null;

    return (
        <Card className="mb-6">
            <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                    <Eye className="h-5 w-5" />
                    Current File Preview
                </CardTitle>
            </CardHeader>
            <CardContent>
                {isImage && fileUrl ? (
                    <div className="flex justify-center">
                        <img
                            src={fileUrl}
                            alt={document.file_name}
                            className="max-h-[300px] object-contain rounded-lg border"
                        />
                    </div>
                ) : isPdf && fileUrl ? (
                    <div className="border rounded-lg overflow-hidden">
                        <iframe
                            src={fileUrl}
                            className="w-full h-[400px]"
                            title={document.file_name}
                        />
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                        <FileType className="h-12 w-12 mb-3" />
                        <p className="text-base font-medium">{document.file_name}</p>
                        <p className="text-sm mb-3">Preview not available for this file type</p>
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => window.open(`/api/Documents/${document.id}/download/`, '_blank')}
                        >
                            <Download className="h-4 w-4 mr-2" />
                            Download to View
                        </Button>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

export default function DocumentFormPage() {
    const navigate = useNavigate();
    const [files, setFiles] = useState<File[] | null>(null);
    const [contentTypeSearch, setContentTypeSearch] = useState("");
    const [objectSearch, setObjectSearch] = useState("");
    const [rawObjectSearch, setRawObjectSearch] = useState("");
    const [documentTypeSearch, setDocumentTypeSearch] = useState("");

    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const documentId = params.id;

    const { data: document, isLoading: isLoadingDocument } = useRetrieveDocument(documentId);
    const { data: contentTypesRaw } = useRetrieveContentTypes({});
    const { data: documentTypesData } = useRetrieveDocumentTypes({ search: documentTypeSearch });
    const createDocument = useCreateDocument();
    const updateDocument = useUpdateDocument();

    // Check if document is approved/released (file changes not allowed)
    const isFileLocked = mode === "edit" && document?.status && (
        document.status === schemas.DocumentsStatusEnum.enum.APPROVED ||
        document.status === schemas.DocumentsStatusEnum.enum.RELEASED
    );

    // Normalize content types - filter to models that have GenericRelation to Documents
    const contentTypesData = Array.isArray(contentTypesRaw) ? contentTypesRaw : contentTypesRaw?.results || [];
    const validDocumentModels = [
        'parttype', 'parts', 'orders', 'workorder', 'processes', 'steps',  // MES
        'equipment', 'companies',  // Core
        'errortype', 'qualityreports', 'quarantinedisposition', 'capa', 'threedmodel',  // QMS
    ];
    const contentTypeOptions = contentTypesData.filter(ct => {
        const appLabelMatch = ct.app_label?.toLowerCase() === 'tracker';
        const modelMatch = validDocumentModels.includes(ct.model?.toLowerCase());
        return appLabelMatch && modelMatch;
    }) || [];

    // Document types
    const documentTypes = documentTypesData?.results || [];

    const form = useForm<FormValues>({
        resolver: zodResolver(createFormSchema(mode)),
        defaultValues: {
            file: undefined,
            classification: "",
            document_type: null,
            content_type: undefined,
            object_id: undefined,
            ai_readable: false,
        },
    });

    useEffect(() => {
        if (mode === "edit" && document) {
            form.setValue("classification", document.classification ?? "");
            form.setValue("ai_readable", document.ai_readable ?? false);
            form.setValue("document_type", document.document_type ?? null);

            if (document.content_type != null) {
                form.setValue("content_type", document.content_type);
            }
            if (document.object_id != null) {
                form.setValue("object_id", document.object_id);
            }
        }
    }, [mode, document, form]);

    const selectedContentType = form.watch("content_type");
    const selectedContentTypeModel = contentTypeOptions.find(ct => ct.id === selectedContentType)?.model;

    // Object search queries - MES models
    const { data: parts } = useRetrieveParts({ search: objectSearch }, { enabled: selectedContentTypeModel === "parts" });
    const { data: partTypes } = useRetrievePartTypes({ search: objectSearch }, { enabled: selectedContentTypeModel === "parttype" });
    const { data: orders } = useRetrieveOrders({ search: objectSearch }, { enabled: selectedContentTypeModel === "orders" });
    const { data: workOrders } = useRetrieveWorkOrders({ search: objectSearch }, { enabled: selectedContentTypeModel === "workorder" });
    const { data: processes } = useRetrieveProcesses({ search: objectSearch }, { enabled: selectedContentTypeModel === "processes" });
    const { data: steps } = useRetrieveSteps({ search: objectSearch }, { enabled: selectedContentTypeModel === "steps" });
    // Core models
    const { data: equipment } = useRetrieveEquipments({ search: objectSearch }, { enabled: selectedContentTypeModel === "equipment" });
    const { data: companies } = useRetrieveCompanies({ search: objectSearch }, { enabled: selectedContentTypeModel === "companies" });
    // QMS models
    const { data: errorTypes } = useRetrieveErrorTypes({ search: objectSearch }, { enabled: selectedContentTypeModel === "errortype" });
    const { data: dispositions } = useRetrieveQuarantineDispositions({ search: objectSearch }, { enabled: selectedContentTypeModel === "quarantinedisposition" });
    const { data: capas } = useListCapas({ search: objectSearch }, { enabled: selectedContentTypeModel === "capa" });
    const { data: threeDModels } = useRetrieveThreeDModels({ search: objectSearch }, { enabled: selectedContentTypeModel === "threedmodel" });

    // Map content type model to results
    const getObjectsForModel = (model: string | undefined) => {
        switch (model) {
            case "parts": return parts?.results;
            case "parttype": return partTypes?.results;
            case "orders": return orders?.results;
            case "workorder": return workOrders?.results;
            case "processes": return processes?.results;
            case "steps": return steps?.results;
            case "equipment": return equipment?.results;
            case "companies": return companies?.results;
            case "errortype": return errorTypes?.results;
            case "quarantinedisposition": return dispositions?.results;
            case "capa": return capas?.results;
            case "threedmodel": return threeDModels?.results;
            default: return [];
        }
    };

    const objects = getObjectsForModel(selectedContentTypeModel);

    // Debounce object search
    useEffect(() => {
        const timeout = setTimeout(() => {
            setObjectSearch(rawObjectSearch);
        }, 300);
        return () => clearTimeout(timeout);
    }, [rawObjectSearch]);

    async function onSubmit(values: FormValues) {
        try {
            if (mode === "create" && (!values.file || !(values.file instanceof File))) {
                toast.error("Please select a valid file to upload");
                return;
            }

            const payload: any = {
                classification: values.classification,
                ai_readable: values.ai_readable ?? false,
                ...(values.document_type && { document_type: values.document_type }),
                ...(values.content_type && { content_type: values.content_type }),
                ...(values.object_id && { object_id: values.object_id }),
            };

            if (values.file && values.file instanceof File) {
                payload.file = values.file;
                payload.file_name = values.file.name;
            }

            if (mode === "edit" && documentId) {
                await updateDocument.mutateAsync({ id: documentId, data: payload });
                toast.success("Document updated successfully!");
                navigate({ to: "/documents/$id", params: { id: String(documentId) } });
            } else {
                const result = await createDocument.mutateAsync(payload);
                toast.success("Document created successfully!");
                if (result?.id) {
                    navigate({ to: "/documents/$id", params: { id: String(result.id) } });
                } else {
                    navigate({ to: "/documents/list" });
                }
            }
        } catch (error) {
            console.error("Form submission error", error);
            toast.error("Failed to submit the form. Please try again.");
        }
    }

    // Helper to get friendly label for content type
    const getContentTypeLabel = (model: string) => {
        const labels: Record<string, string> = {
            // MES
            'parttype': 'Part Type',
            'parts': 'Part',
            'orders': 'Order',
            'workorder': 'Work Order',
            'processes': 'Process',
            'steps': 'Step',
            // Core
            'equipment': 'Equipment',
            'companies': 'Company',
            // QMS
            'errortype': 'Error Type',
            'qualityreports': 'Quality Report',
            'quarantinedisposition': 'Disposition',
            'capa': 'CAPA',
            'threedmodel': '3D Model',
        };
        return labels[model] || model;
    };

    // Helper to get display name for an object based on its content type
    const getObjectDisplayName = (obj: any, model: string | undefined) => {
        switch (model) {
            case "steps":
                return `${obj.name} (${obj.process_name || 'No process'})`;
            case "capa":
                return `${obj.capa_number} - ${obj.title}`;
            case "equipment":
                return obj.name || obj.serial_number || `#${obj.id}`;
            case "companies":
                return obj.name || `#${obj.id}`;
            case "errortype":
                return obj.name || `#${obj.id}`;
            case "quarantinedisposition":
                return obj.disposition_number || `Disposition #${obj.id}`;
            case "threedmodel":
                return obj.name || `Model #${obj.id}`;
            default:
                return obj.ERP_id || obj.name || obj.erp_id || `#${obj.id}`;
        }
    };

    // Show loading state for edit mode
    if (mode === "edit" && isLoadingDocument) {
        return (
            <div className="max-w-3xl mx-auto py-10">
                <div className="flex items-center justify-center">
                    <Loader2 className="h-8 w-8 animate-spin" />
                    <span className="ml-2">Loading document...</span>
                </div>
            </div>
        );
    }

    return (
        <Form {...form}>
            <div className="max-w-3xl mx-auto py-10">
                <h1 className="text-3xl font-bold tracking-tight mb-2">
                    {mode === "edit" ? "Edit Document" : "Upload Document"}
                </h1>
                {mode === "edit" && document && (
                    <p className="text-muted-foreground mb-6">
                        Editing: {document.file_name} (v{document.version || 1})
                    </p>
                )}

                {/* Document Preview - Edit Mode Only */}
                {mode === "edit" && document && (
                    <DocumentPreviewCard document={document} />
                )}

                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    {/* File Upload */}
                    <FormField
                        control={form.control}
                        name="file"
                        render={() => (
                            <FormItem>
                                <FormLabel required={mode === "create"}>Document File</FormLabel>
                                {isFileLocked ? (
                                    <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
                                        <p className="text-sm text-yellow-800">
                                            <strong>File locked:</strong> This document has been approved/released.
                                            To change the file, create a new revision from the document detail page.
                                        </p>
                                        {document?.file_name && (
                                            <p className="mt-2 text-sm text-yellow-700">
                                                Current file: <span className="font-medium">{document.file_name}</span>
                                            </p>
                                        )}
                                    </div>
                                ) : (
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
                                            dropzoneOptions={{ maxFiles: 1, maxSize: 1024 * 1024 * 10 }}
                                            className="relative bg-background rounded-lg p-2"
                                        >
                                            <FileInput
                                                id="fileInput"
                                                className="outline-dashed outline-1 outline-slate-500"
                                            >
                                                <div className="flex items-center justify-center flex-col p-8 w-full">
                                                    <CloudUpload className="text-gray-500 w-10 h-10" />
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
                                                        <Paperclip className="h-4 w-4 stroke-current" />
                                                        <span>{file.name}</span>
                                                    </FileUploaderItem>
                                                ))}
                                            </FileUploaderContent>
                                        </FileUploader>
                                    </FormControl>
                                )}
                                {!isFileLocked && mode === "edit" && document?.file_name && (
                                    <p className="text-sm text-muted-foreground">
                                        Current file: {document.file_name}
                                    </p>
                                )}
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Document Type */}
                    <FormField
                        control={form.control}
                        name="document_type"
                        render={({ field }) => {
                            const selected = documentTypes.find((dt: { id: string }) => dt.id === field.value);
                            return (
                                <FormItem>
                                    <FormLabel>Document Type</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    className={cn("w-full justify-between", !field.value && "text-muted-foreground")}
                                                >
                                                    {selected ? `${selected.name} (${selected.code})` : "Select document type"}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-[400px] p-0">
                                            <Command shouldFilter={false}>
                                                <CommandInput
                                                    value={documentTypeSearch}
                                                    onValueChange={setDocumentTypeSearch}
                                                    placeholder="Search document types..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No document types found.</CommandEmpty>
                                                    <CommandGroup>
                                                        <CommandItem
                                                            value="none"
                                                            onSelect={() => {
                                                                form.setValue("document_type", null);
                                                                setDocumentTypeSearch("");
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
                                                        {documentTypes.map((dt: { id: string }) => (
                                                            <CommandItem
                                                                key={dt.id}
                                                                value={dt.id.toString()}
                                                                onSelect={() => {
                                                                    form.setValue("document_type", dt.id);
                                                                    setDocumentTypeSearch("");
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn(
                                                                        "mr-2 h-4 w-4",
                                                                        dt.id === field.value ? "opacity-100" : "opacity-0"
                                                                    )}
                                                                />
                                                                <div>
                                                                    <span className="font-medium">{dt.name}</span>
                                                                    <span className="text-muted-foreground ml-2">({dt.code})</span>
                                                                </div>
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                    <FormDescription>
                                        Categorize this document (e.g., SOP, Work Instruction, Drawing)
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            );
                        }}
                    />

                    {/* Classification */}
                    <FormField
                        control={form.control}
                        name="classification"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.classification}>Classification Level</FormLabel>
                                <Select
                                    value={field.value}
                                    onValueChange={field.onChange}
                                >
                                    <FormControl>
                                        <SelectTrigger className="w-full">
                                            <SelectValue placeholder="Select classification level" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        {DOCUMENT_CLASSIFICATION.map((level) => (
                                            <SelectItem key={level} value={level}>
                                                {level.charAt(0).toUpperCase() + level.slice(1).toLowerCase()}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <FormDescription>
                                    Security level determines who can access this document
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Link To - Content Type */}
                    <FormField
                        control={form.control}
                        name="content_type"
                        render={({ field }) => {
                            const selected = contentTypeOptions.find((opt) => opt.id === field.value);
                            return (
                                <FormItem>
                                    <FormLabel>Link To (Optional)</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    className={cn("w-full justify-between", !field.value && "text-muted-foreground")}
                                                >
                                                    {selected ? getContentTypeLabel(selected.model) : "Select object type"}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-[400px] p-0">
                                            <Command>
                                                <CommandInput
                                                    value={contentTypeSearch}
                                                    onValueChange={setContentTypeSearch}
                                                    placeholder="Search..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No options found.</CommandEmpty>
                                                    <CommandGroup>
                                                        <CommandItem
                                                            value="none"
                                                            onSelect={() => {
                                                                form.setValue("content_type", undefined);
                                                                form.setValue("object_id", undefined);
                                                                setContentTypeSearch("");
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn(
                                                                    "mr-2 h-4 w-4",
                                                                    !field.value ? "opacity-100" : "opacity-0"
                                                                )}
                                                            />
                                                            None (standalone document)
                                                        </CommandItem>
                                                        {contentTypeOptions.map((opt) => (
                                                            <CommandItem
                                                                key={opt.id}
                                                                value={getContentTypeLabel(opt.model)}
                                                                onSelect={() => {
                                                                    form.setValue("content_type", opt.id);
                                                                    form.setValue("object_id", undefined);
                                                                    setContentTypeSearch("");
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn(
                                                                        "mr-2 h-4 w-4",
                                                                        opt.id === field.value ? "opacity-100" : "opacity-0"
                                                                    )}
                                                                />
                                                                {getContentTypeLabel(opt.model)}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                    <FormDescription>
                                        Attach this document to a specific record
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            );
                        }}
                    />

                    {/* Link To - Object ID */}
                    {selectedContentType && (
                        <FormField
                            control={form.control}
                            name="object_id"
                            render={({ field }) => {
                                const selected = objects?.find((obj: { id: string | number }) => obj.id === field.value);
                                return (
                                    <FormItem>
                                        <FormLabel>Select {getContentTypeLabel(selectedContentTypeModel || "")}</FormLabel>
                                        <Popover>
                                            <PopoverTrigger asChild>
                                                <FormControl>
                                                    <Button
                                                        variant="outline"
                                                        role="combobox"
                                                        className={cn("w-full justify-between", !field.value && "text-muted-foreground")}
                                                    >
                                                        {selected
                                                            ? getObjectDisplayName(selected, selectedContentTypeModel)
                                                            : "Select record"}
                                                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                    </Button>
                                                </FormControl>
                                            </PopoverTrigger>
                                            <PopoverContent className="w-[400px] p-0">
                                                <Command shouldFilter={false}>
                                                    <CommandInput
                                                        value={rawObjectSearch}
                                                        onValueChange={setRawObjectSearch}
                                                        placeholder="Search..."
                                                    />
                                                    <CommandList>
                                                        <CommandEmpty>No items found.</CommandEmpty>
                                                        <CommandGroup>
                                                            {objects?.map((obj: { id: string | number }) => (
                                                                <CommandItem
                                                                    key={obj.id}
                                                                    value={obj.id.toString()}
                                                                    onSelect={() => {
                                                                        form.setValue("object_id", obj.id);
                                                                        setRawObjectSearch("");
                                                                    }}
                                                                >
                                                                    <Check
                                                                        className={cn(
                                                                            "mr-2 h-4 w-4",
                                                                            obj.id === field.value ? "opacity-100" : "opacity-0"
                                                                        )}
                                                                    />
                                                                    {getObjectDisplayName(obj, selectedContentTypeModel)}
                                                                </CommandItem>
                                                            ))}
                                                        </CommandGroup>
                                                    </CommandList>
                                                </Command>
                                            </PopoverContent>
                                        </Popover>
                                        <FormMessage />
                                    </FormItem>
                                );
                            }}
                        />
                    )}

                    {/* AI Readable */}
                    <FormField
                        control={form.control}
                        name="ai_readable"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                <FormControl>
                                    <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel>AI Readable</FormLabel>
                                    <FormDescription>
                                        Allow AI systems to read and analyze this document for search and recommendations
                                    </FormDescription>
                                </div>
                            </FormItem>
                        )}
                    />

                    {/* Submit Button */}
                    <div className="flex gap-4">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => navigate({ to: "/documents/list" })}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            disabled={createDocument.isPending || updateDocument.isPending}
                        >
                            {createDocument.isPending || updateDocument.isPending ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    {mode === "edit" ? "Saving..." : "Uploading..."}
                                </>
                            ) : (
                                mode === "edit" ? "Save Changes" : "Upload Document"
                            )}
                        </Button>
                    </div>
                </form>
            </div>
        </Form>
    );
}
