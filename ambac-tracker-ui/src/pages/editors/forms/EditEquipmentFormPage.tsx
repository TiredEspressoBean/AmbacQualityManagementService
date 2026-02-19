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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { useParams } from "@tanstack/react-router";

import { useRetrieveEquipment } from "@/hooks/useRetrieveEquipment";
import { useCreateEquipment } from "@/hooks/useCreateEquipment";
import { useUpdateEquipment } from "@/hooks/useUpdateEquipment";
import { useRetrieveEquipmentTypes } from "@/hooks/useRetrieveEquipmentTypes";
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
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";

const EQUIPMENT_STATUS_OPTIONS = schemas.EquipmentsStatusEnum.options;

// Use generated schema - error messages handled by global error map
const formSchema = schemas.EquipmentsRequest.pick({
    name: true,
    equipment_type: true,
    serial_number: true,
    manufacturer: true,
    model_number: true,
    location: true,
    status: true,
    notes: true,
});

type FormValues = z.infer<typeof formSchema>;

// Pre-compute required fields for labels
const required = {
    name: isFieldRequired(formSchema.shape.name),
    equipment_type: isFieldRequired(formSchema.shape.equipment_type),
    serial_number: isFieldRequired(formSchema.shape.serial_number),
    manufacturer: isFieldRequired(formSchema.shape.manufacturer),
    model_number: isFieldRequired(formSchema.shape.model_number),
    location: isFieldRequired(formSchema.shape.location),
    status: isFieldRequired(formSchema.shape.status),
    notes: isFieldRequired(formSchema.shape.notes),
};

