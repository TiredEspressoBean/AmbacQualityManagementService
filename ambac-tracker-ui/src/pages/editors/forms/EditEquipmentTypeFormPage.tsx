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

import { useRetrieveEquipmentType } from "@/hooks/useRetrieveEquipmentType";
import { useCreateEquipmentType } from "@/hooks/useCreateEquipmentType";
import { useUpdateEquipmentType } from "@/hooks/useUpdateEquipmentType";
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";

// Use generated schema, pick relevant fields and extend with custom error messages
const formSchema = schemas.EquipmentTypeRequest.pick({
    name: true,
    description: true,
    requires_calibration: true,
    default_calibration_interval_days: true,
    is_portable: true,
    track_downtime: true,
}).extend({
    // Override with custom error messages
    name: z.string()
        .min(1, "Equipment type name is required")
        .max(50, "Name must be 50 characters or less"),
});

type FormValues = z.infer<typeof formSchema>;

const required = {
    name: isFieldRequired(formSchema.shape.name),
};

export default function EquipmentTypeFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const equipmentTypeId = params.id;

    const { data: equipmentType } = useRetrieveEquipmentType(
        { params: { id: equipmentTypeId! } },
        { enabled: mode === "edit" && !!equipmentTypeId }
    );

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            description: "",
            requires_calibration: false,
            default_calibration_interval_days: undefined,
            is_portable: false,
            track_downtime: false,
        },
    });

    useEffect(() => {
        if (mode === "edit" && equipmentType) {
            form.reset({
                name: equipmentType.name ?? "",
                description: equipmentType.description ?? "",
                requires_calibration: equipmentType.requires_calibration ?? false,
                default_calibration_interval_days: equipmentType.default_calibration_interval_days ?? undefined,
                is_portable: equipmentType.is_portable ?? false,
                track_downtime: equipmentType.track_downtime ?? false,
            });
        }
    }, [mode, equipmentType, form]);

    const createEquipmentType = useCreateEquipmentType();
    const updateEquipmentType = useUpdateEquipmentType();

    function onSubmit(values: FormValues) {
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

    const requiresCalibration = form.watch("requires_calibration");

    return (
        <Form {...form}>
            <div className="max-w-3xl mx-auto py-6">
                <h1 className="text-2xl font-semibold tracking-tight">
                    {mode === "edit" ? "Edit Equipment Type" : "Create Equipment Type"}
                </h1>
                <p className="text-muted-foreground text-sm mt-1">
                    Define a category of equipment used in your facility.
                </p>
            </div>
            <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-8 max-w-3xl mx-auto py-10"
            >
                <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel required={required.name}>Name</FormLabel>
                            <FormControl>
                                <Input placeholder="e.g. CNC Lathe, CMM, Robot Arm" {...field} />
                            </FormControl>
                            <FormDescription>The category or type of equipment</FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Description</FormLabel>
                            <FormControl>
                                <Textarea
                                    placeholder="Describe this equipment type, its typical uses, and any special considerations..."
                                    className="resize-none"
                                    {...field}
                                    value={field.value ?? ""}
                                />
                            </FormControl>
                            <FormDescription>Optional details about this equipment type</FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <div className="space-y-4">
                    <FormField
                        control={form.control}
                        name="requires_calibration"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                <FormControl>
                                    <Checkbox
                                        checked={field.value ?? false}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel>Requires Calibration</FormLabel>
                                    <FormDescription>
                                        Equipment of this type needs periodic calibration verification
                                    </FormDescription>
                                </div>
                            </FormItem>
                        )}
                    />

                    {requiresCalibration && (
                        <FormField
                            control={form.control}
                            name="default_calibration_interval_days"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Default Calibration Interval (days)</FormLabel>
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
                                        How often equipment of this type should be calibrated
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    )}
                </div>

                <FormField
                    control={form.control}
                    name="is_portable"
                    render={({ field }) => (
                        <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                            <FormControl>
                                <Checkbox
                                    checked={field.value ?? false}
                                    onCheckedChange={field.onChange}
                                />
                            </FormControl>
                            <div className="space-y-1 leading-none">
                                <FormLabel>Portable</FormLabel>
                                <FormDescription>
                                    Equipment of this type can be moved between locations
                                </FormDescription>
                            </div>
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="track_downtime"
                    render={({ field }) => (
                        <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                            <FormControl>
                                <Checkbox
                                    checked={field.value ?? false}
                                    onCheckedChange={field.onChange}
                                />
                            </FormControl>
                            <div className="space-y-1 leading-none">
                                <FormLabel>Track Downtime</FormLabel>
                                <FormDescription>
                                    Record and monitor downtime events for equipment of this type
                                </FormDescription>
                            </div>
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
