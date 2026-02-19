"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMatchRoute, useNavigate } from '@tanstack/react-router';
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { format, formatDistanceToNow } from "date-fns";
import { CalendarIcon, Check, ChevronsUpDown, Send, ChevronDown, Eye, EyeOff } from "lucide-react";

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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command";
import { cn } from "@/lib/utils";

import { useRetrieveOrder } from '@/hooks/useRetrieveOrder';
import { useUpdateOrder } from '@/hooks/useUpdateOrder';
import { useCreateOrder } from '@/hooks/useCreateOrder';
import { useListHubspotGates } from '@/hooks/useListHubspotGates';
import { useRetrieveCustomers } from '@/hooks/useRetrieveCustomers';
import { useRetrieveCompanies } from '@/hooks/useRetrieveCompanies';
import { api, schemas } from '@/lib/api/generated';
import { ordersEditFormRoute } from "@/router";
import { DocumentUploader } from "@/pages/editors/forms/DocumentUploader";
import { isFieldRequired } from "@/lib/zod-config";

const ORDER_STATUS = schemas.OrdersStatusEnum.options;

// Use generated schema with form-specific overrides
// Note: customer_note is managed via notes timeline on OrderDetailsPage
const formSchema = schemas.OrdersRequest.pick({
    name: true,
    customer: true,
    order_status: true,
    company: true,
    current_hubspot_gate: true,
}).extend({
    // Form uses Date object, converted to string on submit
    estimated_completion: z.date().optional(),
    // Not in generated schema but needed for form
    archived: z.boolean().optional(),
});

type FormValues = z.infer<typeof formSchema>;

const required = {
    name: isFieldRequired(formSchema.shape.name),
    company: isFieldRequired(formSchema.shape.company),
    customer: isFieldRequired(formSchema.shape.customer),
};

