"use client";

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
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { useParams } from "@tanstack/react-router";

import { useRetrieveErrorType } from "@/hooks/useRetrieveErrorType";
import { useCreateErrorType } from "@/hooks/useCreateErrorType";
import { useUpdateErrorType } from "@/hooks/useUpdateErrorType";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { Check, ChevronsUpDown } from "lucide-react";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";

// Use generated schema - error messages handled by global error map
const formSchema = schemas.QualityErrorsListRequest.pick({
    error_name: true,
    error_example: true,
    part_type: true,
    requires_3d_annotation: true,
}).extend({
    // Override part_type to be string (nullable and optional for flexible selection)
    part_type: z.string().nullable().optional(),
});

type FormValues = z.infer<typeof formSchema>;

// Pre-compute required fields for labels
const required = {
    error_name: isFieldRequired(formSchema.shape.error_name),
    error_example: isFieldRequired(formSchema.shape.error_example),
    part_type: isFieldRequired(formSchema.shape.part_type),
    requires_3d_annotation: isFieldRequired(formSchema.shape.requires_3d_annotation),
};

export default function ErrorTypeFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const errorTypeId = params.id;
    const [partTypeSearch, setPartTypeSearch] = useState("");
    const [open, setOpen] = useState(false);

    const { data: errorType, isLoading: isLoadingErrorType } = useRetrieveErrorType(
        { params: { id: errorTypeId! } },
        { enabled: mode === "edit" && !!errorTypeId }
    );

    const { data: partTypes, isLoading: isLoadingPartTypes } = useRetrievePartTypes({
        search: partTypeSearch,
    });

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            error_name: "",
            error_example: "",
            part_type: undefined,
            requires_3d_annotation: false,
        },
    });

    // Reset form when errorType data loads
    useEffect(() => {
        if (mode === "edit" && errorType) {
            form.reset({
                error_name: errorType.error_name || "",
                error_example: errorType.error_example || "",
                part_type: errorType.part_type ?? undefined,
                requires_3d_annotation: errorType.requires_3d_annotation ?? false,
            });
        }
    }, [mode, errorType, form]);

    const createErrorType = useCreateErrorType();
    const updateErrorType = useUpdateErrorType();

    function onSubmit(values: FormValues) {
        // Clean up the data before sending
        const submitData = {
            error_name: values.error_name,
            error_example: values.error_example,
            part_type: values.part_type || null, // Convert undefined to null
            requires_3d_annotation: values.requires_3d_annotation,
        };

        if (mode === "edit" && errorTypeId) {
            updateErrorType.mutate(
                { id: errorTypeId, data: submitData },
                {
                    onSuccess: () => {
                        toast.success("Error type updated successfully!");
                    },
                    onError: (err) => {
                        console.error("Update failed:", err);
                        toast.error("Failed to update error type.");
                    },
                }
            );
        } else {
            createErrorType.mutate(submitData, {
                onSuccess: () => {
                    toast.success("Error type created successfully!");
                    form.reset();
                },
                onError: (err) => {
                    console.error("Creation failed:", err);
                    toast.error("Failed to create error type.");
                },
            });
        }
    }

    // Show loading state
    if (mode === "edit" && isLoadingErrorType) {
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

    const selectedPartType = partTypes?.results.find((pt) => pt.id === form.watch("part_type"));

    return (
        <div className="max-w-3xl mx-auto py-10">
            <div className="mb-8">
                <h1 className="text-3xl font-bold">
                    {mode === "edit" ? "Edit Error Type" : "Create Error Type"}
                </h1>
                <p className="text-muted-foreground">
                    {mode === "edit"
                        ? "Update the error type information below"
                        : "Define a new quality error type that can occur during manufacturing"
                    }
                </p>
            </div>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    <FormField
                        control={form.control}
                        name="error_name"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.error_name}>Error Name</FormLabel>
                                <FormControl>
                                    <Input
                                        placeholder="e.g. Surface Crack, Dimensional Out of Tolerance"
                                        {...field}
                                    />
                                </FormControl>
                                <FormDescription>
                                    A concise name that describes the type of error
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="error_example"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.error_example}>Error Example</FormLabel>
                                <FormControl>
                                    <Textarea
                                        placeholder="Describe what this error looks like, how to identify it, when it typically occurs..."
                                        className="min-h-[100px]"
                                        {...field}
                                    />
                                </FormControl>
                                <FormDescription>
                                    Detailed description to help operators identify this error type
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="part_type"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel required={required.part_type}>Part Type</FormLabel>
                                <Popover open={open} onOpenChange={setOpen}>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                aria-expanded={open}
                                                className={cn(
                                                    "w-full justify-between",
                                                    !field.value && "text-muted-foreground"
                                                )}
                                                disabled={isLoadingPartTypes}
                                            >
                                                {isLoadingPartTypes
                                                    ? "Loading..."
                                                    : selectedPartType
                                                        ? selectedPartType.name
                                                        : "Select a part type (optional)"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-full p-0" align="start">
                                        <Command>
                                            <CommandInput
                                                value={partTypeSearch}
                                                onValueChange={setPartTypeSearch}
                                                placeholder="Search part types..."
                                            />
                                            <CommandList>
                                                <CommandEmpty>No part types found.</CommandEmpty>
                                                <CommandGroup>
                                                    {/* Option to clear selection */}
                                                    <CommandItem
                                                        onSelect={() => {
                                                            form.setValue("part_type", undefined);
                                                            setOpen(false);
                                                        }}
                                                    >
                                                        <Check
                                                            className={cn(
                                                                "mr-2 h-4 w-4",
                                                                !field.value ? "opacity-100" : "opacity-0"
                                                            )}
                                                        />
                                                        No specific part type
                                                    </CommandItem>

                                                    {partTypes?.results.map((pt) => (
                                                        <CommandItem
                                                            key={pt.id}
                                                            value={pt.name}
                                                            onSelect={() => {
                                                                form.setValue("part_type", pt.id);
                                                                setOpen(false);
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn(
                                                                    "mr-2 h-4 w-4",
                                                                    pt.id === field.value ? "opacity-100" : "opacity-0"
                                                                )}
                                                            />
                                                            {pt.name}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>
                                    Link this error to a specific part type, or leave blank for general errors
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="requires_3d_annotation"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                <FormControl>
                                    <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel>
                                        Requires 3D Annotation
                                    </FormLabel>
                                    <FormDescription>
                                        Enable this if defects of this type should be documented with 3D annotations on the part model
                                    </FormDescription>
                                </div>
                            </FormItem>
                        )}
                    />

                    <div className="flex gap-4">
                        <Button
                            type="submit"
                            disabled={createErrorType.isPending || updateErrorType.isPending}
                            className="flex-1"
                        >
                            {mode === "edit"
                                ? updateErrorType.isPending
                                    ? "Saving..."
                                    : "Save Changes"
                                : createErrorType.isPending
                                    ? "Creating..."
                                    : "Create Error Type"}
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    );
}