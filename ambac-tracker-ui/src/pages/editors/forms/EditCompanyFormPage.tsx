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
import { Textarea } from "@/components/ui/textarea";
import { useParams } from "@tanstack/react-router";

import { useRetrieveCompany } from "@/hooks/useRetrieveCompany";
import { useCreateCompanies } from "@/hooks/useCreateCompanies";
import { useUpdateCompanies } from "@/hooks/useUpdateCompanies";

const formSchema = z.object({
    name: z
        .string()
        .min(1, "Company name is required - please enter the official company name")
        .max(255, "Company name must be 255 characters or less"),
    description: z
        .string()
        .min(1, "Description is required - please provide details about the company's business, focus, or operations")
        .max(1000, "Description must be 1000 characters or less"),
    hubspot_api_id: z
        .string()
        .min(1, "HubSpot API ID is required - please enter the unique company ID from HubSpot CRM")
        .max(50, "HubSpot API ID must be 50 characters or less"),
});

export default function CompanyFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const companyId = params.id ? parseInt(params.id, 10) : undefined;

    const { data: company, isLoading: isLoadingCompany } = useRetrieveCompany(
        { params: { id: companyId! } },
        { enabled: mode === "edit" && !!companyId }
    );

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            description: "",
            hubspot_api_id: "",
        },
    });

    // Reset form when company data loads
    useEffect(() => {
        if (mode === "edit" && company) {
            form.reset({
                name: company.name || "",
                description: company.description || "",
                hubspot_api_id: company.hubspot_api_id || "",
            });
        }
    }, [mode, company, form]);

    const createCompany = useCreateCompanies();
    const updateCompany = useUpdateCompanies();

    function onSubmit(values: z.infer<typeof formSchema>) {
        const submitData = {
            name: values.name,
            description: values.description,
            hubspot_api_id: values.hubspot_api_id,
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
                                <FormLabel>Company Name *</FormLabel>
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
                                <FormLabel>Description *</FormLabel>
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
                        name="hubspot_api_id"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>HubSpot API ID *</FormLabel>
                                <FormControl>
                                    <Input
                                        placeholder="e.g. 12345678"
                                        {...field}
                                    />
                                </FormControl>
                                <FormDescription>
                                    The unique identifier for this company in HubSpot CRM
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