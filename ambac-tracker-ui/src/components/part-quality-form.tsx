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
    Popover, PopoverTrigger, PopoverContent,
} from "@/components/ui/popover";
import {
    Command, CommandInput, CommandItem, CommandGroup,
} from "@/components/ui/command";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import {
    Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from "@/components/ui/form";

const formSchema = z.object({
    part: z.number(),
    operator: z.array(z.number()),
    machine: z.number(),
    description: z.string().optional(),
    status: z.string(),
    sampling_rule: z.number().optional(),
    step: z.number(),
    measurements: z.array(z.object({
        definition: z.number(),
        value_numeric: z.number().optional(),
        value_pass_fail: z.enum(["PASS", "FAIL"]).optional(),
    })),
});

type FormValues = z.infer<typeof formSchema>;

export function PartQualityForm({ part, onClose }: { part: any; onClose?: () => void }) {
    const { data: operatorPages } = useInfiniteQuery({
        queryKey: ["employee-options"],
        queryFn: ({ pageParam = 0 }) => api.api_Employees_Options_list({ queries: { offset: pageParam } }),
        getNextPageParam: (lastPage, pages) => lastPage?.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });

    const { data: machinePages } = useInfiniteQuery({
        queryKey: ["equipment-options"],
        queryFn: ({ pageParam = 0 }) => api.api_Equipment_Options_list({ queries: { offset: pageParam } }),
        getNextPageParam: (lastPage, pages) => lastPage?.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });


    const { data: measurementDefs, error, isError } = useQuery({
        queryKey: ["measurement-definitions", { queries: { step: part.step.id }}],
        queryFn: () => api.api_MeasurementDefinitions_list({ queries: { step: part.step } }),
        enabled: !!part?.step
    });

    if (isError) {
        console.error("Failed to fetch measurement definitions:", error);
    }

    const operators = operatorPages?.pages.flatMap((p) => p.results) ?? [];
    const machines = machinePages?.pages.flatMap((p) => p.results) ?? [];

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            part: part.id,
            operator: [],
            machine: undefined,
            status: "PENDING",
            description: "",
            step: part.step,
            sampling_rule: part.sampling_rule,
            measurements: [],
        },
    });

    const { control, handleSubmit, formState: { isSubmitting } } = form;
    const { fields, replace } = useFieldArray({ control, name: "measurements" });

    React.useEffect(() => {
        if (measurementDefs?.results) {
            const initial = measurementDefs.results.map((def: any) => ({
                definition: def.id,
                value_numeric: undefined,
                value_pass_fail: undefined,
            }));
            replace(initial);
        }
    }, [measurementDefs]);

    const [operatorSearch, setOperatorSearch] = React.useState("");
    const [machineSearch, setMachineSearch] = React.useState("");

    if (!measurementDefs && !isError && part?.step) {
        return (
            <div className="flex h-full items-center justify-center p-6">
                <p className="text-sm text-muted-foreground">Loading measurements...</p>
            </div>
        );
    }

    const onSubmit = async (value: FormValues) => {
        try {
            await api.api_ErrorReports_create(value, {
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
            });
            toast.success("Quality Report Submitted");
            onClose?.();
        } catch (err) {
            toast.error("Failed to submit Error Report");
            console.error(err);
        }
    };

    return (
            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                    <FormField
                        control={control}
                        name="operator"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Operator(s)</FormLabel>
                                <FormControl>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <Button variant="outline" className="w-full justify-start">
                                                {field.value.length > 0 ? `${field.value.length} selected` : "Select operators"}
                                            </Button>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-full p-0">
                                            <Command>
                                                <CommandInput
                                                    value={operatorSearch}
                                                    onValueChange={setOperatorSearch}
                                                    placeholder="Search operator..."
                                                />
                                                <CommandGroup>
                                                    {operators.filter((op) =>
                                                        `${op.first_name} ${op.last_name}`.toLowerCase().includes(operatorSearch.toLowerCase())
                                                    ).map((op) => {
                                                        const selected = field.value.includes(op.id);
                                                        return (
                                                            <CommandItem
                                                                key={op.id}
                                                                onSelect={() => {
                                                                    const updated = selected
                                                                        ? field.value.filter((id) => id !== op.id)
                                                                        : [...field.value, op.id];
                                                                    field.onChange(updated);
                                                                }}
                                                            >
                                                                <Checkbox checked={selected} className="mr-2" />
                                                                {op.first_name} {op.last_name}
                                                            </CommandItem>
                                                        );
                                                    })}
                                                </CommandGroup>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={control}
                        name="machine"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Machine</FormLabel>
                                <FormControl>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <Button variant="outline" className="w-full justify-start">
                                                {machines.find((m) => m.id === field.value)?.name || "Select a machine"}
                                            </Button>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-full p-0">
                                            <Command>
                                                <CommandInput
                                                    value={machineSearch}
                                                    onValueChange={setMachineSearch}
                                                    placeholder="Search machine..."
                                                />
                                                <CommandGroup>
                                                    {machines.filter((m) =>
                                                        m.name.toLowerCase().includes(machineSearch.toLowerCase())
                                                    ).map((m) => (
                                                        <CommandItem key={m.id} onSelect={() => field.onChange(m.id)}>
                                                            {m.name}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={control}
                        name="status"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Status</FormLabel>
                                <FormControl>
                                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select status" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="PASS">Pass</SelectItem>
                                            <SelectItem value="FAIL">Fail</SelectItem>
                                            <SelectItem value="PENDING">Pending</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={control}
                        name="description"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Notes</FormLabel>
                                <FormControl>
                                    <Textarea {...field} placeholder="If error, describe the error" />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {fields.map((field, index) => {
                        const def = measurementDefs?.results.find((d: any) => d.id === field.definition);
                        if (!def) return null;

                        return (
                            <FormItem key={field.id} className="space-y-2 border p-3 rounded-md">
                                <FormLabel>{def.label} {def.unit && `(${def.unit})`}</FormLabel>
                                <FormField
                                    control={control}
                                    name={`measurements.${index}.${def.type === "NUMERIC" ? "value_numeric" : "value_pass_fail"}` as const}
                                    render={({ field }) => (
                                        <FormControl>
                                            {def.type === "NUMERIC" ? (
                                                <Input type="number" {...field} onChange={(e) => field.onChange(Number(e.target.value))} />
                                            ) : (
                                                <Select onValueChange={field.onChange} defaultValue={field.value}>
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
                                    )}
                                />
                                <FormMessage />
                            </FormItem>
                        );
                    })}
                        <Button type="submit" variant="destructive" disabled={isSubmitting}>
                            {isSubmitting ? "Reporting..." : "Confirm"}
                        </Button>
                </form>
            </Form>
    );
}
