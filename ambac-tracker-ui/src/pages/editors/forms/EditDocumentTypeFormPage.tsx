"use client";

import { useEffect } from "react";
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
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { useParams } from "@tanstack/react-router";

import { useRetrieveDocumentType } from "@/hooks/useRetrieveDocumentType";
import { useCreateDocumentType } from "@/hooks/useCreateDocumentType";
import { useUpdateDocumentType } from "@/hooks/useUpdateDocumentType";
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";

// Use generated schema with custom regex for code field (frontend UX requirement)
const formSchema = schemas.DocumentTypeRequest.pick({
    name: true,
    code: true,
    description: true,
    requires_approval: true,
    default_review_period_days: true,
    default_retention_days: true,
}).extend({
    // Add uppercase regex validation for code (not enforced by backend)
    code: z.string()
        .min(1)
        .max(20)
        .regex(/^[A-Z0-9_-]+$/, "Code must be uppercase letters, numbers, hyphens, or underscores"),
});

type FormValues = z.infer<typeof formSchema>;

// Pre-compute required fields for labels
const required = {
    name: isFieldRequired(formSchema.shape.name),
    code: isFieldRequired(formSchema.shape.code),
    description: isFieldRequired(formSchema.shape.description),
    requires_approval: isFieldRequired(formSchema.shape.requires_approval),
    default_review_period_days: isFieldRequired(formSchema.shape.default_review_period_days),
    default_retention_days: isFieldRequired(formSchema.shape.default_retention_days),
};

export default function DocumentTypeFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const documentTypeId = params.id;

    const { data: documentType, isLoading: isLoadingDocumentType } = useRetrieveDocumentType(
        { params: { id: documentTypeId! } },
        { enabled: mode === "edit" && !!documentTypeId }
    );

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            code: "",
            description: "",
            requires_approval: true,
            default_review_period_days: undefined,
            default_retention_days: undefined,
        },
    });

    // Reset form when documentType data loads
    useEffect(() => {
        if (mode === "edit" && documentType) {
            form.reset({
                name: documentType.name || "",
                code: documentType.code || "",
                description: documentType.description || "",
                requires_approval: documentType.requires_approval ?? true,
                default_review_period_days: documentType.default_review_period_days ?? undefined,
                default_retention_days: documentType.default_retention_days ?? undefined,
            });
        }
    }, [mode, documentType, form]);

    const createDocumentType = useCreateDocumentType();
    const updateDocumentType = useUpdateDocumentType();

    function onSubmit(values: FormValues) {
        if (mode === "edit" && documentTypeId) {
            updateDocumentType.mutate(
                { id: documentTypeId, data: values },
                {
                    onSuccess: () => {
                        toast.success("Document type updated successfully!");
                    },
                    onError: (err) => {
                        console.error("Update failed:", err);
                        toast.error("Failed to update document type.");
                    },
                }
            );
        } else {
            createDocumentType.mutate(values, {
                onSuccess: () => {
                    toast.success("Document type created successfully!");
                    form.reset();
                },
                onError: (err) => {
                    console.error("Creation failed:", err);
                    toast.error("Failed to create document type.");
                },
            });
        }
    }

    if (mode === "edit" && isLoadingDocumentType) {
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
        <div className="max-w-3xl mx-auto py-10">
            <div className="mb-8">
                <h1 className="text-3xl font-bold">
                    {mode === "edit" ? "Edit Document Type" : "Create Document Type"}
                </h1>
                <p className="text-muted-foreground">
                    {mode === "edit"
                        ? "Update the document type configuration"
                        : "Define a new document type category (e.g., SOP, Work Instruction, Drawing)"}
                </p>
            </div>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    <FormField
                        control={form.control}
                        name="name"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.name}>Name</FormLabel>
                                <FormControl>
                                    <Input
                                        placeholder="e.g. Standard Operating Procedure"
                                        {...field}
                                    />
                                </FormControl>
                                <FormDescription>
                                    The full display name for this document type
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="code"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.code}>Code</FormLabel>
                                <FormControl>
                                    <Input
                                        placeholder="e.g. SOP, WI, DWG"
                                        {...field}
                                        onChange={(e) => field.onChange(e.target.value.toUpperCase())}
                                    />
                                </FormControl>
                                <FormDescription>
                                    Short code used in document IDs (uppercase, no spaces)
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="description"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.description}>Description</FormLabel>
                                <FormControl>
                                    <Textarea
                                        placeholder="Describe what this document type is used for..."
                                        className="min-h-[100px]"
                                        {...field}
                                        value={field.value ?? ""}
                                    />
                                </FormControl>
                                <FormDescription>
                                    Optional description to help users understand when to use this type
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className="grid grid-cols-2 gap-4">
                        <FormField
                            control={form.control}
                            name="default_review_period_days"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel required={required.default_review_period_days}>Review Period (days)</FormLabel>
                                    <FormControl>
                                        <Input
                                            type="number"
                                            placeholder="e.g. 365"
                                            {...field}
                                            value={field.value ?? ""}
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                field.onChange(val === "" ? undefined : parseInt(val, 10));
                                            }}
                                        />
                                    </FormControl>
                                    <FormDescription>
                                        Days between required reviews
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="default_retention_days"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel required={required.default_retention_days}>Retention Period (days)</FormLabel>
                                    <FormControl>
                                        <Input
                                            type="number"
                                            placeholder="e.g. 2555 (7 years)"
                                            {...field}
                                            value={field.value ?? ""}
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                field.onChange(val === "" ? undefined : parseInt(val, 10));
                                            }}
                                        />
                                    </FormControl>
                                    <FormDescription>
                                        How long to retain documents
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    <FormField
                        control={form.control}
                        name="requires_approval"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                <FormControl>
                                    <Checkbox
                                        checked={field.value ?? true}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel>Requires Approval</FormLabel>
                                    <FormDescription>
                                        Documents of this type must go through approval workflow before release
                                    </FormDescription>
                                </div>
                            </FormItem>
                        )}
                    />

                    <div className="flex gap-4">
                        <Button
                            type="submit"
                            disabled={createDocumentType.isPending || updateDocumentType.isPending}
                            className="flex-1"
                        >
                            {mode === "edit"
                                ? updateDocumentType.isPending
                                    ? "Saving..."
                                    : "Save Changes"
                                : createDocumentType.isPending
                                    ? "Creating..."
                                    : "Create Document Type"}
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    );
}
