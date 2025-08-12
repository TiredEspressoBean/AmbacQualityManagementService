"use client"
import {useEffect, useState} from "react"
import {toast} from "sonner"
import {useForm} from "react-hook-form"
import {zodResolver} from "@hookform/resolvers/zod"
import {z} from "zod"
import {cn} from "@/lib/utils"
import {Button} from "@/components/ui/button"
import {Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage,} from "@/components/ui/form"
import {Input} from "@/components/ui/input"
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from "@/components/ui/select"
import {Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList} from "@/components/ui/command"
import {Popover, PopoverContent, PopoverTrigger,} from "@/components/ui/popover"
import {Check, ChevronsUpDown} from "lucide-react"
import {Checkbox} from "@/components/ui/checkbox"

import {useRetrieveOrders} from '@/hooks/useRetrieveOrders.ts'
import {useRetrievePartTypes} from "@/hooks/useRetrievePartTypes.ts";
import {useRetrieveWorkOrders} from "@/hooks/useRetrieveWorkOrders.ts";
import {useRetrieveProcesses} from "@/hooks/useRetrieveProcesses.ts";
import {useRetrieveSteps} from "@/hooks/useRetrieveSteps.ts";
import {schemas} from "@/lib/api/generated.ts";
import {useRetrievePart} from "@/hooks/useRetrievePart.ts";
import {useParams} from "@tanstack/react-router";
import {useRetrieveOrder} from "@/hooks/useRetrieveOrder.ts";
import {useCreatePart} from "@/hooks/useCreatePart.ts";
import {useUpdatePart} from "@/hooks/useUpdatePart.ts";
import {DocumentUploader} from "@/pages/editors/forms/DocumentUploader.tsx";

const PART_STATUS = schemas.PartStatusEnum.options;

const formSchema = z.object({
    ERP_id: z
        .string()
        .min(1, "ERP ID is required - please enter the unique identifier from your ERP system")
        .max(100, "ERP ID must be 100 characters or less"),
    part_status: schemas.PartStatusEnum.optional(),
    order: z.number().optional(),
    part_type: z
        .number()
        .min(1, "Part type must be selected - please choose which type of part this is"),
    step: z
        .number()
        .min(1, "Step must be selected - please choose which manufacturing step this part is in"),
    work_order: z.number().optional(),
    archived: z.boolean().default(false).optional(),
});

type FormData = z.infer<typeof formSchema>;

