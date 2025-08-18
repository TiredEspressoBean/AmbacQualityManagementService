"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMatchRoute, useNavigate } from '@tanstack/react-router';
import { format } from "date-fns";
import { CalendarIcon, Check, ChevronsUpDown } from "lucide-react";

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
import { schemas } from '@/lib/api/generated';
import { ordersEditFormRoute } from "@/router";
import { DocumentUploader } from "@/pages/editors/forms/DocumentUploader";

const ORDER_STATUS = schemas.OrderStatusEnum.options;

const formSchema = z.object({
    name: z.string().min(1, "Order name is required"),
    customer: z.number().min(1, "Customer is required"),
    customer_note: z.string().optional(),
    estimated_completion: z.date().optional(),
    order_status: z.enum(ORDER_STATUS as [string, ...string[]]),
    current_hubspot_gate: z.number().nullable().optional(),
    company: z.number().min(1, "Company is required"),
    archived: z.boolean().optional(),
});

export default function OrderFormPage() {
    const navigate = useNavigate();
    const matchRoute = useMatchRoute();
    const [companySearch, setCompanySearch] = useState("");
    const [customerSearch, setCustomerSearch] = useState("");
    const [companyOpen, setCompanyOpen] = useState(false);
    const [customerOpen, setCustomerOpen] = useState(false);

    const isEditing = !!matchRoute({ to: ordersEditFormRoute.id, fuzzy: true });

    let orderId: number | undefined = undefined;
    if (isEditing) {
        const { id } = ordersEditFormRoute.useParams();
        orderId = Number(id);
    }

    const { data: order, isLoading } = useRetrieveOrder(orderId ?? 0, {
        enabled: !!orderId,
    });

    const { data: hubspotGates = [] } = useListHubspotGates({});
    const { data: customers = [] } = useRetrieveCustomers({
        queries: { search: customerSearch },
    });
    const { data: companies } = useRetrieveCompanies({
        queries: { search: companySearch },
    });

    const updateOrder = useUpdateOrder();
    const createOrder = useCreateOrder();

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            customer: 0,
            customer_note: "",
            estimated_completion: undefined,
            order_status: ORDER_STATUS[0],
            current_hubspot_gate: undefined,
            company: 0,
            archived: false,
        },
    });

    // Reset form when order data loads
    useEffect(() => {
        if (isEditing && order) {
            form.reset({
                name: order.name || "",
                customer: order.customer || 0,
                customer_note: order.customer_note || "",
                estimated_completion: order.estimated_completion ? new Date(order.estimated_completion) : undefined,
                order_status: order.order_status || ORDER_STATUS[0],
                current_hubspot_gate: order.current_hubspot_gate || undefined,
                company: order.company || 0,
                archived: order.archived || false,
            });
        }
    }, [isEditing, order, form]);

    function onSubmit(values: z.infer<typeof formSchema>) {
        const submitData = {
            ...values,
            customer_note: values.customer_note || undefined,
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
                                <FormLabel>Order Name *</FormLabel>
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
                                    <FormLabel>Company *</FormLabel>
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
                                    <FormLabel>Customer *</FormLabel>
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
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Current HubSpot Gate</FormLabel>
                                <Select 
                                    onValueChange={(value) => field.onChange(value === "null" ? undefined : Number(value))}
                                    value={field.value ? String(field.value) : "null"}
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
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="customer_note"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Customer Notes</FormLabel>
                                <FormControl>
                                    <Textarea
                                        placeholder="Any special requirements or notes about this order..."
                                        className="min-h-[100px]"
                                        {...field}
                                    />
                                </FormControl>
                                <FormDescription>
                                    Notes to pass to the customer
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
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