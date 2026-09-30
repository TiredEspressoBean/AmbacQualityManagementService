import { MultiPicker } from "@/components/ui/multi-picker";
import { Combobox } from "@/components/ui/combobox";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useForm, useFieldArray, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api, type PaginatedUserSelectList, type PaginatedEquipmentsList } from "@/lib/api/generated";
import { useInfiniteQuery, useQuery, queryOptions, infiniteQueryOptions } from "@tanstack/react-query";
import { useRetrieveErrorTypes } from "@/hooks/useRetrieveErrorTypes";
import { useCreateErrorType } from "@/hooks/useCreateErrorType";
import { useCreateDocument } from "@/hooks/useCreateDocument";
import { getCookie } from "@/lib/utils";
import { schemas } from "@/lib/api/generated";
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
import { Loader2, AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
    production_equipment: z.string({ required_error: "Machine selection is required" }),
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

// Manually typed to avoid Control<z.infer<...>> vs Control<FormValues> TS2719 clash across two
// react-hook-form module copies. Uses the same shape as z.infer<formSchema> but declared
// explicitly so the three-generic useForm pin resolves to a single concrete type.
type FormValues = {
    part: string;
    operator: number[];
    production_equipment: string;
    description?: string;
    status: "PENDING" | "PASS" | "FAIL";
    sampling_rule?: string;
    step: string;
    file?: File;
    classification?: "INTERNAL" | "EXTERNAL" | "QUALITY";
    detected_by?: number;
    verified_by?: number;
    is_first_piece: boolean;
    errors?: string[];
    measurements: Array<{
        definition: string;
        value_numeric?: number | null;
        value_pass_fail?: "PASS" | "FAIL" | "NA" | null;
    }>;
};

const required = {
    operator: isFieldRequired(formSchema.shape.operator),
    production_equipment: isFieldRequired(formSchema.shape.production_equipment),
};

const operatorOptionsInfinite = () =>
    infiniteQueryOptions<PaginatedUserSelectList, Error>({
        queryKey: ["employee-options"],
        queryFn: ({ pageParam = 0 }) => api.api_Employees_Options_list({ queries: { offset: pageParam as number } }),
        getNextPageParam: (lastPage, pages) => lastPage.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });

const machineOptionsInfinite = () =>
    infiniteQueryOptions<PaginatedEquipmentsList, Error>({
        queryKey: ["equipment-options"],
        queryFn: ({ pageParam = 0 }) => api.api_Equipment_Options_list({ queries: { offset: pageParam as number } }),
        getNextPageParam: (lastPage, pages) => lastPage.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });

export function PartQualityForm({ part, onClose }: { part: any; onClose?: () => void }) {
    // Extract IDs once to ensure consistency across all queries
    const stepId = React.useMemo(() => part?.step?.id || part?.step, [part?.step]);
    const partTypeId = React.useMemo(() => part?.part_type?.id || part?.part_type, [part?.part_type]);

    const [newErrorDialogOpen, setNewErrorDialogOpen] = React.useState(false);
    const [newErrorName, setNewErrorName] = React.useState("");
    const [newErrorExample, setNewErrorExample] = React.useState("");
    const [fileInputKey] = React.useState(Date.now());
    const [isUploadingDocument, setIsUploadingDocument] = React.useState(false);

    const { data: operatorPages, isLoading: operatorsLoading } = useInfiniteQuery(operatorOptionsInfinite());

    const { data: machinePages, isLoading: machinesLoading } = useInfiniteQuery(machineOptionsInfinite());


    const { data: errorTypes, refetch: refetchErrorTypes } = useRetrieveErrorTypes({
        part_type: partTypeId
    });

    const createErrorType = useCreateErrorType();
    const { mutate: uploadDocument } = useCreateDocument();

    const measurementDefinitionsOptions = (sId: string) => queryOptions({
        queryKey: ["measurement-definitions", sId] as const,
        queryFn: () => api.api_MeasurementDefinitions_list({
            queries: { step: sId }
        }),
    });

    const {
        data: measurementDefs,
        error: measurementError,
        isError: measurementIsError,
        isLoading: measurementLoading
    } = useQuery({ ...measurementDefinitionsOptions(stepId), enabled: !!stepId });

    const operators = operatorPages?.pages.flatMap((p) => p.results) ?? [];
    const machines = machinePages?.pages.flatMap((p) => p.results) ?? [];

    const form = useForm<FormValues, any, FormValues>({
        resolver: zodResolver(formSchema) as Resolver<FormValues, any, FormValues>,
        defaultValues: {
            part: part?.id,
            operator: [],
            production_equipment: undefined,
            status: "PENDING",
            description: "",
            step: stepId,
            sampling_rule: part?.sampling_rule,
            measurements: [],
            classification: "INTERNAL",
            is_first_piece: false,
        },
    });

    const { control, handleSubmit, formState: { isSubmitting, errors } } = form;
    const { fields, replace } = useFieldArray({ control, name: "measurements" });
    const measurementsInitialized = React.useRef(false);

    // Initialize measurements when definitions are loaded (only once)
    React.useEffect(() => {
        if (measurementDefs?.results && !measurementsInitialized.current) {
            const initial = measurementDefs.results.map((def: { id: string }) => ({
                definition: def.id,
                value_numeric: undefined,
                value_pass_fail: undefined,
            }));
            replace(initial);
            measurementsInitialized.current = true;
        }
    }, [measurementDefs, replace]);

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
        try {
            // Create the quality report first
            // FormValues includes file/classification used for separate doc upload — cast to API request shape.
            // eslint-disable-next-line local/no-double-cast-via-unknown -- FormValues extends the API shape with file/classification UI fields; cast strips them for the API call
            const createdReport = await api.api_QualityReports_create(values as unknown as Parameters<typeof api.api_QualityReports_create>[0], {
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

                // useCreateDocument is typed for JSON request shape, but the API actually accepts FormData for multipart upload.
                // eslint-disable-next-line local/no-double-cast-via-unknown -- Document upload uses FormData (multipart); generated client type expects JSON object
                uploadDocument(formData as unknown as Parameters<typeof uploadDocument>[0], {
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
                            <MultiPicker
                                label="Operators"
                                hideLabel
                                items={operators.map((op) => ({ id: op.id, label: `${op.first_name} ${op.last_name}` }))}
                                selected={field.value}
                                onChange={field.onChange}
                                placeholder="Select operators"
                                searchPlaceholder="Search operators..."
                                emptyHint="No operators found."
                            />
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
                    name="production_equipment"
                    render={({ field }) => (
                        <FormItem className="flex flex-col">
                            <FormLabel required={required.production_equipment}>Machine</FormLabel>
                            <FormControl>
                                <Combobox
                                    value={field.value || null}
                                    onChange={(v) => v && field.onChange(v)}
                                    options={machines.map((m) => ({ value: m.id, label: m.name }))}
                                    placeholder="Select machine"
                                    searchPlaceholder="Search machines..."
                                    emptyText="No machines found."
                                />
                            </FormControl>
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
                            <MultiPicker
                                label="Error types"
                                hideLabel
                                items={(errorTypes?.results ?? []).map((et) => ({
                                    id: String(et.id), label: et.error_name, ...(et.error_example ? { description: et.error_example } : {}),
                                }))}
                                selected={field.value ?? []}
                                onChange={field.onChange}
                                placeholder="Select error types"
                                searchPlaceholder="Search error types..."
                                emptyHint="No error types found."
                                action={{
                                    label: (q) => `Add new error type${q ? ` "${q}"` : ""}`,
                                    onSelect: (q) => { if (q) setNewErrorName(q); setNewErrorDialogOpen(true); },
                                }}
                            />
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
                                <FormControl>
                                    <Combobox
                                        value={field.value == null ? null : String(field.value)}
                                        onChange={(v) => v && field.onChange(Number(v))}
                                        options={operators.map((op) => ({ value: String(op.id), label: `${op.first_name} ${op.last_name}` }))}
                                        placeholder="Select inspector"
                                        searchPlaceholder="Search..."
                                        emptyText="No employees found."
                                    />
                                </FormControl>
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
                                <FormControl>
                                    <Combobox
                                        value={field.value == null ? null : String(field.value)}
                                        onChange={(v) => v && field.onChange(Number(v))}
                                        options={operators.map((op) => ({ value: String(op.id), label: `${op.first_name} ${op.last_name}` }))}
                                        placeholder="Select verifier (optional)"
                                        searchPlaceholder="Search..."
                                        emptyText="No employees found."
                                    />
                                </FormControl>
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
                            <div className="flex items-center gap-2 mb-4">
                                <h3 className="text-lg font-medium">Measurements</h3>
                                <span className="text-xs bg-destructive/10 text-destructive px-2 py-0.5 rounded-full font-medium">
                                    Required
                                </span>
                            </div>

                            {errors.measurements && (
                                <Alert variant="destructive" className="mb-4">
                                    <AlertCircle className="h-4 w-4" />
                                    <AlertDescription>
                                        All measurements must be filled in before submitting the quality report.
                                    </AlertDescription>
                                </Alert>
                            )}

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
                                                    <FormLabel className="text-base flex items-center gap-2">
                                                        {def.label}
                                                        {def.unit && <span className="text-muted-foreground">({def.unit})</span>}
                                                        {def.required && (
                                                            <span className="text-xs text-destructive">*</span>
                                                        )}
                                                    </FormLabel>
                                                    {def.nominal !== null && def.nominal !== undefined && (
                                                        <p className="text-xs text-muted-foreground">
                                                            Nominal: {def.nominal}
                                                            {def.upper_tol && ` +${def.upper_tol}`}
                                                            {def.lower_tol && ` -${def.lower_tol}`}
                                                            {def.unit && ` ${def.unit}`}
                                                        </p>
                                                    )}
                                                    <FormControl>
                                                        {def.type === "NUMERIC" ? (
                                                            <Input
                                                                type="number"
                                                                step="any"
                                                                placeholder="Enter measurement value"
                                                                name={measurementField.name}
                                                                ref={measurementField.ref}
                                                                onBlur={measurementField.onBlur}
                                                                disabled={measurementField.disabled}
                                                                value={measurementField.value == null ? "" : String(measurementField.value)}
                                                                onChange={(e) => {
                                                                    const value = e.target.value === '' ? undefined : Number(e.target.value);
                                                                    measurementField.onChange(value);
                                                                }}
                                                            />
                                                        ) : (
                                                            <Select
                                                                onValueChange={measurementField.onChange}
                                                                value={measurementField.value == null ? "" : String(measurementField.value)}
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