export default function PartFormPage() {
    const params = useParams({strict: false});
    const mode = params.id ? 'edit' : 'create';
    const partId = params.id ? parseInt(params.id, 10) : undefined;

    // Fetch part data if in edit mode
    const {data: part} = useRetrievePart({params: {id: partId!}}, {enabled: mode === 'edit' && !!partId});

    const [search, setSearch] = useState("")
    const {data: orders} = useRetrieveOrders({
        queries: {search: search}
    })
    const [partTypeSearch, setPartTypeSearch] = useState("")
    const {data: partTypes} = useRetrievePartTypes({
        queries: {search: partTypeSearch}
    })

    const [workOrderSearch, setWorkOrderSearch] = useState("")
    const {data: workOrders} = useRetrieveWorkOrders({
        queries: {search: workOrderSearch},
    })

    const {data: selectedOrder} = useRetrieveOrder(part?.order ?? 0, {
        enabled: !!part?.order,
    });

    const form = useForm<FormData>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            ERP_id: part?.ERP_id ?? "",
            part_status: part?.part_status ?? PART_STATUS[0],
            order: part?.order ?? undefined,
            part_type: part?.part_type ?? undefined,
            step: part?.step ?? undefined,
            archived: part?.archived ?? false,
            work_order: part?.work_order ?? undefined,
        },
    })

    useEffect(() => {
        if (mode === "edit" && part) {
            form.reset({
                ERP_id: part.ERP_id ?? "",
                part_status: part.part_status ?? PART_STATUS[0],
                order: part.order ?? undefined,
                part_type: part.part_type ?? undefined,
                step: part.step ?? undefined,
                archived: part.archived ?? false,
                work_order: part.work_order ?? undefined,
            });
        }
    }, [mode, part, form]);

    const selectedPartType = form.watch("part_type")
    
    // Process selection for filtering steps (not submitted to API)
    const [selectedProcess, setSelectedProcess] = useState<number | undefined>(undefined)

    const {data: processes} = useRetrieveProcesses({
        queries: {part_type: selectedPartType}
    });

    const {data: steps} = useRetrieveSteps({
        queries: {
            part_type: selectedPartType,
            process: selectedProcess || undefined,
        },
    })
    
    // Auto-select process when editing and we have part data
    useEffect(() => {
        if (mode === "edit" && part?.process && processes?.results) {
            const processId = typeof part.process === 'string' ? parseInt(part.process) : part.process;
            const matchingProcess = processes.results.find(p => p.id === processId);
            if (matchingProcess && selectedProcess !== processId) {
                setSelectedProcess(matchingProcess.id);
            }
        }
    }, [mode, part?.process, processes?.results, selectedProcess]);

    // Reset process selection when part type changes
    useEffect(() => {
        setSelectedProcess(undefined);
    }, [selectedPartType]);

    const createPart = useCreatePart();
    const updatePart = useUpdatePart();

    function onSubmit(values: FormData) {
        if (mode === "edit" && partId) {
            updatePart.mutate({
                id: partId, data: values,
            }, {
                onSuccess: () => {
                    toast.success("Part updated successfully!");
                }, onError: (error) => {
                    console.error("Failed to update part:", error);
                    toast.error("Failed to update the part.");
                },
            });
        } else {
            createPart.mutate(values, {
                onSuccess: () => {
                    toast.success("Part created successfully!");
                    form.reset(); // optionally reset the form
                }, onError: (error) => {
                    console.error("Failed to create part:", error);
                    toast.error("Failed to create the part.");
                },
            });
        }
    }

    return (<div>
            <Form {...form}>
                <div className="max-w-3xl mx-auto py-6">
                    <h1 className="text-2xl font-semibold tracking-tight">
                        {mode === "edit" ? "Edit Part" : "Create New Part"}
                    </h1>
                    <p className="text-muted-foreground text-sm mt-1">
                        {mode === "edit" ? `Update details for Part #${partId ?? ""}` : "Fill out the details below to create a new part."}
                    </p>
                </div>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8 max-w-3xl mx-auto py-10">

                    <FormField
                        control={form.control}
                        name="ERP_id"
                        render={({field}) => (<FormItem>
                            <FormLabel>ERP Id *</FormLabel>
                            <FormControl>
                                <Input
                                    placeholder=""

                                    type=""
                                    {...field} />
                            </FormControl>
                            <FormDescription>ID in Glovia</FormDescription>
                            <FormMessage/>
                        </FormItem>)}
                    />

                    <FormField
                        control={form.control}
                        name="part_status"
                        render={({field}) => (<FormItem>
                            <FormLabel>Status</FormLabel>
                            <Select onValueChange={field.onChange} value={field.value}>
                                <FormControl>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select the current status of the part"/>
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                    {PART_STATUS.map((status) => (<SelectItem key={status} value={status}>
                                        {status.replace("_", " ")} {/* optional formatting */}
                                    </SelectItem>))}
                                </SelectContent>
                            </Select>
                            <FormDescription>Status of the part</FormDescription>
                            <FormMessage/>
                        </FormItem>)}
                    />
                    <FormField
                        control={form.control}
                        name="order"
                        render={({field}) => (<FormItem className="flex flex-col">
                            <FormLabel>Order</FormLabel>
                            <Popover>
                                <PopoverTrigger asChild>
                                    <FormControl>
                                        <Button
                                            variant="outline"
                                            role="combobox"
                                            className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                        >
                                            {field.value ? orders?.results.find((o) => o.id === field.value)?.name ?? selectedOrder?.name ?? "Loading..." : "Select an order"}
                                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                        </Button>
                                    </FormControl>
                                </PopoverTrigger>
                                <PopoverContent className="w-[300px] p-0">
                                    <Command>
                                        <CommandInput value={search} onValueChange={setSearch}
                                                      placeholder="Search orders..."/>
                                        <CommandList>
                                            <CommandEmpty>No orders found.</CommandEmpty>
                                            <CommandGroup>
                                                {(orders?.results ?? []).map((order) => {
                                                    return (<CommandItem
                                                        key={order.id}
                                                        value={`${order.name} ${order.customer_first_name} ${order.customer_last_name}`}
                                                        onSelect={() => form.setValue("order", order.id)}
                                                    >
                                                        <Check
                                                            className={cn("mr-2 h-4 w-4", order.id === field.value ? "opacity-100" : "opacity-0")}
                                                        />
                                                        {order.name}
                                                    </CommandItem>)
                                                })}
                                            </CommandGroup>
                                        </CommandList>
                                    </Command>
                                </PopoverContent>
                            </Popover>
                            <FormMessage/>
                        </FormItem>)}
                    />

                    <FormField
                        control={form.control}
                        name="part_type"
                        render={({field}) => {
                            const selectedPartType = partTypes?.results.find(pt => pt.id === field.value)
                            return (<FormItem className="flex flex-col">
                                <FormLabel>Part Type *</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                            >
                                                {selectedPartType?.name ?? "Select a part type"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-[300px] p-0">
                                        <Command>
                                            <CommandInput
                                                value={partTypeSearch}
                                                onValueChange={setPartTypeSearch}
                                                placeholder="Search part types..."
                                            />
                                            <CommandList>
                                                <CommandEmpty>No part types found.</CommandEmpty>
                                                <CommandGroup>
                                                    {partTypes?.results.map((pt) => (<CommandItem
                                                        key={pt.id}
                                                        value={pt.name}
                                                        onSelect={() => {
                                                            form.setValue("part_type", pt.id)
                                                            setPartTypeSearch("")
                                                        }}
                                                    >
                                                        <Check
                                                            className={cn("mr-2 h-4 w-4", pt.id === field.value ? "opacity-100" : "opacity-0")}
                                                        />
                                                        {pt.name}
                                                    </CommandItem>))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormMessage/>
                            </FormItem>)
                        }}
                    />

                    {/* Process Selector - For filtering steps only, not part of form data */}
                    <div className="flex flex-col space-y-2">
                        <FormLabel>Process (for filtering steps)</FormLabel>
                        <Popover>
                            <PopoverTrigger asChild>
                                <Button 
                                    variant="outline" 
                                    role="combobox" 
                                    className={cn(
                                        "w-[300px] justify-between",
                                        !selectedPartType && "text-muted-foreground"
                                    )}
                                    disabled={!selectedPartType}
                                >
                                    {selectedProcess 
                                        ? processes?.results.find((p) => p.id === selectedProcess)?.name ?? "Loading..." 
                                        : selectedPartType ? "Select a process to filter steps" : "Select part type first"
                                    }
                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                </Button>
                            </PopoverTrigger>
                            <PopoverContent className="w-[300px] p-0">
                                <Command>
                                    <CommandInput placeholder="Search processes..."/>
                                    <CommandList>
                                        <CommandEmpty>No processes found.</CommandEmpty>
                                        <CommandGroup>
                                            {(processes?.results ?? []).map((process) => (
                                                <CommandItem
                                                    key={process.id}
                                                    value={process.name}
                                                    onSelect={() => setSelectedProcess(process.id)}
                                                >
                                                    <Check
                                                        className={cn(
                                                            "mr-2 h-4 w-4", 
                                                            process.id === selectedProcess ? "opacity-100" : "opacity-0"
                                                        )}
                                                    />
                                                    {process.name}
                                                </CommandItem>
                                            ))}
                                        </CommandGroup>
                                    </CommandList>
                                </Command>
                            </PopoverContent>
                        </Popover>
                        <FormDescription>
                            This helps filter the step choices. The process is determined automatically from the selected step.
                        </FormDescription>
                    </div>

                    <FormField
                        control={form.control}
                        name="step"
                        render={({field}) => (<FormItem className="flex flex-col">
                            <FormLabel>Step *</FormLabel>
                            <Popover>
                                <PopoverTrigger asChild>
                                    <FormControl>
                                        <Button
                                            variant="outline"
                                            role="combobox"
                                            className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                        >
                                            {field.value ? steps?.results.find((s) => s.id === field.value)?.description ?? "Loading..." : "Select a step"}
                                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                        </Button>
                                    </FormControl>
                                </PopoverTrigger>
                                <PopoverContent className="w-[300px] p-0">
                                    <Command>
                                        <CommandInput placeholder="Search steps..."/>
                                        <CommandList>
                                            <CommandEmpty>No steps found.</CommandEmpty>
                                            <CommandGroup>
                                                {steps?.results.map((step) => (<CommandItem
                                                    key={step.id}
                                                    value={String(step.id)} // use step.id, not name
                                                    onSelect={() => form.setValue("step", step.id)}
                                                >
                                                    <Check
                                                        className={cn("mr-2 h-4 w-4", field.value === step.id ? "opacity-100" : "opacity-0")}
                                                    />
                                                    {step.description}
                                                </CommandItem>))}
                                            </CommandGroup>
                                        </CommandList>
                                    </Command>
                                </PopoverContent>
                            </Popover>
                            <FormMessage/>
                        </FormItem>)}
                    />

                    <FormField
                        control={form.control}
                        name="work_order"
                        render={({field}) => {
                            const selected = workOrders?.results.find((wo) => wo.id === field.value);

                            return (<FormItem className="flex flex-col">
                                <FormLabel>Work Order</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                            >
                                                {selected ? selected.ERP_id : "Select a work order"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-[300px] p-0">
                                        <Command>
                                            <CommandInput
                                                value={workOrderSearch}
                                                onValueChange={setWorkOrderSearch}
                                                placeholder="Search work orders..."
                                            />
                                            <CommandList>
                                                <CommandEmpty>No work orders found.</CommandEmpty>
                                                <CommandGroup>
                                                    {workOrders?.results.map((wo) => (<CommandItem
                                                        key={wo.id}
                                                        value={wo.ERP_id}
                                                        onSelect={() => {
                                                            form.setValue("work_order", wo.id);
                                                            setWorkOrderSearch("");
                                                        }}
                                                    >
                                                        <Check
                                                            className={cn("mr-2 h-4 w-4", wo.id === field.value ? "opacity-100" : "opacity-0")}
                                                        />
                                                        {wo.ERP_id}
                                                    </CommandItem>))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormMessage/>
                            </FormItem>);
                        }}
                    />


                    <FormField
                        control={form.control}
                        name="archived"
                        render={({field}) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                <FormControl>
                                    <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel>Archived</FormLabel>
                                    <FormDescription>Is this part currently archived</FormDescription>
                                    <FormMessage/>
                                </div>
                            </FormItem>)}
                    />
                    <Button type="submit">Submit</Button>
                </form>
            </Form>

            {mode === "edit" && partId && (
                <div className="max-w-3xl mx-auto py-6">
                    <h3 className="text-lg font-semibold">Attach Documents</h3>
                    <DocumentUploader objectId={partId} contentType="parts"/>
                </div>)}
        </div>

    )
}