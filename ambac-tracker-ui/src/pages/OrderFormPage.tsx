// Enhanced OrderFormPage with TanStack Form best practices, UX improvements, and modularity placeholders

import {useMatchRoute, useNavigate} from '@tanstack/react-router';
import {useEffect} from 'react';
import {useForm} from '@tanstack/react-form';
import {useListHubspotGates} from '@/hooks/useListHubspotGates';
import {Popover, PopoverTrigger, PopoverContent} from '@/components/ui/popover.tsx';
import {Checkbox} from '@/components/ui/checkbox';
import {Command, CommandEmpty, CommandList, CommandItem, CommandInput} from '@/components/ui/command';
import {Calendar} from "@/components/ui/calendar";
import {useRetrieveOrder} from '@/hooks/useRetrieveOrder';
import {useUpdateOrder} from '@/hooks/useUpdateOrder';
import {useCreateOrder} from '@/hooks/useCreateOrder';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {Textarea} from '@/components/ui/textarea';
import {Skeleton} from '@/components/ui/skeleton';
import {toast} from 'sonner';
import {schemas} from '@/lib/api/generated.ts';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select.tsx';
import {ChevronsUpDown, Check, CalendarIcon} from 'lucide-react';
import {useRetrieveCustomers} from '@/hooks/useRetrieveCustomers.ts';
import {useRetrieveCompanies} from '@/hooks/useRetrieveCompanies.ts';
import {format} from "date-fns";
import {cn} from "@/lib/utils.ts";
import {z} from "zod";
import {ordersEditFormRoute} from "@/router.tsx";
import {DocumentUploader} from "@/pages/editors/forms/DocumentUploader.tsx";

const ORDER_STATUS = schemas.OrderStatusEnum.options;

type OrderFormValues = z.infer<typeof schemas.PatchedOrdersRequest>

