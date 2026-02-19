"use client";

import { useEffect, useState } from "react";
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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { CalendarIcon, Check, ChevronsUpDown } from "lucide-react";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command";
import { format } from "date-fns";

import { useRetrieveCalibrationRecord } from "@/hooks/useRetrieveCalibrationRecord";
import { useCreateCalibrationRecord } from "@/hooks/useCreateCalibrationRecord";
import { useUpdateCalibrationRecord } from "@/hooks/useUpdateCalibrationRecord";
import { useRetrieveEquipments } from "@/hooks/useRetrieveEquipments";
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";

// Get enum options from schemas
const RESULT_OPTIONS = schemas.ResultEnum.options;
const CALIBRATION_TYPE_OPTIONS = schemas.CalibrationTypeEnum.options;

// Use generated schema
const formSchema = schemas.CalibrationRecordRequest.pick({
    equipment: true,
    calibration_date: true,
    due_date: true,
    result: true,
    calibration_type: true,
    performed_by: true,
    external_lab: true,
    certificate_number: true,
    standards_used: true,
    as_found_in_tolerance: true,
    adjustments_made: true,
    notes: true,
});

type FormValues = z.infer<typeof formSchema>;

// Pre-compute required fields
const required = {
    equipment: isFieldRequired(formSchema.shape.equipment),
    calibration_date: isFieldRequired(formSchema.shape.calibration_date),
    due_date: isFieldRequired(formSchema.shape.due_date),
    result: isFieldRequired(formSchema.shape.result),
    calibration_type: isFieldRequired(formSchema.shape.calibration_type),
};

