import * as React from "react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api/generated";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
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
import { Check, ChevronsUpDown, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const formSchema = z.object({
    part: z.number(),
    operator: z.array(z.number()).min(1, "At least one operator must be selected"),
    machine: z.number({ required_error: "Machine selection is required" }),
    description: z.string().optional(),
    status: z.enum(["PASS", "FAIL", "PENDING"]),
    sampling_rule: z.number().optional(),
    step: z.number(),
    measurements: z.array(z.object({
        definition: z.number(),
        value_numeric: z.number().optional(),
        value_pass_fail: z.enum(["PASS", "FAIL"]).optional(),
    })).refine(
        (measurements) => measurements.every(m =>
            m.value_numeric !== undefined || m.value_pass_fail !== undefined
        ),
        { message: "All measurements must have a value" }
    ),
});

type FormValues = z.infer<typeof formSchema>;

export function PartQualityForm({ part, onClose }: { part: any; onClose?: () => void }) {
    const [operatorPopoverOpen, setOperatorPopoverOpen] = React.useState(false);
    const [machinePopoverOpen, setMachinePopoverOpen] = React.useState(false);
    const [operatorSearch, setOperatorSearch] = React.useState("");
    const [machineSearch, setMachineSearch] = React.useState("");

    const { data: operatorPages, isLoading: operatorsLoading } = useInfiniteQuery({
        queryKey: ["employee-options"],
        queryFn: ({ pageParam = 0 }) => api.api_Employees_Options_list({ queries: { offset: pageParam } }),
        getNextPageParam: (lastPage, pages) => lastPage?.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });

    const { data: machinePages, isLoading: machinesLoading } = useInfiniteQuery({
        queryKey: ["equipment-options"],
        queryFn: ({ pageParam = 0 }) => api.api_Equipment_Options_list({ queries: { offset: pageParam } }),
        getNextPageParam: (lastPage, pages) => lastPage?.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });

    const {
        data: measurementDefs,
        error: measurementError,
        isError: measurementIsError,
        isLoading: measurementLoading
    } = useQuery({
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
        },
    });

    const { control, handleSubmit, formState: { isSubmitting, errors } } = form;
    const { fields, replace } = useFieldArray({ control, name: "measurements" });

    // Initialize measurements when definitions are loaded
    React.useEffect(() => {
        if (measurementDefs?.results) {
            const initial = measurementDefs.results.map((def: any) => ({
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
            await api.api_ErrorReports_create(values, {
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
            });
            toast.success("Quality Report Submitted");
            onClose?.();
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

    return (
        <Form {...form}>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                {/* Operators Field */}
                <FormField
                    control={control}
                    name="operator"
                    render={({ field }) => (
                        <FormItem className="flex flex-col">
                            <FormLabel>Operators *</FormLabel>
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
                            <FormLabel>Machine *</FormLabel>
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
                                    <SelectItem value="PASS">Pass</SelectItem>
                                    <SelectItem value="FAIL">Fail</SelectItem>
                                    <SelectItem value="PENDING">Pending</SelectItem>
                                </SelectContent>
                            </Select>
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

                {/* Measurements */}
                {fields.length > 0 && (
                    <div className="space-y-4">
                        <div className="border-t pt-4">
                            <h3 className="text-lg font-medium mb-4">Measurements</h3>
                            <div className="space-y-4">
                                {fields.map((field, index) => {
                                    const def = measurementDefs?.results.find((d: any) => d.id === field.definition);
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
                                                                    <SelectItem value="PASS">Pass</SelectItem>
                                                                    <SelectItem value="FAIL">Fail</SelectItem>
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
                        disabled={isSubmitting}
                        className="min-w-[120px]"
                    >
                        {isSubmitting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Submitting...
                            </>
                        ) : (
                            "Submit Report"
                        )}
                    </Button>
                </div>
            </form>
        </Form>
    );
}