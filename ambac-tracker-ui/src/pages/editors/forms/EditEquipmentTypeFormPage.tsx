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
import { useParams } from "@tanstack/react-router";

import { useRetrieveEquipmentType } from "@/hooks/useRetrieveEquipmentType";
import { useCreateEquipmentType } from "@/hooks/useCreateEquipmentType";
import { useUpdateEquipmentType } from "@/hooks/useUpdateEquipmentType";

const formSchema = z.object({
    name: z.string().min(1, "Name is required"),
});

export default function EquipmentTypeFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const equipmentTypeId = params.id ? parseInt(params.id, 10) : undefined;

    const { data: equipmentType } = useRetrieveEquipmentType(
        { params: { id: equipmentTypeId! } },
        { enabled: mode === "edit" && !!equipmentTypeId }
    );

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
        },
    });

    useEffect(() => {
        if (mode === "edit" && equipmentType) {
            form.reset({
                name: equipmentType.name ?? "",
            });
        }
    }, [mode, equipmentType, form]);

    const createEquipmentType = useCreateEquipmentType();
    const updateEquipmentType = useUpdateEquipmentType();

    function onSubmit(values: z.infer<typeof formSchema>) {
        if (mode === "edit" && equipmentTypeId) {
            updateEquipmentType.mutate(
                { id: equipmentTypeId, data: values },
                {
                    onSuccess: () => toast.success("Equipment type updated successfully!"),
                    onError: (err) => {
                        console.error("Update failed:", err);
                        toast.error("Failed to update equipment type.");
                    },
                }
            );
        } else {
            createEquipmentType.mutate(values, {
                onSuccess: () => {
                    toast.success("Equipment type created successfully!");
                    form.reset();
                },
                onError: (err) => {
                    console.error("Creation failed:", err);
                    toast.error("Failed to create equipment type.");
                },
            });
        }
    }

    return (
        <Form {...form}>
            <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-8 max-w-3xl mx-auto py-10"
            >
                <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Name</FormLabel>
                            <FormControl>
                                <Input placeholder="e.g. CNC Lathe, CMM, Robot Arm" {...field} />
                            </FormControl>
                            <FormDescription>The category or type of equipment</FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <Button
                    type="submit"
                    disabled={createEquipmentType.isPending || updateEquipmentType.isPending}
                >
                    {mode === "edit"
                        ? updateEquipmentType.isPending
                            ? "Saving..."
                            : "Save Changes"
                        : createEquipmentType.isPending
                            ? "Creating..."
                            : "Create Equipment Type"}
                </Button>
            </form>
        </Form>
    );
}
