"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { format } from "date-fns"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Calendar as CalendarIcon, Check, ChevronsUpDown } from "lucide-react"
import { Calendar } from "@/components/ui/calendar"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { useParams } from "@tanstack/react-router"

import { useRetrieveOrders } from '@/hooks/useRetrieveOrders'
import { useRetrieveProcesses } from '@/hooks/useRetrieveProcesses'
import { useCreateWorkOrder } from '@/hooks/useCreateWorkOrder'
import { useUpdateWorkOrder } from '@/hooks/useUpdateWorkOrder'
import { useRetrieveWorkOrder } from '@/hooks/useRetrieveWorkOrder'
import { schemas } from '@/lib/api/generated'
import { DocumentUploader } from "@/pages/editors/forms/DocumentUploader.tsx";
import { isFieldRequired } from '@/lib/zod-config'

const WORKORDER_STATUS = schemas.WorkOrderStatusEnum.options
const PRIORITY_OPTIONS = schemas.PriorityEnum.options

// Use generated schema fields with custom date handling
const formSchema = schemas.WorkOrderRequest.pick({
    ERP_id: true,
    workorder_status: true,
    priority: true,
    notes: true,
    related_order: true,
    process: true,
}).extend({
    // Override related_order to be string (UUID from select)
    related_order: z.string(),
    // Handle date separately since form uses Date object
    expected_completion: z.coerce.date(),
})

type FormValues = z.infer<typeof formSchema>

// Pre-compute required fields for labels
const required = {
    ERP_id: isFieldRequired(formSchema.shape.ERP_id),
    workorder_status: isFieldRequired(formSchema.shape.workorder_status),
    priority: isFieldRequired(formSchema.shape.priority),
    notes: isFieldRequired(formSchema.shape.notes),
    related_order: true, // Overridden to required
    process: isFieldRequired(formSchema.shape.process),
    expected_completion: true,
}