export default function OrderFormPage() {
    const navigate = useNavigate();
    const matchRoute = useMatchRoute();
    const [companySearch, setCompanySearch] = useState("");
    const [customerSearch, setCustomerSearch] = useState("");
    const [companyOpen, setCompanyOpen] = useState(false);
    const [customerOpen, setCustomerOpen] = useState(false);
    const [newNote, setNewNote] = useState("");
    const [noteVisibility, setNoteVisibility] = useState<"visible" | "internal">("visible");
    const [notesExpanded, setNotesExpanded] = useState(false);
    const queryClient = useQueryClient();

    const isEditing = !!matchRoute({ to: ordersEditFormRoute.id, fuzzy: true });

    let orderId: string | undefined = undefined;
    if (isEditing) {
        const { id } = ordersEditFormRoute.useParams();
        orderId = id;
    }

    const { data: order, isLoading } = useRetrieveOrder(orderId ?? "", {
        enabled: !!orderId,
    });

    const { data: hubspotGates = [] } = useListHubspotGates({});
    const { data: customers = [] } = useRetrieveCustomers({
        search: customerSearch,
    });
    const { data: companies } = useRetrieveCompanies({
        search: companySearch,
    });

    const updateOrder = useUpdateOrder();
    const createOrder = useCreateOrder();

    // Add note mutation (only available in edit mode)
    const addNoteMutation = useMutation({
        mutationFn: async ({ message, visibility }: { message: string; visibility: string }) => {
            if (!orderId) throw new Error("Order ID required");
            return await api.api_Orders_add_note_create({
                params: { id: orderId },
                body: { message, visibility } as any,
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["order", orderId] });
            setNewNote("");
            toast.success("Note added");
        },
        onError: () => {
            toast.error("Failed to add note");
        },
    });

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            customer: undefined,
            estimated_completion: undefined,
            order_status: ORDER_STATUS[0],
            current_hubspot_gate: undefined,
            company: undefined,
            archived: false,
        },
    });

    // Reset form when order data loads
    useEffect(() => {
        if (isEditing && order) {
            form.reset({
                name: order.name || "",
                customer: order.customer ?? undefined,
                estimated_completion: order.estimated_completion ? new Date(order.estimated_completion) : undefined,
                order_status: order.order_status || ORDER_STATUS[0],
                current_hubspot_gate: order.current_hubspot_gate ?? undefined,
                company: order.company ?? undefined,
                archived: order.archived || false,
            });
        }
    }, [isEditing, order, form, hubspotGates.length]);

    function onSubmit(values: FormValues) {
        const submitData = {
            ...values,
            estimated_completion: values.estimated_completion ? format(values.estimated_completion, "yyyy-MM-dd") : undefined,
            current_hubspot_gate: values.current_hubspot_gate || undefined,
        };

        if (isEditing && orderId) {
            updateOrder.mutate(
                { id: orderId, newData: submitData },
                {
                    onSuccess: () => {
                        toast.success("Order updated successfully!");
                    },
                    onError: (err) => {
                        console.error("Update failed:", err);
                        toast.error("Failed to update order.");
                    },
                }
            );
        } else {
            createOrder.mutate(submitData, {
                onSuccess: (data) => {
                    toast.success("Order created successfully!");
                    navigate({ to: `/orders/${data.id}/edit` });
                },
                onError: (err) => {
                    console.error("Creation failed:", err);
                    toast.error("Failed to create order. Please check all required fields.");
                },
            });
        }
    }

    // Show loading state
    if (isEditing && isLoading) {
        return (
            <div className="max-w-4xl mx-auto py-10">
                <div className="animate-pulse">
                    <div className="h-8 bg-gray-200 rounded mb-4"></div>
                    <div className="h-4 bg-gray-200 rounded mb-8"></div>
                    <div className="h-32 bg-gray-200 rounded"></div>
                </div>
            </div>
        );
    }

    const selectedCustomer = customers?.find((c) => c.id === form.watch("customer"));
    const selectedCompany = companies?.results?.find((c) => c.id === form.watch("company"));

    return (
        <div className="max-w-4xl mx-auto py-10">
            <div className="mb-8">
                <h1 className="text-3xl font-bold">
                    {isEditing ? `Edit ${order?.name ?? `Order #${orderId}`}` : 'Create New Order'}
                </h1>
                <p className="text-muted-foreground">
                    {isEditing ? "Update the order information below" : "Create a new order in the system"}
                </p>
            </div>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    <FormField
                        control={form.control}
                        name="name"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.name}>Order Name</FormLabel>
                                <FormControl>
                                    <Input placeholder="e.g. Order #12345" {...field} />
                                </FormControl>
                                <FormDescription>
                                    A unique name or identifier for this order
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <FormField
                            control={form.control}
                            name="company"
                            render={({ field }) => (
                                <FormItem className="flex flex-col">
                                    <FormLabel required={required.company}>Company</FormLabel>
                                    <Popover open={companyOpen} onOpenChange={setCompanyOpen}>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    aria-expanded={companyOpen}
                                                    className={cn(
                                                        "w-full justify-between",
                                                        !field.value && "text-muted-foreground"
                                                    )}
                                                >
                                                    {selectedCompany
                                                        ? selectedCompany.name
                                                        : "Select company"}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-full p-0" align="start">
                                            <Command>
                                                <CommandInput
                                                    value={companySearch}
                                                    onValueChange={setCompanySearch}
                                                    placeholder="Search companies..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No companies found.</CommandEmpty>
                                                    <CommandGroup>
                                                        {companies?.results?.map((company) => (
                                                            <CommandItem
                                                                key={company.id}
                                                                value={company.name}
                                                                onSelect={() => {
                                                                    form.setValue("company", company.id);
                                                                    setCompanyOpen(false);
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn(
                                                                        "mr-2 h-4 w-4",
                                                                        company.id === field.value ? "opacity-100" : "opacity-0"
                                                                    )}
                                                                />
                                                                {company.name}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                    <FormDescription>
                                        The company placing this order
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="customer"
                            render={({ field }) => (
                                <FormItem className="flex flex-col">
                                    <FormLabel required={required.customer}>Customer</FormLabel>
                                    <Popover open={customerOpen} onOpenChange={setCustomerOpen}>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    aria-expanded={customerOpen}
                                                    className={cn(
                                                        "w-full justify-between",
                                                        !field.value && "text-muted-foreground"
                                                    )}
                                                >
                                                    {selectedCustomer
                                                        ? `${selectedCustomer.first_name} ${selectedCustomer.last_name}`
                                                        : "Select customer"}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-full p-0" align="start">
                                            <Command>
                                                <CommandInput
                                                    value={customerSearch}
                                                    onValueChange={setCustomerSearch}
                                                    placeholder="Search customers..."
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No customers found.</CommandEmpty>
                                                    <CommandGroup>
                                                        {customers?.map((customer) => (
                                                            <CommandItem
                                                                key={customer.id}
                                                                value={`${customer.first_name} ${customer.last_name}`}
                                                                onSelect={() => {
                                                                    form.setValue("customer", customer.id);
                                                                    setCustomerOpen(false);
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn(
                                                                        "mr-2 h-4 w-4",
                                                                        customer.id === field.value ? "opacity-100" : "opacity-0"
                                                                    )}
                                                                />
                                                                {`${customer.first_name} ${customer.last_name}`}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                    <FormDescription>
                                        The customer contact for this order
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    <FormField
                        control={form.control}
                        name="estimated_completion"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel>Estimated Completion</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant={"outline"}
                                                className={cn(
                                                    "w-full pl-3 text-left font-normal",
                                                    !field.value && "text-muted-foreground"
                                                )}
                                            >
                                                {field.value ? (
                                                    format(field.value, "PPP")
                                                ) : (
                                                    <span>Pick a date</span>
                                                )}
                                                <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-auto p-0" align="start">
                                        <Calendar
                                            mode="single"
                                            selected={field.value}
                                            onSelect={field.onChange}
                                            disabled={(date) =>
                                                date < new Date("2020-01-01")
                                            }
                                            initialFocus
                                        />
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>
                                    When this order is expected to be completed
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="order_status"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Order Status</FormLabel>
                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select order status" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        {ORDER_STATUS.map((status) => (
                                            <SelectItem key={status} value={status}>
                                                {status}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <FormDescription>
                                    Current status of this order
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="current_hubspot_gate"
                        render={({ field }) => {
                            const stringValue = field.value !== null && field.value !== undefined ? String(field.value) : "null";
                            return (
                                <FormItem>
                                    <FormLabel>Current HubSpot Gate</FormLabel>
                                    <Select
                                        key={`hubspot-gate-${stringValue}`}
                                        onValueChange={(value) => field.onChange(value === "null" ? null : Number(value))}
                                        defaultValue={stringValue}
                                    >
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select HubSpot gate" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            <SelectItem value="null">No gate selected</SelectItem>
                                            {hubspotGates.map((gate) => (
                                                <SelectItem key={gate.id} value={String(gate.id)}>
                                                    {gate.stage_name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <FormDescription>
                                        Current HubSpot pipeline gate
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            );
                        }}
                    />

                    <FormField
                        control={form.control}
                        name="archived"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                <FormControl>
                                    <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                                <div className="space-y-1 leading-none">
                                    <FormLabel>
                                        Archive Order
                                    </FormLabel>
                                    <FormDescription>
                                        Mark this order as archived. Archived orders are hidden from most views.
                                    </FormDescription>
                                </div>
                            </FormItem>
                        )}
                    />

                    {/* Notes Timeline - Only in edit mode */}
                    {isEditing && order && (
                        <Card>
                            <CardHeader className="pb-3">
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-base">Notes</CardTitle>
                                    {order.notes_timeline && (order.notes_timeline as any[]).length > 1 && (
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => setNotesExpanded(!notesExpanded)}
                                        >
                                            {notesExpanded ? "Show Latest" : `Show All (${(order.notes_timeline as any[]).length})`}
                                            <ChevronDown className={cn("h-4 w-4 ml-1 transition-transform", notesExpanded && "rotate-180")} />
                                        </Button>
                                    )}
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                {/* Add Note Input */}
                                <div className="flex gap-2">
                                    <Textarea
                                        placeholder="Add a note..."
                                        value={newNote}
                                        onChange={(e) => setNewNote(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === "Enter" && !e.shiftKey && newNote.trim()) {
                                                e.preventDefault();
                                                addNoteMutation.mutate({ message: newNote, visibility: noteVisibility });
                                            }
                                        }}
                                        className="flex-1 min-h-[60px] resize-none"
                                    />
                                    <div className="flex flex-col gap-2">
                                        <Button
                                            type="button"
                                            variant="outline"
                                            size="icon"
                                            onClick={() => setNoteVisibility(noteVisibility === "visible" ? "internal" : "visible")}
                                            title={noteVisibility === "visible" ? "Visible to customer" : "Internal only"}
                                        >
                                            {noteVisibility === "visible" ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                                        </Button>
                                        <Button
                                            type="button"
                                            size="icon"
                                            disabled={!newNote.trim() || addNoteMutation.isPending}
                                            onClick={() => addNoteMutation.mutate({ message: newNote, visibility: noteVisibility })}
                                        >
                                            <Send className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>

                                {/* Notes Timeline */}
                                {order.notes_timeline && (order.notes_timeline as any[]).length > 0 ? (
                                    <div className="space-y-3 pt-2 border-t">
                                        {(notesExpanded
                                            ? (order.notes_timeline as any[])
                                            : [order.latest_note]
                                        ).filter(Boolean).map((note: any, idx: number) => (
                                            <div key={idx} className="flex gap-3 text-sm">
                                                <div className="flex-shrink-0 w-2 h-2 mt-2 rounded-full bg-primary" />
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                                                        <span className="font-medium text-foreground">{note.user}</span>
                                                        <span>•</span>
                                                        <span>{note.timestamp ? formatDistanceToNow(new Date(note.timestamp), { addSuffix: true }) : ""}</span>
                                                        {note.visibility === "internal" && (
                                                            <span className="text-orange-500 flex items-center gap-1">
                                                                <EyeOff className="h-3 w-3" /> Internal
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="text-foreground whitespace-pre-wrap">{note.message}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-sm text-muted-foreground">No notes yet</p>
                                )}
                            </CardContent>
                        </Card>
                    )}

                    <div className="flex gap-4">
                        <Button
                            type="submit"
                            disabled={createOrder.isPending || updateOrder.isPending}
                            className="flex-1"
                        >
                            {isEditing
                                ? updateOrder.isPending
                                    ? "Saving..."
                                    : "Save Changes"
                                : createOrder.isPending
                                    ? "Creating..."
                                    : "Create Order"}
                        </Button>
                    </div>
                </form>
            </Form>

            {isEditing && orderId && (
                <div className="mt-8 space-y-4">
                    <h3 className="text-lg font-semibold">Attach Documents</h3>
                    <DocumentUploader objectId={orderId} contentType="orders" />
                </div>
            )}
        </div>
    );
}