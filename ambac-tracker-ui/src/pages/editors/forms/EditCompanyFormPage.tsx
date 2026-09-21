import { useEffect } from "react";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useParams } from "@tanstack/react-router";

import { useRetrieveCompany } from "@/hooks/useRetrieveCompany";
import { useCreateCompanies } from "@/hooks/useCreateCompanies";
import { useUpdateCompanies } from "@/hooks/useUpdateCompanies";
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";

// Use generated schema directly - error messages handled by global error map
const formSchema = schemas.CompanyRequest.pick({
    name: true,
    description: true,
    // Tier 2 of the outside-process turnaround chain: step override → THIS supplier
    // default → tenant default → 7 days. Turnaround is a property of the vendor, so
    // this is its natural home; without it a planner can only set it per step.
    default_outside_process_turnaround_days: true,
    // This customer's standing arrangement for cores they send in. Receiving
    // inherits it, so without an edit surface here the inheritance chain has
    // nothing to inherit FROM and every receipt falls back to EXCHANGE.
    default_core_fulfilment_mode: true,
});

// "" and null both reach us for an unset arrangement (blank=True, null=True).
// The Select needs one sentinel, and neither empty string nor null can be a
// SelectItem value, so UNSET stands in for both and maps back to null on save.
const UNSET = "__unset__";

type FormValues = z.infer<typeof formSchema>;

// Pre-compute required fields for labels
const required = {
    name: isFieldRequired(formSchema.shape.name),
    description: isFieldRequired(formSchema.shape.description),
};

export default function CompanyFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const companyId = params.id;

    const { data: company, isLoading: isLoadingCompany } = useRetrieveCompany(
        { params: { id: companyId! } },
        { enabled: mode === "edit" && !!companyId }
    );

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            description: "",
            default_outside_process_turnaround_days: null,
            default_core_fulfilment_mode: null,
        },
    });

    // Reset form when company data loads
    useEffect(() => {
        if (mode === "edit" && company) {
            form.reset({
                name: company.name || "",
                description: company.description || "",
                // Both of these were missing: the form loaded blank over real
                // values, so opening a company and saving it cleared them.
                default_outside_process_turnaround_days:
                    company.default_outside_process_turnaround_days ?? null,
                default_core_fulfilment_mode:
                    company.default_core_fulfilment_mode || null,
            });
        }
    }, [mode, company, form]);

    const createCompany = useCreateCompanies();
    const updateCompany = useUpdateCompanies();

    function onSubmit(values: FormValues) {
        const submitData = {
            name: values.name,
            description: values.description,
            // Previously omitted, which meant the turnaround input on this form
            // was decorative — it rendered, and nothing it held was ever sent.
            default_outside_process_turnaround_days:
                values.default_outside_process_turnaround_days ?? null,
            default_core_fulfilment_mode: values.default_core_fulfilment_mode || null,
        };

        if (mode === "edit" && companyId) {
            updateCompany.mutate(
                { id: companyId, data: submitData },
                {
                    onSuccess: () => {
                        toast.success("Company updated successfully!");
                    },
                    onError: (err) => {
                        console.error("Update failed:", err);
                        toast.error("Failed to update company.");
                    },
                }
            );
        } else {
            createCompany.mutate(submitData, {
                onSuccess: () => {
                    toast.success("Company created successfully!");
                    form.reset();
                },
                onError: (err) => {
                    console.error("Creation failed:", err);
                    toast.error("Failed to create company.");
                },
            });
        }
    }

    // Show loading state
    if (mode === "edit" && isLoadingCompany) {
        return (
            <div className="max-w-3xl mx-auto py-10">
                <div className="animate-pulse">
                    <div className="h-8 bg-gray-200 rounded mb-4"></div>
                    <div className="h-4 bg-gray-200 rounded mb-8"></div>
                    <div className="h-32 bg-gray-200 rounded"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto py-10">
            <div className="mb-8">
                <h1 className="text-3xl font-bold">
                    {mode === "edit" ? "Edit Company" : "Create Company"}
                </h1>
                <p className="text-muted-foreground">
                    {mode === "edit"
                        ? "Update the company information below"
                        : "Add a new company to the system"
                    }
                </p>
            </div>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    <FormField
                        control={form.control}
                        name="name"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.name}>Company Name</FormLabel>
                                <FormControl>
                                    <Input
                                        placeholder="e.g. Acme Manufacturing Corp"
                                        {...field}
                                    />
                                </FormControl>
                                <FormDescription>
                                    The official name of the company
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="description"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.description}>Description</FormLabel>
                                <FormControl>
                                    <Textarea
                                        placeholder="Describe the company, its business focus, location, or other relevant details..."
                                        className="min-h-[100px]"
                                        {...field}
                                    />
                                </FormControl>
                                <FormDescription>
                                    Detailed description of the company and its operations
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="default_outside_process_turnaround_days"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Outside-process turnaround (days)</FormLabel>
                                <FormControl>
                                    <Input
                                        type="number"
                                        min={1}
                                        placeholder="Leave blank to use the site default"
                                        value={field.value ?? ""}
                                        onChange={(e) => field.onChange(
                                            e.target.value === "" ? null : Number(e.target.value)
                                        )}
                                    />
                                </FormControl>
                                <FormDescription>
                                    Calendar days from ship-out to return when this company runs a
                                    subcontract operation. Used unless the step sets its own; a
                                    shipped part's promised return date overrides both.
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="default_core_fulfilment_mode"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Core fulfilment arrangement</FormLabel>
                                <Select
                                    value={field.value || UNSET}
                                    onValueChange={(v) => {
                                        // Radix emits "" on mount, before the
                                        // content is mounted to match the value
                                        // against — which lands AFTER the reset
                                        // above and silently blanked the loaded
                                        // arrangement. No SelectItem carries "",
                                        // so it is never a real choice.
                                        if (!v) return;
                                        field.onChange(v === UNSET ? null : v);
                                    }}
                                >
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        <SelectItem value={UNSET}>
                                            Not recorded
                                        </SelectItem>
                                        <SelectItem value="EXCHANGE">
                                            Exchange — they get a unit from stock
                                        </SelectItem>
                                        <SelectItem value="REPAIR_RETURN">
                                            Repair &amp; return — their own unit goes back
                                        </SelectItem>
                                    </SelectContent>
                                </Select>
                                <FormDescription>
                                    What happens to cores this customer sends in. Receiving
                                    proposes this for each core, and says it came from the
                                    customer's arrangement rather than a default. Leave it
                                    unrecorded rather than guessing: a repair-and-return unit
                                    received as an exchange has its components pooled, and the
                                    customer's own unit can then never be reassembled.
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className="flex gap-4">
                        <Button
                            type="submit"
                            disabled={createCompany.isPending || updateCompany.isPending}
                            className="flex-1"
                        >
                            {mode === "edit"
                                ? updateCompany.isPending
                                    ? "Saving..."
                                    : "Save Changes"
                                : createCompany.isPending
                                    ? "Creating..."
                                    : "Create Company"}
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    );
}