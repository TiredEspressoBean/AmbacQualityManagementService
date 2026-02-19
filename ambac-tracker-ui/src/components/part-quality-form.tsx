import * as React from "react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api, type PaginatedUserSelectList, type PaginatedEquipmentsList, type PaginatedMeasurementDefinitionList } from "@/lib/api/generated";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useRetrieveErrorTypes } from "@/hooks/useRetrieveErrorTypes";
import { useCreateErrorType } from "@/hooks/useCreateErrorType";
import { useCreateDocument } from "@/hooks/useCreateDocument";
import { getCookie } from "@/lib/utils";
import { schemas } from "@/lib/api/generated";
import {
    Popover,
    PopoverTrigger,
    PopoverContent,
} from "@/components/ui/popover";
import {
    Command,
    CommandInput,
    CommandItem,
    CommandGroup,
    CommandEmpty,
} from "@/components/ui/command";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectTrigger,
    SelectValue,
    SelectContent,
    SelectItem
} from "@/components/ui/select";
import {
    Form,
    FormField,
    FormItem,
    FormLabel,
    FormControl,
    FormMessage,
    FormDescription,
} from "@/components/ui/form";
import { Check, ChevronsUpDown, Loader2, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import { isFieldRequired } from "@/lib/zod-config";

const formSchema = z.object({
    part: z.string(),
    operator: z.array(z.number()).min(1, "At least one operator must be selected"),
    machine: z.string({ required_error: "Machine selection is required" }),
    description: z.string().optional(),
    status: schemas.QualityReportStatusEnum,
    sampling_rule: z.string().optional(),
    step: z.string(),
    file: z.instanceof(File).optional(),
    classification: schemas.ClassificationEnum.optional(),
    detected_by: z.number().optional(),
    verified_by: z.number().optional(),
    is_first_piece: z.boolean().default(false),
    // Use generated schema for measurements - definition is a UUID string, not number
    measurements: z.array(schemas.MeasurementResultRequest).refine(
        (measurements) => measurements.every(m =>
            m.value_numeric !== undefined || m.value_pass_fail !== undefined
        ),
        { message: "All measurements must have a value" }
    ),
});

type FormValues = z.infer<typeof formSchema>;

const required = {
    operator: isFieldRequired(formSchema.shape.operator),
    machine: isFieldRequired(formSchema.shape.machine),
};

export function PartQualityForm({ part, onClose }: { part: any; onClose?: () => void }) {
    const [operatorPopoverOpen, setOperatorPopoverOpen] = React.useState(false);
    const [machinePopoverOpen, setMachinePopoverOpen] = React.useState(false);
    const [errorTypesPopoverOpen, setErrorTypesPopoverOpen] = React.useState(false);
    const [detectedByPopoverOpen, setDetectedByPopoverOpen] = React.useState(false);
    const [verifiedByPopoverOpen, setVerifiedByPopoverOpen] = React.useState(false);
    const [operatorSearch, setOperatorSearch] = React.useState("");
    const [machineSearch, setMachineSearch] = React.useState("");
    const [errorTypesSearch, setErrorTypesSearch] = React.useState("");
    const [detectedBySearch, setDetectedBySearch] = React.useState("");
    const [verifiedBySearch, setVerifiedBySearch] = React.useState("");
    const [newErrorDialogOpen, setNewErrorDialogOpen] = React.useState(false);
    const [newErrorName, setNewErrorName] = React.useState("");
    const [newErrorExample, setNewErrorExample] = React.useState("");
    const [_fileInputKey, _setFileInputKey] = React.useState(Date.now());
    const [isUploadingDocument, setIsUploadingDocument] = React.useState(false);

    const { data: operatorPages, isLoading: operatorsLoading } = useInfiniteQuery<PaginatedUserSelectList, Error>({
        queryKey: ["employee-options"],
        queryFn: ({ pageParam = 0 }) => api.api_Employees_Options_list({ queries: { offset: pageParam } }),
        getNextPageParam: (lastPage, pages) => lastPage.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });

    const { data: machinePages, isLoading: machinesLoading } = useInfiniteQuery<PaginatedEquipmentsList, Error>({
        queryKey: ["equipment-options"],
        queryFn: ({ pageParam = 0 }) => api.api_Equipment_Options_list({ queries: { offset: pageParam } }),
        getNextPageParam: (lastPage, pages) => lastPage.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });


    const { data: errorTypes, isLoading: _errorTypesLoading, refetch: refetchErrorTypes } = useRetrieveErrorTypes({
        part_type: part?.part_type?.id || part?.part_type
    });

    const createErrorType = useCreateErrorType();
    const { mutate: uploadDocument } = useCreateDocument();

    const {
        data: measurementDefs,
        error: measurementError,
        isError: measurementIsError,
        isLoading: measurementLoading
    } = useQuery<PaginatedMeasurementDefinitionList, Error>({
        queryKey: ["measurement-definitions", { queries: { step: part?.step?.id || part?.step }}],
        queryFn: () => api.api_MeasurementDefinitions_list({
            queries: { step: part?.step?.id || part?.step }
        }),
        enabled: !!(part?.step?.id || part?.step)
    });

    const operators = operatorPages?.pages.flatMap((p) => p.results) ?? [];
    const machines = machinePages?.pages.flatMap((p) => p.results) ?? [];

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            part: part?.id,
            operator: [],
            machine: undefined,
            status: "PENDING",
            description: "",
            step: part?.step?.id || part?.step,
            sampling_rule: part?.sampling_rule,
            measurements: [],
            classification: "internal",
            is_first_piece: false,
        },
    });

    const { control, handleSubmit, formState: { isSubmitting, errors } } = form;
    const { fields, replace } = useFieldArray({ control, name: "measurements" });

    // Initialize measurements when definitions are loaded
    React.useEffect(() => {
        if (measurementDefs?.results) {
            const initial = measurementDefs.results.map((def: { id: string }) => ({
                definition: def.id,
                value_numeric: undefined,
                value_pass_fail: undefined,
            }));
            replace(initial);
        }
    }, [measurementDefs, replace]);

    // Debug form errors
    React.useEffect(() => {
        if (Object.keys(errors).length > 0) {
            console.log("Form validation errors:", errors);
        }
    }, [errors]);

    if (measurementLoading || operatorsLoading || machinesLoading) {
        return (
            <div className="flex h-full items-center justify-center p-6">
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                <p className="text-sm text-muted-foreground">Loading form data...</p>
            </div>
        );
    }

    if (measurementIsError) {
        return (
            <div className="flex h-full items-center justify-center p-6">
                <p className="text-sm text-destructive">
                    Failed to load measurement definitions: {measurementError?.message}
                </p>
            </div>
        );
    }

    const onSubmit = async (values: FormValues) => {
        console.log("Form submitted with values:", values);
        try {
            // Create the quality report first
            const createdReport = await api.api_ErrorReports_create(values, {
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
            });

            // If a file was selected, upload it
            if (values.file && values.classification) {
                setIsUploadingDocument(true);
                const formData = new FormData();
                formData.append("file", values.file);
                formData.append("classification", values.classification);
                formData.append("object_id", String(createdReport.id));
                formData.append("content_type", "qualityreports");

                uploadDocument(formData, {
                    onSuccess: () => {
                        setIsUploadingDocument(false);
                        toast.success("Quality Report and Document Submitted");
                        onClose?.();
                    },
                    onError: (err) => {
                        setIsUploadingDocument(false);
                        console.error("Document upload error:", err);
                        toast.error("Report created, but document upload failed");
                        onClose?.();
                    },
                });
            } else {
                toast.success("Quality Report Submitted");
                onClose?.();
            }
        } catch (err) {
            console.error("API Error:", err);
            toast.error("Failed to submit Quality Report");
        }
    };

    const filteredOperators = operators.filter((op) =>
        `${op.first_name} ${op.last_name}`.toLowerCase().includes(operatorSearch.toLowerCase())
    );

    const filteredMachines = machines.filter((m) =>
        m.name.toLowerCase().includes(machineSearch.toLowerCase())
    );

    const filteredErrorTypes = errorTypes?.results?.filter((et) =>
        et.error_name.toLowerCase().includes(errorTypesSearch.toLowerCase())
    ) ?? [];

    const filteredDetectedBy = operators.filter((op) =>
        `${op.first_name} ${op.last_name}`.toLowerCase().includes(detectedBySearch.toLowerCase())
    );

    const filteredVerifiedBy = operators.filter((op) =>
        `${op.first_name} ${op.last_name}`.toLowerCase().includes(verifiedBySearch.toLowerCase())
    );

    const handleCreateErrorType = async () => {
        if (!newErrorName.trim()) {
            toast.error("Error name is required");
            return;
        }

        try {
            await createErrorType.mutateAsync({
                error_name: newErrorName,
                error_example: newErrorExample,
                part_type: part?.part_type?.id || part?.part_type,
            });
            toast.success("Error type created successfully");
            setNewErrorName("");
            setNewErrorExample("");
            setNewErrorDialogOpen(false);
            refetchErrorTypes();
        } catch (err) {
            console.error("Failed to create error type:", err);
            toast.error("Failed to create error type");
        }
    };

    return (
        <Form {...form}>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                {/* Operators Field */}
                <FormField
                    control={control}
                    name="operator"
                    render={({ field }) => (
                        <FormItem className="flex flex-col">
                            <FormLabel required={required.operator}>Operators</FormLabel>
                            <Popover open={operatorPopoverOpen} onOpenChange={setOperatorPopoverOpen}>
                                <PopoverTrigger asChild>
                                    <FormControl>
                                        <Button
                                            variant="outline"
                                            role="combobox"
                                            aria-expanded={operatorPopoverOpen}
                                            className="w-full justify-between"
                                        >
                                            {field.value.length > 0
                                                ? `${field.value.length} operator${field.value.length > 1 ? 's' : ''} selected`
                                                : "Select operators"
                                            }
                                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                        </Button>
                                    </FormControl>
                                </PopoverTrigger>
                                <PopoverContent className="w-full p-0">
                                    <Command>
                                        <CommandInput
                                            placeholder="Search operators..."
                                            value={operatorSearch}
                                            onValueChange={setOperatorSearch}
                                        />
                                        <CommandEmpty>No operators found.</CommandEmpty>
                                        <CommandGroup className="max-h-64 overflow-auto">
                                            {filteredOperators.map((operator) => {
                                                const isSelected = field.value.includes(operator.id);
                                                return (
                                                    <CommandItem
                                                        key={operator.id}
                                                        onSelect={() => {
                                                            const updated = isSelected
                                                                ? field.value.filter((id) => id !== operator.id)
                                                                : [...field.value, operator.id];
                                                            field.onChange(updated);
                                                        }}
                                                    >
                                                        <Checkbox
                                                            checked={isSelected}
                                                            className="mr-2"
                                                        />
                                                        {operator.first_name} {operator.last_name}
                                                    </CommandItem>
                                                );
                                            })}
                                        </CommandGroup>
                                    </Command>
                                </PopoverContent>
                            </Popover>
                            <FormDescription>
                                Select all operators involved in this quality check
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                {/* Machine Field */}
                <FormField
                    control={control}
                    name="machine"
                    render={({ field }) => (
                        <FormItem className="flex flex-col">
                            <FormLabel required={required.machine}>Machine</FormLabel>
                            <Popover open={machinePopoverOpen} onOpenChange={setMachinePopoverOpen}>
                                <PopoverTrigger asChild>
                                    <FormControl>
                                        <Button
                                            variant="outline"
                                            role="combobox"
                                            aria-expanded={machinePopoverOpen}
                                            className="w-full justify-between"
                                        >
                                            {field.value
                                                ? machines.find((machine) => machine.id === field.value)?.name
                                                : "Select machine"
                                            }
                                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                        </Button>
                                    </FormControl>
                                </PopoverTrigger>
                                <PopoverContent className="w-full p-0">
                                    <Command>
                                        <CommandInput
                                            placeholder="Search machines..."
                                            value={machineSearch}
                                            onValueChange={setMachineSearch}
                                        />
                                        <CommandEmpty>No machines found.</CommandEmpty>
                                        <CommandGroup className="max-h-64 overflow-auto">
                                            {filteredMachines.map((machine) => (
                                                <CommandItem
                                                    key={machine.id}
                                                    onSelect={() => {
                                                        field.onChange(machine.id);
                                                        setMachinePopoverOpen(false);
                                                    }}
                                                >
                                                    <Check
                                                        className={cn(
                                                            "mr-2 h-4 w-4",
                                                            field.value === machine.id ? "opacity-100" : "opacity-0"
                                                        )}
                                                    />
                                                    {machine.name}
                                                </CommandItem>
                                            ))}
                                        </CommandGroup>
                                    </Command>
                                </PopoverContent>
                            </Popover>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                {/* Status Field */}
                <FormField
                    control={control}
                    name="status"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Status</FormLabel>
                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                <FormControl>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select status" />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                    {schemas.QualityReportStatusEnum.options.map((status) => (
                                        <SelectItem key={status} value={status}>
                                            {status.charAt(0) + status.slice(1).toLowerCase()}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                {/* Error Types Field */}
                <FormField
                    control={control}
                    name="errors"
                    render={({ field }) => (
                        <FormItem className="flex flex-col">
                            <FormLabel>Error Types</FormLabel>
                            <Popover open={errorTypesPopoverOpen} onOpenChange={setErrorTypesPopoverOpen}>
                                <PopoverTrigger asChild>
                                    <FormControl>
                                        <Button
                                            variant="outline"
                                            role="combobox"
                                            aria-expanded={errorTypesPopoverOpen}
                                            className="w-full justify-between"
                                        >
                                            {field.value && field.value.length > 0
                                                ? `${field.value.length} error type${field.value.length > 1 ? 's' : ''} selected`
                                                : "Select error types"
                                            }
                                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                        </Button>
                                    </FormControl>
                                </PopoverTrigger>
                                <PopoverContent className="w-full p-0">
                                    <Command>
                                        <CommandInput
                                            placeholder="Search error types..."
                                            value={errorTypesSearch}
                                            onValueChange={setErrorTypesSearch}
                                        />
                                        <CommandEmpty>
                                            <div className="flex flex-col items-center gap-2 py-6">
                                                <p className="text-sm text-muted-foreground">No error types found.</p>
                                                <Button
                                                    type="button"
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={() => {
                                                        setErrorTypesPopoverOpen(false);
                                                        setNewErrorDialogOpen(true);
                                                    }}
                                                    className="gap-1"
                                                >
                                                    <Plus className="h-3 w-3" />
                                                    Add New Error Type
                                                </Button>
                                            </div>
                                        </CommandEmpty>
                                        <CommandGroup className="max-h-64 overflow-auto">
                                            {filteredErrorTypes.map((errorType) => {
                                                const isSelected = field.value?.includes(errorType.id) ?? false;
                                                return (
                                                    <CommandItem
                                                        key={errorType.id}
                                                        onSelect={() => {
                                                            const updated = isSelected
                                                                ? (field.value?.filter((id) => id !== errorType.id) ?? [])
                                                                : [...(field.value ?? []), errorType.id];
                                                            field.onChange(updated);
                                                        }}
                                                    >
                                                        <Checkbox
                                                            checked={isSelected}
                                                            className="mr-2"
                                                        />
                                                        <div className="flex flex-col">
                                                            <span>{errorType.error_name}</span>
                                                            {errorType.error_example && (
                                                                <span className="text-xs text-muted-foreground">
                                                                    {errorType.error_example}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </CommandItem>
                                                );
                                            })}
                                            <CommandItem
                                                onSelect={() => {
                                                    setErrorTypesPopoverOpen(false);
                                                    setNewErrorDialogOpen(true);
                                                }}
                                                className="border-t"
                                            >
                                                <Plus className="mr-2 h-4 w-4" />
                                                Add New Error Type
                                            </CommandItem>
                                        </CommandGroup>
                                    </Command>
                                </PopoverContent>
                            </Popover>
                            <FormDescription>
                                Select error types for this part or add a new one
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                {/* Description Field */}
                <FormField
                    control={control}
                    name="description"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Notes</FormLabel>
                            <FormControl>
                                <Textarea
                                    {...field}
                                    placeholder="Add any additional notes or observations..."
                                    className="min-h-[80px]"
                                />
                            </FormControl>
                            <FormDescription>
                                Describe any issues, observations, or additional context
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                {/* First Piece Inspection Flag */}
                <FormField
                    control={control}
                    name="is_first_piece"
                    render={({ field }) => (
                        <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4 bg-amber-50 dark:bg-amber-950/20">
                            <FormControl>
                                <Checkbox
                                    checked={field.value}
                                    onCheckedChange={field.onChange}
                                />
                            </FormControl>
                            <div className="space-y-1 leading-none">
                                <FormLabel>First Piece Inspection (FPI)</FormLabel>
                                <FormDescription>
                                    Mark this as the first piece inspection for setup verification. Required before other parts can proceed at this step.
                                </FormDescription>
                            </div>
                        </FormItem>
                    )}
                />

                {/* Traceability Section */}
                <div className="grid gap-4 md:grid-cols-2">
                    {/* Detected By Field */}
                    <FormField
                        control={control}
                        name="detected_by"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel>Detected By</FormLabel>
                                <Popover open={detectedByPopoverOpen} onOpenChange={setDetectedByPopoverOpen}>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                aria-expanded={detectedByPopoverOpen}
                                                className="w-full justify-between"
                                            >
                                                {field.value
                                                    ? `${operators.find((op) => op.id === field.value)?.first_name} ${operators.find((op) => op.id === field.value)?.last_name}`
                                                    : "Select inspector"
                                                }
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-full p-0">
                                        <Command>
                                            <CommandInput
                                                placeholder="Search..."
                                                value={detectedBySearch}
                                                onValueChange={setDetectedBySearch}
                                            />
                                            <CommandEmpty>No employees found.</CommandEmpty>
                                            <CommandGroup className="max-h-64 overflow-auto">
                                                {filteredDetectedBy.map((emp) => (
                                                    <CommandItem
                                                        key={emp.id}
                                                        onSelect={() => {
                                                            field.onChange(emp.id);
                                                            setDetectedByPopoverOpen(false);
                                                        }}
                                                    >
                                                        <Check
                                                            className={cn(
                                                                "mr-2 h-4 w-4",
                                                                field.value === emp.id ? "opacity-100" : "opacity-0"
                                                            )}
                                                        />
                                                        {emp.first_name} {emp.last_name}
                                                    </CommandItem>
                                                ))}
                                            </CommandGroup>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>
                                    Inspector who detected the defect
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Verified By Field */}
                    <FormField
                        control={control}
                        name="verified_by"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel>Verified By</FormLabel>
                                <Popover open={verifiedByPopoverOpen} onOpenChange={setVerifiedByPopoverOpen}>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                aria-expanded={verifiedByPopoverOpen}
                                                className="w-full justify-between"
                                            >
                                                {field.value
                                                    ? `${operators.find((op) => op.id === field.value)?.first_name} ${operators.find((op) => op.id === field.value)?.last_name}`
                                                    : "Select verifier (optional)"
                                                }
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-full p-0">
                                        <Command>
                                            <CommandInput
                                                placeholder="Search..."
                                                value={verifiedBySearch}
                                                onValueChange={setVerifiedBySearch}
                                            />
                                            <CommandEmpty>No employees found.</CommandEmpty>
                                            <CommandGroup className="max-h-64 overflow-auto">
                                                {filteredVerifiedBy.map((emp) => (
                                                    <CommandItem
                                                        key={emp.id}
                                                        onSelect={() => {
                                                            field.onChange(emp.id);
                                                            setVerifiedByPopoverOpen(false);
                                                        }}
                                                    >
                                                        <Check
                                                            className={cn(
                                                                "mr-2 h-4 w-4",
                                                                field.value === emp.id ? "opacity-100" : "opacity-0"
                                                            )}
                                                        />
                                                        {emp.first_name} {emp.last_name}
                                                    </CommandItem>
                                                ))}
                                            </CommandGroup>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>
                                    Second signature for critical inspections
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                {/* Measurements */}
                {fields.length > 0 && (
                    <div className="space-y-4">
                        <div className="border-t pt-4">
                            <h3 className="text-lg font-medium mb-4">Measurements</h3>
                            <div className="space-y-4">
                                {fields.map((field, index) => {
                                    const def = measurementDefs?.results.find((d: { id: string }) => d.id === field.definition);
                                    if (!def) return null;

                                    return (
                                        <FormField
                                            key={field.id}
                                            control={control}
                                            name={`measurements.${index}.${def.type === "NUMERIC" ? "value_numeric" : "value_pass_fail"}` as const}
                                            render={({ field: measurementField }) => (
                                                <FormItem className="border rounded-md p-4">
                                                    <FormLabel className="text-base">
                                                        {def.label}
                                                        {def.unit && <span className="text-muted-foreground ml-1">({def.unit})</span>}
                                                    </FormLabel>
                                                    <FormControl>
                                                        {def.type === "NUMERIC" ? (
                                                            <Input
                                                                type="number"
                                                                step="any"
                                                                placeholder="Enter measurement value"
                                                                {...measurementField}
                                                                onChange={(e) => {
                                                                    const value = e.target.value === '' ? undefined : Number(e.target.value);
                                                                    measurementField.onChange(value);
                                                                }}
                                                            />
                                                        ) : (
                                                            <Select
                                                                onValueChange={measurementField.onChange}
                                                                value={measurementField.value}
                                                            >
                                                                <SelectTrigger>
                                                                    <SelectValue placeholder="Select result" />
                                                                </SelectTrigger>
                                                                <SelectContent>
                                                                    {schemas.ValuePassFailEnum.options.map((val) => (
                                                                        <SelectItem key={val} value={val}>
                                                                            {val.charAt(0) + val.slice(1).toLowerCase()}
                                                                        </SelectItem>
                                                                    ))}
                                                                </SelectContent>
                                                            </Select>
                                                        )}
                                                    </FormControl>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                )}

                {/* Document Upload Section */}
                <div className="border-t pt-4 space-y-4">
                    <h3 className="text-lg font-medium">Attach Document (Optional)</h3>

                    <FormField
                        control={control}
                        name="file"
                        render={({ field: { onChange } }) => (
                            <FormItem>
                                <FormLabel>File</FormLabel>
                                <FormControl>
                                    <Input
                                        key={fileInputKey}
                                        type="file"
                                        accept="*/*"
                                        onChange={(e) => onChange(e.target.files?.[0])}
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={control}
                        name="classification"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Classification</FormLabel>
                                <FormControl>
                                    <Select onValueChange={field.onChange} value={field.value}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select classification" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {schemas.ClassificationEnum.options.map((level) => (
                                                <SelectItem key={level} value={level}>
                                                    {level.charAt(0).toUpperCase() + level.slice(1)}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                {/* Submit Button */}
                <div className="flex justify-end space-x-2 pt-4 border-t">
                    {onClose && (
                        <Button type="button" variant="outline" onClick={onClose}>
                            Cancel
                        </Button>
                    )}
                    <Button
                        type="submit"
                        variant="destructive"
                        disabled={isSubmitting || isUploadingDocument}
                        className="min-w-[120px]"
                    >
                        {isSubmitting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Submitting...
                            </>
                        ) : isUploadingDocument ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Uploading Document...
                            </>
                        ) : (
                            "Submit Report"
                        )}
                    </Button>
                </div>
            </form>

            {/* Create New Error Type Dialog */}
            <Dialog open={newErrorDialogOpen} onOpenChange={setNewErrorDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Add New Error Type</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <label htmlFor="error-name" className="text-sm font-medium">
                                Error Name *
                            </label>
                            <Input
                                id="error-name"
                                placeholder="Enter error name"
                                value={newErrorName}
                                onChange={(e) => setNewErrorName(e.target.value)}
                            />
                        </div>
                        <div className="space-y-2">
                            <label htmlFor="error-example" className="text-sm font-medium">
                                Example (Optional)
                            </label>
                            <Textarea
                                id="error-example"
                                placeholder="Enter an example of this error"
                                value={newErrorExample}
                                onChange={(e) => setNewErrorExample(e.target.value)}
                                className="min-h-[80px]"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => {
                                setNewErrorDialogOpen(false);
                                setNewErrorName("");
                                setNewErrorExample("");
                            }}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="button"
                            onClick={handleCreateErrorType}
                            disabled={createErrorType.isPending}
                        >
                            {createErrorType.isPending ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Creating...
                                </>
                            ) : (
                                "Create Error Type"
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Form>
    );
}