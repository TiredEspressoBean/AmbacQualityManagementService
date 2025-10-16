import * as React from "react";
import {Button} from "@/components/ui/button";
import {toast} from "sonner";
import {useForm} from "react-hook-form";
import {zodResolver} from "@hookform/resolvers/zod";
import {z} from "zod";
import {api} from "@/lib/api/generated";
import {useInfiniteQuery} from "@tanstack/react-query";
import {useQualityReports} from "@/hooks/useQualityReports";
import {useRetrieveParts} from "@/hooks/useRetrieveParts";
import {cn, getCookie} from "@/lib/utils";
import {Popover, PopoverContent, PopoverTrigger,} from "@/components/ui/popover";
import {Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,} from "@/components/ui/command";
import {Textarea} from "@/components/ui/textarea";
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from "@/components/ui/select";
import {Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage,} from "@/components/ui/form";
import {Calendar as CalendarIcon, Check, ChevronsUpDown, Loader2} from "lucide-react";
import {format} from "date-fns";
import {Calendar} from "@/components/ui/calendar";

const formSchema = z.object({
    current_state: z.enum(["OPEN", "IN_PROGRESS", "CLOSED"]),
    disposition_type: z.string().optional(),
    assigned_to: z.number().optional(),
    description: z.string().optional(),
    resolution_notes: z.string().optional(),
    resolution_completed_by: z.number().optional().nullable(),
    resolution_completed_at: z.string().optional().nullable(),
    part: z.number().nullable(),
    quality_reports: z.array(z.number())
});

type FormValues = z.infer<typeof formSchema>;