export default function EquipmentFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const equipmentId = params.id;
    const [equipmentTypeSearch, setEquipmentTypeSearch] = useState("");
    const [open, setOpen] = useState(false);

    const { data: equipment, isLoading: isLoadingEquipment } = useRetrieveEquipment(
        { params: { id: equipmentId! } },
        { enabled: mode === "edit" && !!equipmentId }
    );

    const { data: equipmentTypes, isLoading: isLoadingEquipmentTypes } = useRetrieveEquipmentTypes({
        search: equipmentTypeSearch,
    });

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            equipment_type: undefined,
            serial_number: "",
            manufacturer: "",
            model_number: "",
            location: "",
            status: undefined,
            notes: "",
        },
    });

    // Reset form when equipment data loads
    useEffect(() => {
        if (mode === "edit" && equipment) {
            form.reset({
                name: equipment.name ?? "",
                equipment_type: equipment.equipment_type ?? undefined,
                serial_number: equipment.serial_number ?? "",
                manufacturer: equipment.manufacturer ?? "",
                model_number: equipment.model_number ?? "",
                location: equipment.location ?? "",
                status: equipment.status ?? undefined,
                notes: equipment.notes ?? "",
            });
        }
    }, [mode, equipment, form]);

    const createEquipment = useCreateEquipment();
    const updateEquipment = useUpdateEquipment();

    function onSubmit(values: FormValues) {
        const submitData = {
            name: values.name,
            equipment_type: values.equipment_type || null,
            serial_number: values.serial_number || undefined,
            manufacturer: values.manufacturer || undefined,
            model_number: values.model_number || undefined,
            location: values.location || undefined,
            status: values.status || undefined,
            notes: values.notes || undefined,
        };

        if (mode === "edit" && equipmentId) {
            updateEquipment.mutate(
                { id: equipmentId, data: submitData },
                {
                    onSuccess: () => {
                        toast.success("Equipment updated successfully!");
                    },
                    onError: (err) => {
                        console.error("Update failed:", err);
                        toast.error("Failed to update equipment.");
                    },
                }
            );
        } else {
            createEquipment.mutate(submitData, {
                onSuccess: () => {
                    toast.success("Equipment created successfully!");
                    form.reset();
                },
                onError: (err) => {
                    console.error("Creation failed:", err);
                    toast.error("Failed to create equipment.");
                },
            });
        }
    }

    // Show loading state
    if (mode === "edit" && isLoadingEquipment) {
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

    const selectedEquipmentType = equipmentTypes?.results.find((et) => et.id === form.watch("equipment_type"));

    return (
        <div className="max-w-3xl mx-auto py-10">
            <div className="mb-8">
                <h1 className="text-3xl font-bold">
                    {mode === "edit" ? "Edit Equipment" : "Create Equipment"}
                </h1>
                <p className="text-muted-foreground">
                    {mode === "edit"
                        ? "Update the equipment information below"
                        : "Add a new piece of equipment to the system"
                    }
                </p>
            </div>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    <FormField
                        control={form.control}
                        name="name"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.name}>Equipment Name</FormLabel>
                                <FormControl>
                                    <Input
                                        placeholder="e.g. CNC Machine #1, Inspection Station A"
                                        {...field}
                                    />
                                </FormControl>
                                <FormDescription>
                                    A descriptive name for this piece of equipment
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="equipment_type"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel required={required.equipment_type}>Equipment Type</FormLabel>
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
                                                disabled={isLoadingEquipmentTypes}
                                            >
                                                {isLoadingEquipmentTypes
                                                    ? "Loading..."
                                                    : selectedEquipmentType
                                                        ? selectedEquipmentType.name
                                                        : "Select an equipment type (optional)"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-full p-0" align="start">
                                        <Command>
                                            <CommandInput
                                                value={equipmentTypeSearch}
                                                onValueChange={setEquipmentTypeSearch}
                                                placeholder="Search equipment types..."
                                            />
                                            <CommandList>
                                                <CommandEmpty>No equipment types found.</CommandEmpty>
                                                <CommandGroup>
                                                    <CommandItem
                                                        onSelect={() => {
                                                            form.setValue("equipment_type", undefined);
                                                            setOpen(false);
                                                        }}
                                                    >
                                                        <Check
                                                            className={cn(
                                                                "mr-2 h-4 w-4",
                                                                !field.value ? "opacity-100" : "opacity-0"
                                                            )}
                                                        />
                                                        No specific equipment type
                                                    </CommandItem>

                                                    {equipmentTypes?.results.map((et) => (
                                                        <CommandItem
                                                            key={et.id}
                                                            value={et.name}
                                                            onSelect={() => {
                                                                form.setValue("equipment_type", et.id);
                                                                setOpen(false);
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn(
                                                                    "mr-2 h-4 w-4",
                                                                    et.id === field.value ? "opacity-100" : "opacity-0"
                                                                )}
                                                            />
                                                            {et.name}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>
                                    Categorize this equipment by type, or leave blank for general equipment
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <FormField
                            control={form.control}
                            name="serial_number"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel required={required.serial_number}>Serial Number</FormLabel>
                                    <FormControl>
                                        <Input placeholder="e.g. SN-2024-001" {...field} value={field.value ?? ""} />
                                    </FormControl>
                                    <FormDescription>
                                        Unique serial number for this equipment
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="manufacturer"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel required={required.manufacturer}>Manufacturer</FormLabel>
                                    <FormControl>
                                        <Input placeholder="e.g. Haas, Fanuc, Keyence" {...field} value={field.value ?? ""} />
                                    </FormControl>
                                    <FormDescription>
                                        Equipment manufacturer
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="model_number"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel required={required.model_number}>Model Number</FormLabel>
                                    <FormControl>
                                        <Input placeholder="e.g. VF-2, M-20iA" {...field} value={field.value ?? ""} />
                                    </FormControl>
                                    <FormDescription>
                                        Model or part number
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="location"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel required={required.location}>Location</FormLabel>
                                    <FormControl>
                                        <Input placeholder="e.g. Building A, Bay 3" {...field} value={field.value ?? ""} />
                                    </FormControl>
                                    <FormDescription>
                                        Physical location of the equipment
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    <FormField
                        control={form.control}
                        name="status"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.status}>Status</FormLabel>
                                <Select
                                    value={field.value || ""}
                                    onValueChange={(value) => field.onChange(value || undefined)}
                                >
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select equipment status" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        {EQUIPMENT_STATUS_OPTIONS.map((status) => (
                                            <SelectItem key={status} value={status}>
                                                {status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <FormDescription>
                                    Current operational status of the equipment
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="notes"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.notes}>Notes</FormLabel>
                                <FormControl>
                                    <Textarea
                                        placeholder="Additional notes about this equipment (calibration info, maintenance history, etc.)"
                                        className="min-h-[100px]"
                                        {...field}
                                        value={field.value ?? ""}
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className="flex gap-4">
                        <Button
                            type="submit"
                            disabled={createEquipment.isPending || updateEquipment.isPending}
                            className="flex-1"
                        >
                            {mode === "edit"
                                ? updateEquipment.isPending
                                    ? "Saving..."
                                    : "Save Changes"
                                : createEquipment.isPending
                                    ? "Creating..."
                                    : "Create Equipment"}
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    );
}