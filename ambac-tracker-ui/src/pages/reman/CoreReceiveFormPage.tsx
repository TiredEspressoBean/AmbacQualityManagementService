import { useState } from "react";
import { useNavigate, Link } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api/generated";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { useRetrieveCustomers } from "@/hooks/useRetrieveCustomers";
import { ArrowLeft, Loader2, Package } from "lucide-react";
import { toast } from "sonner";

const formSchema = z.object({
    core_number: z.string().min(1, "Core number is required"),
    serial_number: z.string().optional(),
    core_type: z.string().min(1, "Core type is required"),
    received_date: z.string().min(1, "Received date is required"),
    customer: z.string().optional(),
    source_type: z.enum(["CUSTOMER_RETURN", "PURCHASED", "WARRANTY", "TRADE_IN"]),
    source_reference: z.string().optional(),
    condition_grade: z.enum(["A", "B", "C", "SCRAP"]),
    condition_notes: z.string().optional(),
    core_credit_value: z.string().optional(),
});

type FormData = z.infer<typeof formSchema>;

export function CoreReceiveFormPage() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Fetch part types for core type dropdown
    const { data: partTypesData } = useRetrievePartTypes({ limit: 100 });
    const partTypes = partTypesData?.results ?? [];

    // Fetch customers for dropdown
    const { data: customersData } = useRetrieveCustomers({ limit: 100 });
    const customers = customersData?.results ?? [];

    const form = useForm<FormData>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            core_number: "",
            serial_number: "",
            core_type: "",
            received_date: new Date().toISOString().split("T")[0],
            customer: "__none__",
            source_type: "CUSTOMER_RETURN",
            source_reference: "",
            condition_grade: "B",
            condition_notes: "",
            core_credit_value: "",
        },
    });

    const createMutation = useMutation({
        mutationFn: (data: FormData) => {
            const payload: any = {
                ...data,
                core_credit_value: data.core_credit_value ? data.core_credit_value : null,
                customer: data.customer && data.customer !== "__none__" ? data.customer : null,
            };
            return api.api_Cores_create(payload);
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ["cores"] });
            toast.success("Core received successfully");
            navigate({ to: `/reman/cores/${data.id}` });
        },
        onError: (error: any) => {
            toast.error(error?.message || "Failed to receive core");
            setIsSubmitting(false);
        },
    });

    const onSubmit = (data: FormData) => {
        setIsSubmitting(true);
        createMutation.mutate(data);
    };

    return (
        <div className="max-w-2xl mx-auto space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" asChild>
                    <Link to="/reman/cores">
                        <ArrowLeft className="h-4 w-4" />
                    </Link>
                </Button>
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        <Package className="h-6 w-6" />
                        Receive Core
                    </h1>
                    <p className="text-muted-foreground">
                        Log an incoming core for remanufacturing
                    </p>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Core Information</CardTitle>
                    <CardDescription>
                        Enter the details of the incoming core
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <FormField
                                    control={form.control}
                                    name="core_number"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Core Number *</FormLabel>
                                            <FormControl>
                                                <Input placeholder="CORE-001" {...field} />
                                            </FormControl>
                                            <FormDescription>
                                                Unique identifier for this core
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="serial_number"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Serial Number</FormLabel>
                                            <FormControl>
                                                <Input placeholder="OEM serial if available" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <FormField
                                control={form.control}
                                name="core_type"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Core Type *</FormLabel>
                                        <Select onValueChange={field.onChange} value={field.value}>
                                            <FormControl>
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select core type" />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                {partTypes.map((pt: any) => (
                                                    <SelectItem key={pt.id} value={pt.id}>
                                                        {pt.name}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <div className="grid grid-cols-2 gap-4">
                                <FormField
                                    control={form.control}
                                    name="source_type"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Source Type *</FormLabel>
                                            <Select onValueChange={field.onChange} value={field.value}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    <SelectItem value="CUSTOMER_RETURN">Customer Return</SelectItem>
                                                    <SelectItem value="PURCHASED">Purchased Core</SelectItem>
                                                    <SelectItem value="WARRANTY">Warranty Return</SelectItem>
                                                    <SelectItem value="TRADE_IN">Trade-In</SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="source_reference"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Reference Number</FormLabel>
                                            <FormControl>
                                                <Input placeholder="RMA, PO, or other reference" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <FormField
                                    control={form.control}
                                    name="customer"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Customer</FormLabel>
                                            <Select onValueChange={field.onChange} value={field.value}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select customer (optional)" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    <SelectItem value="__none__">No customer</SelectItem>
                                                    {customers.map((c: any) => (
                                                        <SelectItem key={c.id} value={c.id}>
                                                            {c.name}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="received_date"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Received Date *</FormLabel>
                                            <FormControl>
                                                <Input type="date" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <FormField
                                    control={form.control}
                                    name="condition_grade"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Condition Grade *</FormLabel>
                                            <Select onValueChange={field.onChange} value={field.value}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    <SelectItem value="A">Grade A - Excellent</SelectItem>
                                                    <SelectItem value="B">Grade B - Good</SelectItem>
                                                    <SelectItem value="C">Grade C - Fair</SelectItem>
                                                    <SelectItem value="scrap">Scrap - Not Usable</SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="core_credit_value"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Credit Value ($)</FormLabel>
                                            <FormControl>
                                                <Input
                                                    type="number"
                                                    step="0.01"
                                                    placeholder="0.00"
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormDescription>
                                                Core credit to be issued
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <FormField
                                control={form.control}
                                name="condition_notes"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Condition Notes</FormLabel>
                                        <FormControl>
                                            <Textarea
                                                placeholder="Describe the condition of the core..."
                                                rows={3}
                                                {...field}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <div className="flex justify-end gap-4">
                                <Button type="button" variant="outline" asChild>
                                    <Link to="/reman/cores">Cancel</Link>
                                </Button>
                                <Button type="submit" disabled={isSubmitting}>
                                    {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    Receive Core
                                </Button>
                            </div>
                        </form>
                    </Form>
                </CardContent>
            </Card>
        </div>
    );
}

export default CoreReceiveFormPage;