export default function WorkOrderFormPage() {
    const params = useParams({ strict: false })
    const mode = params.id ? "edit" : "create"
    const workOrderId = params.id

    const [search, setSearch] = useState("")
    const [processSearch, setProcessSearch] = useState("")
    const { data: orders } = useRetrieveOrders({ search })
    const { data: processes } = useRetrieveProcesses({ search: processSearch })

    const { data: workOrder } = useRetrieveWorkOrder(workOrderId!, { enabled: mode === "edit" && !!workOrderId })

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            ERP_id: "",
            workorder_status: undefined,
            priority: undefined,
            notes: "",
            related_order: undefined,
            process: undefined,
            expected_completion: new Date(),
        },
    })

    useEffect(() => {
        if (mode === "edit" && workOrder) {
            form.reset({
                ERP_id: workOrder.ERP_id ?? "",
                workorder_status: workOrder.workorder_status,
                priority: workOrder.priority ?? undefined,
                notes: workOrder.notes ?? "",
                related_order: workOrder.related_order,
                process: workOrder.process ?? undefined,
                expected_completion: workOrder.expected_completion ? new Date(workOrder.expected_completion) : new Date(),
            })
        }
    }, [mode, workOrder, form])

    const createWorkOrder = useCreateWorkOrder()
    const updateWorkOrder = useUpdateWorkOrder()

    function onSubmit(values: FormValues) {
        const payload = {
            ...values,
            process: values.process || null,
            expected_completion: values.expected_completion?.toISOString(),
        }

        if (mode === "edit" && workOrderId) {
            updateWorkOrder.mutate(
                { id: workOrderId, data: payload },
                {
                    onSuccess: () => toast.success("Work order updated successfully!"),
                    onError: () => toast.error("Failed to update the work order."),
                }
            )
        } else {
            createWorkOrder.mutate(payload, {
                onSuccess: () => {
                    toast.success("Work order created successfully!")
                    form.reset()
                },
                onError: () => toast.error("Failed to create the work order."),
            })
        }
    }


    return (
        <div>
        <Form {...form}>
            <h1 className="text-2xl font-bold tracking-tight mb-6">
                {mode === "edit" ? "Edit Work Order" : "Create Work Order"}
            </h1>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8 max-w-3xl mx-auto py-10">
                <div className="grid grid-cols-2 gap-4">
                    <FormField
                        control={form.control}
                        name="workorder_status"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel required={required.workorder_status}>Status</FormLabel>
                                <Select onValueChange={field.onChange} value={field.value}>
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select status"/>
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        {WORKORDER_STATUS.map((status) => (
                                            <SelectItem key={status} value={status}>
                                                {status.replace(/_/g, " ")}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <FormDescription>Current status of the work order</FormDescription>
                                <FormMessage/>
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="priority"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel required={required.priority}>Priority</FormLabel>
                                <Select onValueChange={(val) => field.onChange(parseInt(val, 10))} value={field.value?.toString()}>
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select priority"/>
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        {PRIORITY_OPTIONS.map((priority) => (
                                            <SelectItem key={priority} value={priority.toString()}>
                                                {priority === 1 ? "Urgent" : priority === 2 ? "High" : priority === 3 ? "Normal" : "Low"}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <FormDescription>Work order scheduling priority</FormDescription>
                                <FormMessage/>
                            </FormItem>
                        )}
                    />
                </div>

                <FormField
                    control={form.control}
                    name="ERP_id"
                    render={({field}) => (
                        <FormItem>
                            <FormLabel required={required.ERP_id}>ERP ID</FormLabel>
                            <FormControl>
                                <Input placeholder="Enter ERP ID" {...field} />
                            </FormControl>
                            <FormDescription>The ID of this workorder in the ERP system</FormDescription>
                            <FormMessage/>
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="notes"
                    render={({field}) => (
                        <FormItem>
                            <FormLabel required={required.notes}>Notes</FormLabel>
                            <FormControl>
                                <Textarea placeholder="Optional notes" className="resize-none" {...field} value={field.value ?? ""} />
                            </FormControl>
                            <FormDescription>Short notes for this current work order</FormDescription>
                            <FormMessage/>
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="related_order"
                    render={({field}) => {
                        const selectedOrder = orders?.results.find((o) => o.id === field.value)
                        return (
                            <FormItem className="flex flex-col">
                                <FormLabel required={required.related_order}>Related Order</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                            >
                                                {selectedOrder?.name || "Select an order"}
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
                                                    {orders?.results.map((order) => (
                                                        <CommandItem
                                                            key={order.id}
                                                            value={order.name}
                                                            onSelect={() => form.setValue("related_order", order.id)}
                                                        >
                                                            <Check
                                                                className={cn("mr-2 h-4 w-4", order.id === field.value ? "opacity-100" : "opacity-0")}
                                                            />
                                                            {order.name}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>The customer order this work order is attached to</FormDescription>
                                <FormMessage/>
                            </FormItem>
                        )
                    }}
                />

                <FormField
                    control={form.control}
                    name="process"
                    render={({ field }) => {
                        const selectedProcess = processes?.results.find((p) => p.id === field.value)
                        return (
                            <FormItem className="flex flex-col">
                                <FormLabel required={required.process}>Process</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                            >
                                                {selectedProcess?.name || "Select a process (optional)"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-[300px] p-0">
                                        <Command>
                                            <CommandInput
                                                value={processSearch}
                                                onValueChange={setProcessSearch}
                                                placeholder="Search processes..."
                                            />
                                            <CommandList>
                                                <CommandEmpty>No processes found.</CommandEmpty>
                                                <CommandGroup>
                                                    <CommandItem
                                                        onSelect={() => {
                                                            form.setValue("process", undefined)
                                                            setProcessSearch("")
                                                        }}
                                                    >
                                                        <Check
                                                            className={cn("mr-2 h-4 w-4", !field.value ? "opacity-100" : "opacity-0")}
                                                        />
                                                        No process
                                                    </CommandItem>
                                                    {processes?.results.map((process) => (
                                                        <CommandItem
                                                            key={process.id}
                                                            value={`${process.name}__${process.id}`}
                                                            onSelect={() => {
                                                                form.setValue("process", process.id)
                                                                setProcessSearch("")
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn("mr-2 h-4 w-4", process.id === field.value ? "opacity-100" : "opacity-0")}
                                                            />
                                                            {process.name}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>The manufacturing process this work order follows</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )
                    }}
                />

                <FormField
                    control={form.control}
                    name="expected_completion"
                    render={({field}) => (
                        <FormItem className="flex flex-col">
                            <FormLabel required={required.expected_completion}>Expected Completion Date</FormLabel>
                            <Popover>
                                <PopoverTrigger asChild>
                                    <FormControl>
                                        <Button
                                            variant="outline"
                                            className={cn(
                                                "w-[240px] pl-3 text-left font-normal",
                                                !field.value && "text-muted-foreground"
                                            )}
                                        >
                                            {field.value ? format(field.value, "PPP") : <span>Pick a date</span>}
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
                            <FormDescription>Date this workorder is expected to complete</FormDescription>
                            <FormMessage/>
                        </FormItem>
                    )}
                />

                <Button type="submit">Submit</Button>
            </form>
        </Form>

            {mode === "edit" && workOrderId && (
                <div className="max-w-3xl mx-auto py-6">
                    <h3 className="text-lg font-semibold">Attach Documents</h3>
                    <DocumentUploader objectId={workOrderId} contentType="workorder"/>
                </div>)}
        </div>
    )
}