export default function EditCalibrationRecordFormPage() {
    const params = useParams({ strict: false });
    const navigate = useNavigate();
    const mode = params.id && params.id !== "new" ? "edit" : "create";
    const recordId = params.id !== "new" ? params.id : undefined;

    const [equipmentSearch, setEquipmentSearch] = useState("");
    const [equipmentOpen, setEquipmentOpen] = useState(false);

    const { data: record, isLoading: isLoadingRecord } = useRetrieveCalibrationRecord(recordId || "");

    const { data: equipmentData } = useRetrieveEquipments(
        { search: equipmentSearch },
    );
    const equipmentList = equipmentData?.results ?? [];

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            equipment: undefined,
            calibration_date: "",
            due_date: "",
            result: "pass",
            calibration_type: "scheduled",
            performed_by: "",
            external_lab: "",
            certificate_number: "",
            standards_used: "",
            as_found_in_tolerance: null,
            adjustments_made: false,
            notes: "",
        },
    });

    // Reset form when record data loads
    useEffect(() => {
        if (mode === "edit" && record) {
            form.reset({
                equipment: record.equipment ?? undefined,
                calibration_date: record.calibration_date ?? "",
                due_date: record.due_date ?? "",
                result: record.result ?? "pass",
                calibration_type: record.calibration_type ?? "scheduled",
                performed_by: record.performed_by ?? "",
                external_lab: record.external_lab ?? "",
                certificate_number: record.certificate_number ?? "",
                standards_used: record.standards_used ?? "",
                as_found_in_tolerance: record.as_found_in_tolerance ?? null,
                adjustments_made: record.adjustments_made ?? false,
                notes: record.notes ?? "",
            });
        }
    }, [mode, record, form]);

    const createRecord = useCreateCalibrationRecord();
    const updateRecord = useUpdateCalibrationRecord();

    function onSubmit(values: FormValues) {
        const submitData = {
            equipment: values.equipment,
            calibration_date: values.calibration_date,
            due_date: values.due_date,
            result: values.result || undefined,
            calibration_type: values.calibration_type || undefined,
            performed_by: values.performed_by || undefined,
            external_lab: values.external_lab || undefined,
            certificate_number: values.certificate_number || undefined,
            standards_used: values.standards_used || undefined,
            as_found_in_tolerance: values.as_found_in_tolerance,
            adjustments_made: values.adjustments_made,
            notes: values.notes || undefined,
        };

        if (mode === "edit" && recordId) {
            updateRecord.mutate(
                { params: { id: recordId }, ...submitData },
                {
                    onSuccess: () => {
                        toast.success("Calibration record updated successfully!");
                        navigate({ to: "/quality/calibrations/records" });
                    },
                    onError: (err) => {
                        console.error("Update failed:", err);
                        toast.error("Failed to update calibration record.");
                    },
                }
            );
        } else {
            createRecord.mutate(submitData, {
                onSuccess: () => {
                    toast.success("Calibration record created successfully!");
                    navigate({ to: "/quality/calibrations/records" });
                },
                onError: (err) => {
                    console.error("Creation failed:", err);
                    toast.error("Failed to create calibration record.");
                },
            });
        }
    }

    if (mode === "edit" && isLoadingRecord) {
        return <div className="container mx-auto p-6">Loading...</div>;
    }

    return (
        <div className="container mx-auto p-6 max-w-2xl">
            <h1 className="text-2xl font-bold mb-6">
                {mode === "edit" ? "Edit Calibration Record" : "New Calibration Record"}
            </h1>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    {/* Equipment */}
                    <FormField
                        control={form.control}
                        name="equipment"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel>Equipment {required.equipment && "*"}</FormLabel>
                                <Popover open={equipmentOpen} onOpenChange={setEquipmentOpen}>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                className={cn(
                                                    "justify-between",
                                                    !field.value && "text-muted-foreground"
                                                )}
                                            >
                                                {field.value
                                                    ? equipmentList.find((e: any) => e.id === field.value)?.name ||
                                                      "Select equipment"
                                                    : "Select equipment"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-full p-0">
                                        <Command>
                                            <CommandInput
                                                placeholder="Search equipment..."
                                                value={equipmentSearch}
                                                onValueChange={setEquipmentSearch}
                                            />
                                            <CommandList>
                                                <CommandEmpty>No equipment found.</CommandEmpty>
                                                <CommandGroup>
                                                    {equipmentList.map((equip: any) => (
                                                        <CommandItem
                                                            key={equip.id}
                                                            value={equip.name}
                                                            onSelect={() => {
                                                                field.onChange(equip.id);
                                                                setEquipmentOpen(false);
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn(
                                                                    "mr-2 h-4 w-4",
                                                                    field.value === equip.id ? "opacity-100" : "opacity-0"
                                                                )}
                                                            />
                                                            {equip.name}
                                                            {equip.serial_number && (
                                                                <span className="text-muted-foreground ml-2">
                                                                    ({equip.serial_number})
                                                                </span>
                                                            )}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className="grid grid-cols-2 gap-4">
                        {/* Calibration Date */}
                        <FormField
                            control={form.control}
                            name="calibration_date"
                            render={({ field }) => (
                                <FormItem className="flex flex-col">
                                    <FormLabel>Calibration Date {required.calibration_date && "*"}</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    className={cn(
                                                        "pl-3 text-left font-normal",
                                                        !field.value && "text-muted-foreground"
                                                    )}
                                                >
                                                    {field.value ? format(new Date(field.value), "PPP") : "Pick a date"}
                                                    <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-auto p-0" align="start">
                                            <Calendar
                                                mode="single"
                                                selected={field.value ? new Date(field.value) : undefined}
                                                onSelect={(date) => field.onChange(date ? format(date, "yyyy-MM-dd") : "")}
                                                initialFocus
                                            />
                                        </PopoverContent>
                                    </Popover>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        {/* Due Date */}
                        <FormField
                            control={form.control}
                            name="due_date"
                            render={({ field }) => (
                                <FormItem className="flex flex-col">
                                    <FormLabel>Next Due Date {required.due_date && "*"}</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    className={cn(
                                                        "pl-3 text-left font-normal",
                                                        !field.value && "text-muted-foreground"
                                                    )}
                                                >
                                                    {field.value ? format(new Date(field.value), "PPP") : "Pick a date"}
                                                    <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-auto p-0" align="start">
                                            <Calendar
                                                mode="single"
                                                selected={field.value ? new Date(field.value) : undefined}
                                                onSelect={(date) => field.onChange(date ? format(date, "yyyy-MM-dd") : "")}
                                                initialFocus
                                            />
                                        </PopoverContent>
                                    </Popover>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        {/* Result */}
                        <FormField
                            control={form.control}
                            name="result"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Result</FormLabel>
                                    <Select onValueChange={field.onChange} value={field.value ?? undefined}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select result" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            {RESULT_OPTIONS.map((option) => (
                                                <SelectItem key={option} value={option}>
                                                    {option.charAt(0).toUpperCase() + option.slice(1)}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        {/* Calibration Type */}
                        <FormField
                            control={form.control}
                            name="calibration_type"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Calibration Type</FormLabel>
                                    <Select onValueChange={field.onChange} value={field.value ?? undefined}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select type" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            {CALIBRATION_TYPE_OPTIONS.map((option) => (
                                                <SelectItem key={option} value={option}>
                                                    {option.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    {/* Performed By */}
                    <FormField
                        control={form.control}
                        name="performed_by"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Performed By</FormLabel>
                                <FormControl>
                                    <Input placeholder="Name of person or lab" {...field} value={field.value ?? ""} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* External Lab */}
                    <FormField
                        control={form.control}
                        name="external_lab"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>External Lab</FormLabel>
                                <FormControl>
                                    <Input placeholder="External calibration lab name" {...field} value={field.value ?? ""} />
                                </FormControl>
                                <FormDescription>
                                    If calibration was performed by an external lab
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Certificate Number */}
                    <FormField
                        control={form.control}
                        name="certificate_number"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Certificate Number</FormLabel>
                                <FormControl>
                                    <Input placeholder="Calibration certificate number" {...field} value={field.value ?? ""} />
                                </FormControl>
                                <FormDescription>
                                    For traceability per ISO 9001
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Standards Used */}
                    <FormField
                        control={form.control}
                        name="standards_used"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Standards Used</FormLabel>
                                <FormControl>
                                    <Textarea
                                        placeholder="Reference standards with traceability info (e.g., NIST-traceable gauge blocks, cert #12345)"
                                        {...field}
                                        value={field.value ?? ""}
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className="grid grid-cols-2 gap-4">
                        {/* As Found In Tolerance */}
                        <FormField
                            control={form.control}
                            name="as_found_in_tolerance"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>As-Found Status</FormLabel>
                                    <Select
                                        onValueChange={(val) => field.onChange(val === "true" ? true : val === "false" ? false : null)}
                                        value={field.value === true ? "true" : field.value === false ? "false" : "not_recorded"}
                                    >
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Was equipment in tolerance?" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            <SelectItem value="not_recorded">Not Recorded</SelectItem>
                                            <SelectItem value="true">In Tolerance</SelectItem>
                                            <SelectItem value="false">Out of Tolerance</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <FormDescription>
                                        Equipment status before calibration
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        {/* Adjustments Made */}
                        <FormField
                            control={form.control}
                            name="adjustments_made"
                            render={({ field }) => (
                                <FormItem className="flex flex-row items-start space-x-3 space-y-0 pt-8">
                                    <FormControl>
                                        <Checkbox
                                            checked={field.value ?? false}
                                            onCheckedChange={field.onChange}
                                        />
                                    </FormControl>
                                    <div className="space-y-1 leading-none">
                                        <FormLabel>Adjustments Made</FormLabel>
                                        <FormDescription>
                                            Equipment required adjustment
                                        </FormDescription>
                                    </div>
                                </FormItem>
                            )}
                        />
                    </div>

                    {/* Notes */}
                    <FormField
                        control={form.control}
                        name="notes"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Notes</FormLabel>
                                <FormControl>
                                    <Textarea
                                        placeholder="Additional notes..."
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
                            disabled={createRecord.isPending || updateRecord.isPending}
                        >
                            {createRecord.isPending || updateRecord.isPending
                                ? "Saving..."
                                : mode === "edit"
                                ? "Update Calibration Record"
                                : "Create Calibration Record"}
                        </Button>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => navigate({ to: "/quality/calibrations/records" })}
                        >
                            Cancel
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    );
}