export default function OrderFormPage() {
    const navigate = useNavigate();


    const matchRoute = useMatchRoute();

    const isEditing = !!matchRoute({ to: ordersEditFormRoute.id, fuzzy: true });

    let orderId: number | undefined = undefined;
    if (isEditing) {
        const { id } = ordersEditFormRoute.useParams();
        orderId = Number(id);
    }

    const {data: hubspotGates = []} = useListHubspotGates({});
    const {data: customers = []} = useRetrieveCustomers({});
    const {data: companies = []} = useRetrieveCompanies({});

    const {data: order, isLoading} = useRetrieveOrder(orderId ?? 0, {
        enabled: !!orderId,
    });

    const updateOrder = useUpdateOrder();
    const createOrder = useCreateOrder();

    const form = useForm({
        defaultValues: {
            name: '',
            customer: undefined,
            customer_note: '',
            estimated_completion: order?.estimated_completion
                ? new Date(order.estimated_completion)
                : undefined,
            status: ORDER_STATUS[0],
            hubspot_deal_id: '',
            current_hubspot_gate: undefined,
            company: undefined,
            last_synced_hubspot_stage: '',
            archived: false,
        } as OrderFormValues,
        onSubmit: async ({ value }) => {
            const parsed = {
                ...value,
                estimated_completion: value.estimated_completion
                    ? value.estimated_completion
                    : undefined,
            };

            const result = schemas.PatchedOrdersRequest.safeParse(parsed);
            if (!result.success) {
                console.log("Validation failed", result.error.format());
                toast.error("Validation failed. Please check the form fields.");
                return result.error.format(); // required!
            }

            const payload = {
                id: orderId as number,
                newData: {
                    ...parsed,
                },
            };

            if (isEditing) {
                updateOrder.mutate(payload, {
                    onSuccess: () => toast.success('Order updated!'),
                    onError: (e) => {
                        console.log(e)
                        toast.error('Failed to update order')
                    },
                });
            } else {
                createOrder.mutate(payload.newData, {
                    // TODO: Throw some manual validation in here for customers and such
                    onSuccess: (data) => {
                        toast.success('Order created!');
                        navigate({ to: `/orders/${data.id}/edit` });
                    },
                    onError: () => toast.error('Double check to make sure your fields are filled, namely customer company and name.'),
                });
            }
        },
    });

    useEffect(() => {
        if (isEditing && order) {
            form.update({
                defaultValues: {
                    name: order.name ?? '',
                    customer: order.customer ?? 0,
                    customer_note: order.customer_note ?? '',
                    company: order.company ?? null,
                    estimated_completion: order.estimated_completion,
                    order_status: order.order_status ?? ORDER_STATUS[0],
                    current_hubspot_gate: order.current_hubspot_gate ?? null,
                    last_synced_hubspot_stage: order.last_synced_hubspot_stage ?? '',
                    archived: order.archived ?? false,
                },
            });
        }
    }, [order, isEditing]);

    if (isEditing && isLoading) return <Skeleton className="h-32 w-full"/>;

    return (<div className="space-y-6 p-6 max-w-4xl mx-auto">
        <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold">
                {isEditing ? `Edit ${order?.name ?? `Order #${orderId}`}` : 'Create New Order'}
            </h1>
        </div>

        <form
            onSubmit={async (e) => {
                e.preventDefault();
                await form.handleSubmit(); // await is required
            }}
            className="space-y-6"
        >
            {/* General Info Section */}
            <section className="space-y-4">
                <h2 className="text-xl font-semibold">General Info</h2>

                <form.Field name="name">
                    {(field) => (<div className="space-y-1">
                        <label className="text-sm font-medium text-gray-700">Order Name</label>
                        <Input
                            value={field.state.value ?? ''}
                            onChange={(e) => field.handleChange(e.target.value)}
                            placeholder="Order Name"
                        />
                    </div>)}
                </form.Field>

                <form.Field name="estimated_completion">
                    {(field) => {
                        const date = field.state.value ? new Date(field.state.value) : null;

                        return (
                            <div className="space-y-1">
                                <label className="text-sm font-medium text-gray-700">Estimated Completion</label>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <Button
                                            variant="outline"
                                            className={cn(
                                                "w-full justify-start text-left font-normal",
                                                !date && "text-muted-foreground"
                                            )}
                                        >
                                            <CalendarIcon className="mr-2 h-4 w-4"/>
                                            {date ? format(date, "PPP") : "Pick a date"}
                                        </Button>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-auto p-0" align="start">
                                        <Calendar
                                            mode="single"
                                            selected={date ?? undefined}
                                            onSelect={(selectedDate) => {
                                                if (selectedDate) {
                                                    field.handleChange(selectedDate.toISOString());
                                                }
                                            }}
                                        />
                                    </PopoverContent>
                                </Popover>
                            </div>
                        );
                    }}
                </form.Field>

                <form.Field name="customer_note">
                    {(field) => (<div className="space-y-1">
                        <label className="text-sm font-medium text-gray-700">Customer Notes</label>
                        <Textarea
                            value={field.state.value ?? ''}
                            onChange={(e) => field.handleChange(e.target.value)}
                            placeholder="Customer Notes"
                        />
                    </div>)}
                </form.Field>

                <form.Field name="order_status">
                    {(field) => {
                        return (
                            <div className="space-y-1">
                                <label className="text-sm font-medium text-gray-700">Status</label>
                                <Select
                                    key={`status-${field.state.value}`} // Force re-render when value changes
                                    value={field.state.value || ORDER_STATUS[0]} // ensure it's not ''
                                    onValueChange={(val) => {
                                        field.handleChange(val as (typeof ORDER_STATUS)[number]);
                                    }}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select a status">
                                            {field.state.value || ORDER_STATUS[0]}
                                        </SelectValue>
                                    </SelectTrigger>
                                    <SelectContent>
                                        {ORDER_STATUS.map((status) => (
                                            <SelectItem key={status} value={status}>
                                                {status}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        );
                    }}
                </form.Field>


                <form.Field name="current_hubspot_gate">
                    {(field) => {
                        const selectedGate = hubspotGates.find(g => g.id === field.state.value);

                        return (
                            <div className="space-y-1">
                                <label className="text-sm font-medium text-gray-700">Current Hubspot Gate</label>
                                <Select
                                    value={field.state.value ? String(field.state.value) : ''}
                                    onValueChange={(val) => {
                                        const id = parseInt(val, 10);
                                        field.handleChange(isNaN(id) ? null : id);
                                    }}
                                >
                                    <SelectTrigger>
                                        {selectedGate?.stage_name || "Select a gate"}
                                    </SelectTrigger>
                                    <SelectContent>
                                        {hubspotGates.map((gate) => (
                                            <SelectItem key={gate.id} value={String(gate.id)}>
                                                {gate.stage_name}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        );
                    }}
                </form.Field>


                <form.Field name="last_synced_hubspot_stage">
                    {(field) => (<div className="space-y-1">
                        <label className="text-sm font-medium text-gray-700">Last Synced Hubspot Stage</label>
                        <Input
                            value={field.state.value ?? ''}
                            readOnly
                            disabled
                            onChange={(e) => field.handleChange(e.target.value)}
                            placeholder="Last Synced HubSpot Stage"
                        />
                    </div>)}
                </form.Field>


                <form.Field name="archived">
                    {(field) => (
                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="archived"
                                checked={field.state.value}
                                onCheckedChange={(checked) => field.handleChange(!!checked)}
                            />
                            <label htmlFor="archived" className="text-sm font-medium text-gray-700">
                                Archived
                            </label>
                        </div>
                    )}
                </form.Field>

                <form.Field name="company">
                    {(field) => {
                        const selected = companies.find((c) => c.id === field.state.value);

                        // Show skeleton while loading in edit mode and company ID is set but not resolved
                        if (
                            isEditing &&
                            typeof field.state.value === "number" &&
                            !selected &&
                            isLoading
                        ) {
                            return <Skeleton className="h-10 w-full" />;
                        }
                        return (<div className="space-y-1">
                            <label className="text-sm font-medium text-gray-700">Company</label>
                            <Popover>
                                <PopoverTrigger asChild>
                                    <Button variant="outline" role="combobox"
                                            className="w-full justify-between">
                                        {selected ? selected.name : 'Select company'}
                                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                    </Button>
                                </PopoverTrigger>
                                <PopoverContent className="p-0">
                                    <Command
                                        filter={(value, search) =>
                                            value.toLowerCase().includes(search.toLowerCase()) ? 1 : 0
                                        }>
                                        <CommandInput placeholder="Search company..."/>
                                        <CommandEmpty>No company found.</CommandEmpty>
                                        <CommandList>
                                            {companies.map(company => (<CommandItem
                                                key={company.id}
                                                value={company.name}
                                                onSelect={() => field.handleChange(company.id)}
                                            >
                                                <Check
                                                    className={
                                                        company.id === field.state.value
                                                            ? "mr-2 h-4 w-4 opacity-100"
                                                            : "mr-2 h-4 w-4 opacity-0"
                                                    }
                                                />
                                                {company.name}
                                            </CommandItem>))}
                                        </CommandList>
                                    </Command>
                                </PopoverContent>
                            </Popover>
                        </div>);

                    }}
                </form.Field>

                <form.Field name="customer">
                    {(field) => {
                        const selected = customers.find(c => c.id === field.state.value);
                        return (
                            <div className="space-y-1">
                                <label className="text-sm font-medium text-gray-700">Customer</label>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <Button variant="outline" role="combobox"
                                                className="w-full justify-between">
                                            {selected ? `${selected.first_name} ${selected.last_name}` : 'Select customer'}
                                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                        </Button>
                                    </PopoverTrigger>
                                    <PopoverContent className="p-0">
                                        <Command
                                            filter={(value, search) =>
                                                value.toLowerCase().includes(search.toLowerCase()) ? 1 : 0
                                            }>
                                            <CommandInput placeholder="Search customer..."/>
                                            <CommandEmpty>No customer found.</CommandEmpty>
                                            <CommandList>
                                                {customers.map(customer => {
                                                    const fullName = `${customer.first_name} ${customer.last_name}`;
                                                    return (
                                                        <CommandItem
                                                            key={customer.id}
                                                            value={fullName}
                                                            onSelect={() => field.handleChange(customer.id)}
                                                        >
                                                            <Check
                                                                className={
                                                                    customer.id === field.state.value
                                                                        ? "mr-2 h-4 w-4 opacity-100"
                                                                        : "mr-2 h-4 w-4 opacity-0"
                                                                }
                                                            />
                                                            {fullName}
                                                        </CommandItem>
                                                    );
                                                })}
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                            </div>);
                    }}
                </form.Field>
            </section>

            <Button type="submit" disabled={form.state.isSubmitting}>
                {form.state.isSubmitting ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Order'}
            </Button>
        </form>


        {isEditing && orderId && (<div className="space-y-2">
            <h3 className="text-lg font-semibold">Attach Documents</h3>
            <DocumentUploader objectId={orderId} contentType="orders"/>
        </div>)}
    </div>);
}