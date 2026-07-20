"use client";

import { useEffect } from "react";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useParams } from "@tanstack/react-router";

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
import { Switch } from "@/components/ui/switch";

import { useRetrieveJobRole } from "@/hooks/useRetrieveJobRole";
import { useCreateJobRole } from "@/hooks/useCreateJobRole";
import { useUpdateJobRole } from "@/hooks/useUpdateJobRole";
import { TrainingRequirementsEditor } from "@/components/training/TrainingRequirementsEditor";
import { schemas } from "@/lib/api/generated";

const formSchema = schemas.JobRoleRequest.pick({
    name: true,
    description: true,
    active: true,
});

type FormValues = z.infer<typeof formSchema>;

export default function EditJobRoleFormPage() {
    const params = useParams({ strict: false });
    const navigate = useNavigate();
    const roleId = (params as { roleId?: string }).roleId;
    const mode = roleId ? "edit" : "create";

    const { data: role, isLoading } = useRetrieveJobRole(roleId || "");

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: { name: "", description: "", active: true },
    });

    useEffect(() => {
        if (mode === "edit" && role) {
            form.reset({
                name: role.name ?? "",
                description: role.description ?? "",
                active: role.active ?? true,
            });
        }
    }, [mode, role, form]);

    const createRole = useCreateJobRole();
    const updateRole = useUpdateJobRole();

    function onSubmit(values: FormValues) {
        const submitData = {
            name: values.name,
            description: values.description || undefined,
            active: values.active,
        };
        if (mode === "edit" && roleId) {
            updateRole.mutate({ id: roleId, data: submitData }, {
                onSuccess: () => { toast.success("Job role updated."); navigate({ to: "/quality/training/roles" }); },
                onError: () => toast.error("Failed to update job role."),
            });
        } else {
            createRole.mutate(submitData as never, {
                onSuccess: () => { toast.success("Job role created."); navigate({ to: "/quality/training/roles" }); },
                onError: () => toast.error("Failed to create job role."),
            });
        }
    }

    if (mode === "edit" && isLoading) {
        return <div className="container mx-auto p-6">Loading...</div>;
    }

    return (
        <div className="container mx-auto max-w-2xl p-6">
            <h1 className="mb-6 text-2xl font-bold">{mode === "edit" ? "Edit Job Role" : "New Job Role"}</h1>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    <FormField
                        control={form.control}
                        name="name"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Name *</FormLabel>
                                <FormControl>
                                    <Input placeholder="e.g., CMM Inspector" {...field} />
                                </FormControl>
                                <FormDescription>The job role / position (distinct from permission groups).</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="description"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Description</FormLabel>
                                <FormControl>
                                    <Textarea placeholder="What this role does…" {...field} value={field.value ?? ""} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="active"
                        render={({ field }) => (
                            <FormItem className="flex items-center gap-3">
                                <FormControl>
                                    <Switch checked={field.value ?? true} onCheckedChange={field.onChange} />
                                </FormControl>
                                <FormLabel className="!mt-0">Active</FormLabel>
                            </FormItem>
                        )}
                    />

                    <div className="flex gap-4">
                        <Button type="submit" disabled={createRole.isPending || updateRole.isPending}>
                            {createRole.isPending || updateRole.isPending ? "Saving..." : mode === "edit" ? "Update Job Role" : "Create Job Role"}
                        </Button>
                        <Button type="button" variant="outline" onClick={() => navigate({ to: "/quality/training/roles" })}>
                            Cancel
                        </Button>
                    </div>
                </form>
            </Form>

            {mode === "edit" && roleId && (
                <div className="mt-8">
                    <TrainingRequirementsEditor scope={{ job_role: roleId }} />
                </div>
            )}
        </div>
    );
}