export default function PartDispositionForm({part, disposition, onClose}: { part: any; disposition?: any; onClose?: () => void }) {
    const [assignedToPopoverOpen, setAssignedToPopoverOpen] = React.useState(false);
    const [completedByPopoverOpen, setCompletedByPopoverOpen] = React.useState(false);
    const [partPopoverOpen, setPartPopoverOpen] = React.useState(false);
    const [qualityReportsPopoverOpen, setQualityReportsPopoverOpen] = React.useState(false);
    const [assignedToSearch, setAssignedToSearch] = React.useState("");
    const [completedBySearch, setCompletedBySearch] = React.useState("");
    const [partSearch, setPartSearch] = React.useState("");
    const [qualityReportSearch, setQualityReportSearch] = React.useState("");

    const {data: employeePages, isLoading: employeesLoading} = useInfiniteQuery({
        queryKey: ["employee-options"],
        queryFn: ({pageParam = 0}) => api.api_Employees_Options_list({queries: {offset: pageParam}}),
        getNextPageParam: (lastPage, pages) => lastPage?.results.length === 100 ? pages.length * 100 : undefined,
        initialPageParam: 0,
    });

    const employees = employeePages?.pages.flatMap((p) => p.results) ?? [];

    const {data: partsData} = useRetrieveParts({queries: {limit: 100, search: partSearch}});
    const {data: qualityReportsData} = useQualityReports({queries: {limit: 100, search: qualityReportSearch}});

    const parts = partsData?.results ?? [];
    const qualityReports = qualityReportsData?.results ?? [];

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema), defaultValues: {
            part: disposition?.part ?? part?.id,
            current_state: disposition?.current_state ?? "OPEN",
            disposition_type: disposition?.disposition_type,
            assigned_to: disposition?.assigned_to,
            description: disposition?.description ?? "",
            resolution_notes: disposition?.resolution_notes ?? "",
            resolution_completed_by: disposition?.resolution_completed_by,
            resolution_completed_at: disposition?.resolution_completed_at ?? new Date().toISOString(),
            quality_reports: disposition?.quality_reports ?? []
        },
    })

    const {control, handleSubmit, formState: {isSubmitting, errors}} = form;

    React.useEffect(() => {
        if (Object.keys(errors).length > 0) {
            console.log("Form validation errors:", errors);
        }
    }, [errors]);

    if (employeesLoading) {
        return (<div className="flex h-full items-center justify-center p-6">
                <Loader2 className="h-4 w-4 animate-spin mr-2"/>
                <p className="text-sm text-muted-foreground">Loading form data...</p>
            </div>);
    }

    const onSubmit = async (values: FormValues) => {
        console.log("Form submitted with values:", values);
        try {
            if (disposition?.id) {
                await api.api_QuarantineDispositions_partial_update(values, {
                    params: { id: disposition.id },
                    headers: {"X-CSRFToken": getCookie("csrftoken") ?? ""},
                });
                toast.success("Disposition Updated");
            } else {
                await api.api_QuarantineDispositions_create(values, {
                    headers: {"X-CSRFToken": getCookie("csrftoken") ?? ""},
                });
                toast.success("Disposition Created");
            }
            onClose?.();
        } catch (err) {
            console.error("API Error:", err);
            toast.error(disposition?.id ? "Failed to update Disposition" : "Failed to create Disposition");
        }
    };

    const filteredAssignedTo = employees.filter((emp) => `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(assignedToSearch.toLowerCase()));

    const filteredCompletedBy = employees.filter((emp) => `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(completedBySearch.toLowerCase()));

    return (
        <Form {...form}>
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col h-full">
                {disposition?.disposition_number && (
                    <div className="px-6 pt-6 pb-2">
                        <h3 className="text-lg font-semibold">Disposition #{disposition.disposition_number}</h3>
                    </div>
                )}
                <div className="flex-1 space-y-6 p-6 overflow-y-auto">

            <FormField
                control={control}
                name="current_state"
                render={({field}) => (<FormItem>
                        <FormLabel>Current State</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select current state"/>
                                </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                                <SelectItem value="OPEN">Open</SelectItem>
                                <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
                                <SelectItem value="CLOSED">Closed</SelectItem>
                            </SelectContent>
                        </Select>
                        <FormDescription>State of the disposition as it currently is</FormDescription>
                        <FormMessage/>
                    </FormItem>)}
            />

            <FormField
                control={control}
                name="disposition_type"
                render={({field}) => (<FormItem>
                        <FormLabel>Disposition Type</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select disposition type"/>
                                </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                                <SelectItem value="REPAIR">Repair</SelectItem>
                                <SelectItem value="REWORK">Rework</SelectItem>
                                <SelectItem value="SCRAP">Scrap</SelectItem>
                                <SelectItem value="USE_AS_IS">Use As Is</SelectItem>
                                <SelectItem value="RETURN_TO_VENDOR">Return to Vendor</SelectItem>
                            </SelectContent>
                        </Select>
                        <FormDescription>The type of resolution for this disposition</FormDescription>
                        <FormMessage/>
                    </FormItem>)}
            />
            <FormField
                control={control}
                name="assigned_to"
                render={({field}) => (
                    <FormItem className="flex flex-col">
                        <FormLabel>Assigned To</FormLabel>
                        <Popover open={assignedToPopoverOpen} onOpenChange={setAssignedToPopoverOpen}>
                            <PopoverTrigger asChild>
                                <FormControl>
                                    <Button
                                        variant="outline"
                                        role="combobox"
                                        aria-expanded={assignedToPopoverOpen}
                                        className="w-full justify-between"
                                    >
                                        {field.value
                                            ? employees.find((emp) => emp.id === field.value)?.first_name + " " + employees.find((emp) => emp.id === field.value)?.last_name
                                            : "Select employee"
                                        }
                                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                    </Button>
                                </FormControl>
                            </PopoverTrigger>
                            <PopoverContent className="w-full p-0">
                                <Command>
                                    <CommandInput
                                        placeholder="Search employees..."
                                        value={assignedToSearch}
                                        onValueChange={setAssignedToSearch}
                                    />
                                    <CommandList>
                                        <CommandEmpty>No employees found.</CommandEmpty>
                                        <CommandGroup className="max-h-64 overflow-auto">
                                            {filteredAssignedTo.map((employee) => (
                                                <CommandItem
                                                    key={employee.id}
                                                    onSelect={() => {
                                                        field.onChange(employee.id);
                                                        setAssignedToPopoverOpen(false);
                                                    }}
                                                >
                                                    <Check
                                                        className={cn(
                                                            "mr-2 h-4 w-4",
                                                            field.value === employee.id ? "opacity-100" : "opacity-0"
                                                        )}
                                                    />
                                                    {employee.first_name} {employee.last_name}
                                                </CommandItem>
                                            ))}
                                        </CommandGroup>
                                    </CommandList>
                                </Command>
                            </PopoverContent>
                        </Popover>
                        <FormDescription>Who this resolution is assigned to</FormDescription>
                        <FormMessage/>
                    </FormItem>
                )}
            />

            <FormField
                control={control}
                name="description"
                render={({field}) => (
                    <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                            <Textarea
                                placeholder="Add description for this disposition..."
                                className="resize-none"
                                {...field}
                            />
                        </FormControl>
                        <FormDescription>
                            Description for this disposition, not related to the resolution itself
                        </FormDescription>
                        <FormMessage/>
                    </FormItem>
                )}
            />

            <FormField
                control={control}
                name="resolution_notes"
                render={({field}) => (
                    <FormItem>
                        <FormLabel>Resolution Notes</FormLabel>
                        <FormControl>
                            <Textarea
                                placeholder="Add resolution notes..."
                                className="resize-none"
                                {...field}
                            />
                        </FormControl>
                        <FormDescription>Notes for this particular disposition's resolution</FormDescription>
                        <FormMessage/>
                    </FormItem>
                )}
            />
            <FormField
                control={control}
                name="resolution_completed_by"
                render={({field}) => (
                    <FormItem className="flex flex-col">
                        <FormLabel>Resolution Completed By</FormLabel>
                        <Popover open={completedByPopoverOpen} onOpenChange={setCompletedByPopoverOpen}>
                            <PopoverTrigger asChild>
                                <FormControl>
                                    <Button
                                        variant="outline"
                                        role="combobox"
                                        aria-expanded={completedByPopoverOpen}
                                        className="w-full justify-between"
                                    >
                                        {field.value
                                            ? employees.find((emp) => emp.id === field.value)?.first_name + " " + employees.find((emp) => emp.id === field.value)?.last_name
                                            : "Select employee"
                                        }
                                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                    </Button>
                                </FormControl>
                            </PopoverTrigger>
                            <PopoverContent className="w-full p-0">
                                <Command>
                                    <CommandInput
                                        placeholder="Search employees..."
                                        value={completedBySearch}
                                        onValueChange={setCompletedBySearch}
                                    />
                                    <CommandList>
                                        <CommandEmpty>No employees found.</CommandEmpty>
                                        <CommandGroup className="max-h-64 overflow-auto">
                                            {filteredCompletedBy.map((employee) => (
                                                <CommandItem
                                                    key={employee.id}
                                                    onSelect={() => {
                                                        field.onChange(employee.id);
                                                        setCompletedByPopoverOpen(false);
                                                    }}
                                                >
                                                    <Check
                                                        className={cn(
                                                            "mr-2 h-4 w-4",
                                                            field.value === employee.id ? "opacity-100" : "opacity-0"
                                                        )}
                                                    />
                                                    {employee.first_name} {employee.last_name}
                                                </CommandItem>
                                            ))}
                                        </CommandGroup>
                                    </CommandList>
                                </Command>
                            </PopoverContent>
                        </Popover>
                        <FormDescription>
                            Who completed the resolution or may verify that the resolution has been completed
                        </FormDescription>
                        <FormMessage/>
                    </FormItem>
                )}
            />

            <FormField
                control={form.control}
                name="resolution_completed_at"
                render={({field}) => (<FormItem className="flex flex-col">
                    <FormLabel>Resolution Completion Date</FormLabel>
                    <Popover>
                        <PopoverTrigger asChild>
                            <FormControl>
                                <Button
                                    variant={"outline"}
                                    className={cn("w-[240px] pl-3 text-left font-normal", !field.value && "text-muted-foreground")}
                                >
                                    {field.value ? (format(field.value, "PPP")) : (<span>Pick a date</span>)}
                                    <CalendarIcon className="ml-auto h-4 w-4 opacity-50"/>
                                </Button>
                            </FormControl>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0" align="start">
                            <Calendar
                                mode="single"
                                selected={field.value}
                                onSelect={field.onChange}
                                initialFocus
                            />
                        </PopoverContent>
                    </Popover>
                    <FormDescription>The date on which that this resolution was completed</FormDescription>
                    <FormMessage/>
                </FormItem>)}
            />
            <FormField
                control={control}
                name="part"
                render={({field}) => (
                    <FormItem className="flex flex-col">
                        <FormLabel>Related Part</FormLabel>
                        <Popover open={partPopoverOpen} onOpenChange={setPartPopoverOpen}>
                            <PopoverTrigger asChild>
                                <FormControl>
                                    <Button
                                        variant="outline"
                                        role="combobox"
                                        aria-expanded={partPopoverOpen}
                                        className="w-full justify-between"
                                    >
                                        {field.value
                                            ? parts.find((p) => p.id === field.value)?.ERP_id || `Part #${field.value}`
                                            : "Select part"
                                        }
                                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                    </Button>
                                </FormControl>
                            </PopoverTrigger>
                            <PopoverContent className="w-full p-0">
                                <Command>
                                    <CommandInput
                                        placeholder="Search parts..."
                                        value={partSearch}
                                        onValueChange={setPartSearch}
                                    />
                                    <CommandList>
                                        <CommandEmpty>No parts found.</CommandEmpty>
                                        <CommandGroup className="max-h-64 overflow-auto">
                                            {parts.map((p) => (
                                                <CommandItem
                                                    key={p.id}
                                                    onSelect={() => {
                                                        field.onChange(p.id);
                                                        setPartPopoverOpen(false);
                                                    }}
                                                >
                                                    <Check
                                                        className={cn(
                                                            "mr-2 h-4 w-4",
                                                            field.value === p.id ? "opacity-100" : "opacity-0"
                                                        )}
                                                    />
                                                    {p.ERP_id} - {p.part_type_name}
                                                </CommandItem>
                                            ))}
                                        </CommandGroup>
                                    </CommandList>
                                </Command>
                            </PopoverContent>
                        </Popover>
                        <FormDescription>The part that this disposition is related to</FormDescription>
                        <FormMessage/>
                    </FormItem>
                )}
            />
            <FormField
                control={control}
                name="quality_reports"
                render={({field}) => (
                    <FormItem className="flex flex-col">
                        <FormLabel>Quality Reports</FormLabel>
                        <Popover open={qualityReportsPopoverOpen} onOpenChange={setQualityReportsPopoverOpen}>
                            <PopoverTrigger asChild>
                                <FormControl>
                                    <Button
                                        variant="outline"
                                        role="combobox"
                                        aria-expanded={qualityReportsPopoverOpen}
                                        className="w-full justify-between"
                                    >
                                        {field.value && field.value.length > 0
                                            ? `${field.value.length} report${field.value.length > 1 ? 's' : ''} selected`
                                            : "Select quality reports"
                                        }
                                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                    </Button>
                                </FormControl>
                            </PopoverTrigger>
                            <PopoverContent className="w-full p-0">
                                <Command>
                                    <CommandInput
                                        placeholder="Search quality reports..."
                                        value={qualityReportSearch}
                                        onValueChange={setQualityReportSearch}
                                    />
                                    <CommandList>
                                        <CommandEmpty>No quality reports found.</CommandEmpty>
                                        <CommandGroup className="max-h-64 overflow-auto">
                                            {qualityReports.map((qr) => (
                                                <CommandItem
                                                    key={qr.id}
                                                    onSelect={() => {
                                                        const currentValue = field.value || [];
                                                        const newValue = currentValue.includes(qr.id)
                                                            ? currentValue.filter((id) => id !== qr.id)
                                                            : [...currentValue, qr.id];
                                                        field.onChange(newValue);
                                                    }}
                                                >
                                                    <Check
                                                        className={cn(
                                                            "mr-2 h-4 w-4",
                                                            field.value?.includes(qr.id) ? "opacity-100" : "opacity-0"
                                                        )}
                                                    />
                                                    Report #{qr.id} - Part #{qr.part} - {qr.created_at ? format(new Date(qr.created_at), 'MMM dd, yyyy') : 'No date'}
                                                </CommandItem>
                                            ))}
                                        </CommandGroup>
                                    </CommandList>
                                </Command>
                            </PopoverContent>
                        </Popover>
                        {field.value && field.value.length > 0 && (
                            <div className="mt-2 space-y-1">
                                <p className="text-sm font-medium text-muted-foreground">Selected Reports:</p>
                                <ul className="text-sm text-muted-foreground space-y-1">
                                    {field.value.map(id => {
                                        const report = qualityReports.find(qr => qr.id === id);
                                        if (!report) return <li key={id}>#{id}</li>;
                                        const dateStr = report.created_at ? format(new Date(report.created_at), 'MMM dd, yyyy') : 'No date';
                                        return (
                                            <li key={id} className="flex items-center gap-2">
                                                <span className="font-mono">#{id}</span>
                                                <span>-</span>
                                                <span>Part #{report.part}</span>
                                                <span>-</span>
                                                <span>{dateStr}</span>
                                                <span className={`px-2 py-0.5 rounded text-xs ${
                                                    report.status === 'PASS' ? 'bg-green-100 text-green-800' :
                                                    report.status === 'FAIL' ? 'bg-red-100 text-red-800' :
                                                    'bg-yellow-100 text-yellow-800'
                                                }`}>
                                                    {report.status}
                                                </span>
                                            </li>
                                        );
                                    })}
                                </ul>
                            </div>
                        )}
                        <FormDescription>Quality reports that this disposition is related to</FormDescription>
                        <FormMessage/>
                    </FormItem>
                )}
            />
                </div>

                <div className="flex justify-end space-x-2 p-6 border-t bg-background">
                    {onClose && (
                        <Button type="button" variant="outline" onClick={onClose}>
                            Cancel
                        </Button>
                    )}
                    <Button
                        type="submit"
                        disabled={isSubmitting}
                        className="min-w-[120px]"
                    >
                        {isSubmitting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Submitting...
                            </>
                        ) : (
                            "Submit Disposition"
                        )}
                    </Button>
                </div>
            </form>
        </Form>
    )
}