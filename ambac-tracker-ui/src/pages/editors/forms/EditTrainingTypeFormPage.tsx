"use client";

import { useEffect } from "react";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useParams } from "@tanstack/react-router";

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

import { useRetrieveTrainingType } from "@/hooks/useRetrieveTrainingType";
import { useCreateTrainingType } from "@/hooks/useCreateTrainingType";
import { useUpdateTrainingType } from "@/hooks/useUpdateTrainingType";
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";

// Use generated schema
const formSchema = schemas.TrainingTypeRequest.pick({
    name: true,
    description: true,
    validity_period_days: true,
});

type FormValues = z.infer<typeof formSchema>;

// Pre-compute required fields
const required = {
    name: isFieldRequired(formSchema.shape.name),
    description: isFieldRequired(formSchema.shape.description),
    validity_period_days: isFieldRequired(formSchema.shape.validity_period_days),
};

export default function EditTrainingTypeFormPage() {
    const params = useParams({ strict: false });
    const navigate = useNavigate();
    const mode = params.id && params.id !== "new" ? "edit" : "create";
    const typeId = params.id !== "new" ? params.id : undefined;

    const { data: trainingType, isLoading: isLoadingType } = useRetrieveTrainingType(typeId || "");

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            description: "",
            validity_period_days: null,
        },
    });

    // Reset form when data loads
    useEffect(() => {
        if (mode === "edit" && trainingType) {
            form.reset({
                name: trainingType.name ?? "",
                description: trainingType.description ?? "",
                validity_period_days: trainingType.validity_period_days ?? null,
            });
        }
    }, [mode, trainingType, form]);

    const createType = useCreateTrainingType();
    const updateType = useUpdateTrainingType();

    function onSubmit(values: FormValues) {
        const submitData = {
            name: values.name,
            description: values.description || undefined,
            validity_period_days: values.validity_period_days || undefined,
        };

        if (mode === "edit" && typeId) {
            updateType.mutate(
                { params: { id: typeId }, ...submitData },
                {
                    onSuccess: () => {
                        toast.success("Training type updated successfully!");
                        navigate({ to: "/quality/training/types" });
                    },
                    onError: (err) => {
                        console.error("Update failed:", err);
                        toast.error("Failed to update training type.");
                    },
                }
            );
        } else {
            createType.mutate(submitData, {
                onSuccess: () => {
                    toast.success("Training type created successfully!");
                    navigate({ to: "/quality/training/types" });
                },
                onError: (err) => {
                    console.error("Creation failed:", err);
                    toast.error("Failed to create training type.");
                },
            });
        }
    }

    if (mode === "edit" && isLoadingType) {
        return <div className="container mx-auto p-6">Loading...</div>;
    }

    return (
        <div className="container mx-auto p-6 max-w-2xl">
            <h1 className="text-2xl font-bold mb-6">
                {mode === "edit" ? "Edit Training Type" : "New Training Type"}
            </h1>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    {/* Name */}
                    <FormField
                        control={form.control}
                        name="name"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Name {required.name && "*"}</FormLabel>
                                <FormControl>
                                    <Input placeholder="e.g., Blueprint Reading" {...field} />
                                </FormControl>
                                <FormDescription>
                                    Name of the training or qualification
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Description */}
                    <FormField
                        control={form.control}
                        name="description"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Description</FormLabel>
                                <FormControl>
                                    <Textarea
                                        placeholder="Describe what this training covers..."
                                        {...field}
                                        value={field.value ?? ""}
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Validity Period */}
                    <FormField
                        control={form.control}
                        name="validity_period_days"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Validity Period (Days)</FormLabel>
                                <FormControl>
                                    <Input
                                        type="number"
                                        placeholder="365"
                                        {...field}
                                        value={field.value ?? ""}
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            field.onChange(val ? parseInt(val, 10) : null);
                                        }}
                                    />
                                </FormControl>
                                <FormDescription>
                                    How many days the training is valid. Leave empty for training that never expires.
                                    Common values: 365 (1 year), 730 (2 years), 1095 (3 years).
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className="flex gap-4">
                        <Button
                            type="submit"
                            disabled={createType.isPending || updateType.isPending}
                        >
                            {createType.isPending || updateType.isPending
                                ? "Saving..."
                                : mode === "edit"
                                ? "Update Training Type"
                                : "Create Training Type"}
                        </Button>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => navigate({ to: "/quality/training/types" })}
                        >
                            Cancel
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    );
}
