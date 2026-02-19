"use client";

import { useEffect, useState } from "react";
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
import { Checkbox } from "@/components/ui/checkbox";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useParams } from "@tanstack/react-router";

import { useRetrieveApprovalTemplate } from "@/hooks/useRetrieveApprovalTemplate";
import { useCreateApprovalTemplate } from "@/hooks/useCreateApprovalTemplate";
import { useUpdateApprovalTemplate } from "@/hooks/useUpdateApprovalTemplate";
import { useRetrieveGroups } from "@/hooks/useRetrieveGroups";
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";

// Pull enum options from generated schema
const APPROVAL_TYPES = schemas.ApprovalTypeEnum.options;
const APPROVAL_FLOWS = schemas.ApprovalFlowTypeEnum.options;
const SEQUENCE_TYPES = schemas.ApprovalSequenceEnum.options;
const DELEGATION_POLICIES = schemas.DelegationPolicyEnum.options;

// Convert SNAKE_CASE to Title Case (e.g., "DOCUMENT_RELEASE" -> "Document Release")
const toTitleCase = (value: string) =>
    value.toLowerCase().replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

// Use generated schema - error messages handled by global error map
const formSchema = schemas.ApprovalTemplateRequest.pick({
    template_name: true,
    approval_type: true,
    approval_flow_type: true,
    approval_sequence: true,
    delegation_policy: true,
    allow_self_approval: true,
    default_due_days: true,
    escalation_days: true,
    default_threshold: true,
    auto_assign_by_role: true,
});

type FormValues = z.infer<typeof formSchema>;

// Pre-compute required fields for labels
const required = {
    template_name: isFieldRequired(formSchema.shape.template_name),
    approval_type: isFieldRequired(formSchema.shape.approval_type),
    approval_flow_type: isFieldRequired(formSchema.shape.approval_flow_type),
    approval_sequence: isFieldRequired(formSchema.shape.approval_sequence),
    delegation_policy: isFieldRequired(formSchema.shape.delegation_policy),
    allow_self_approval: isFieldRequired(formSchema.shape.allow_self_approval),
    default_due_days: isFieldRequired(formSchema.shape.default_due_days),
    escalation_days: isFieldRequired(formSchema.shape.escalation_days),
    default_threshold: isFieldRequired(formSchema.shape.default_threshold),
    auto_assign_by_role: isFieldRequired(formSchema.shape.auto_assign_by_role),
};

export default function ApprovalTemplateFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const templateId = params.id;

    const { data: template, isLoading: isLoadingTemplate } = useRetrieveApprovalTemplate(
        { params: { id: templateId! } },
        { enabled: mode === "edit" && !!templateId }
    );

    const [groupSearch, setGroupSearch] = useState("");
    const [groupPopoverOpen, setGroupPopoverOpen] = useState(false);

    const { data: groups } = useRetrieveGroups();
    const groupsList = Array.isArray(groups?.results) ? groups.results : groups?.results || [];

    // Filter groups based on search
    const filteredGroups = groupsList.filter((group: { name: string }) =>
        group.name.toLowerCase().includes(groupSearch.toLowerCase())
    );

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            template_name: "",
            approval_type: undefined as unknown as FormValues["approval_type"],
            approval_flow_type: "ALL_REQUIRED",
            approval_sequence: "PARALLEL",
            delegation_policy: "DISABLED",
            allow_self_approval: false,
            default_due_days: 5,
            escalation_days: null,
            default_threshold: null,
            auto_assign_by_role: null,
        },
    });

    // Reset form when template data loads
    useEffect(() => {
        if (mode === "edit" && template) {
            form.reset({
                template_name: template.template_name || "",
                approval_type: template.approval_type,
                approval_flow_type: template.approval_flow_type || "ALL_REQUIRED",
                approval_sequence: template.approval_sequence || "PARALLEL",
                delegation_policy: template.delegation_policy || "DISABLED",
                allow_self_approval: template.allow_self_approval || false,
                default_due_days: template.default_due_days || 5,
                escalation_days: template.escalation_days ?? null,
                default_threshold: template.default_threshold ?? null,
                auto_assign_by_role: template.auto_assign_by_role ?? null,
            });
        }
    }, [mode, template, form]);

    const createTemplate = useCreateApprovalTemplate();
    const updateTemplate = useUpdateApprovalTemplate();

    function onSubmit(values: FormValues) {
        const submitData = {
            ...values,
            escalation_days: values.escalation_days || null,
            default_threshold: values.default_threshold || null,
            auto_assign_by_role: values.auto_assign_by_role || null,
        };

        if (mode === "edit" && templateId) {
            updateTemplate.mutate(
                { id: templateId, data: submitData },
                {
                    onSuccess: () => {
                        toast.success("Approval template updated successfully!");
                    },
                    onError: (err) => {
                        console.error("Update failed:", err);
                        toast.error("Failed to update approval template.");
                    },
                }
            );
        } else {
            createTemplate.mutate(submitData, {
                onSuccess: () => {
                    toast.success("Approval template created successfully!");
                    form.reset();
                },
                onError: (err) => {
                    console.error("Creation failed:", err);
                    toast.error("Failed to create approval template.");
                },
            });
        }
    }

    if (mode === "edit" && isLoadingTemplate) {
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
                    {mode === "edit" ? "Edit Approval Template" : "Create Approval Template"}
                </h1>
                <p className="text-muted-foreground">
                    {mode === "edit"
                        ? "Update the approval workflow template configuration"
                        : "Define a new approval workflow template for documents, CAPAs, or other items"}
                </p>
            </div>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    {/* Basic Info */}
                    <div className="space-y-4">
                        <h2 className="text-lg font-semibold">Basic Information</h2>

                        <FormField
                            control={form.control}
                            name="template_name"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel required={required.template_name}>Template Name</FormLabel>
                                    <FormControl>
                                        <Input
                                            placeholder="e.g. Document Release - Standard"
                                            {...field}
                                        />
                                    </FormControl>
                                    <FormDescription>
                                        A descriptive name for this approval template
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="approval_type"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel required={required.approval_type}>Approval Type</FormLabel>
                                    <Select onValueChange={field.onChange} value={field.value}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select approval type" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            {APPROVAL_TYPES.map((type) => (
                                                <SelectItem key={type} value={type}>
                                                    {toTitleCase(type)}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <FormDescription>
                                        What type of items this template applies to
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    {/* Workflow Rules */}
                    <div className="space-y-4 border-t pt-6">
                        <h2 className="text-lg font-semibold">Workflow Rules</h2>

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="approval_flow_type"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel required={required.approval_flow_type}>Approval Flow</FormLabel>
                                        <Select onValueChange={field.onChange} value={field.value}>
                                            <FormControl>
                                                <SelectTrigger>
                                                    <SelectValue />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                {APPROVAL_FLOWS.map((flow) => (
                                                    <SelectItem key={flow} value={flow}>
                                                        {toTitleCase(flow)}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <FormDescription>
                                            How many approvers must approve
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="approval_sequence"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel required={required.approval_sequence}>Sequence</FormLabel>
                                        <Select onValueChange={field.onChange} value={field.value}>
                                            <FormControl>
                                                <SelectTrigger>
                                                    <SelectValue />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                {SEQUENCE_TYPES.map((seq) => (
                                                    <SelectItem key={seq} value={seq}>
                                                        {toTitleCase(seq)}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <FormDescription>
                                            Parallel or sequential approval
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="delegation_policy"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel required={required.delegation_policy}>Delegation</FormLabel>
                                        <Select onValueChange={field.onChange} value={field.value}>
                                            <FormControl>
                                                <SelectTrigger>
                                                    <SelectValue />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                {DELEGATION_POLICIES.map((policy) => (
                                                    <SelectItem key={policy} value={policy}>
                                                        {toTitleCase(policy)}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <FormDescription>
                                            Can approvers delegate?
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="default_threshold"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel required={required.default_threshold}>Threshold (if applicable)</FormLabel>
                                        <FormControl>
                                            <Input
                                                type="number"
                                                placeholder="e.g. 2"
                                                {...field}
                                                value={field.value ?? ""}
                                                onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : null)}
                                            />
                                        </FormControl>
                                        <FormDescription>
                                            Min approvals needed for threshold flow
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <FormField
                            control={form.control}
                            name="auto_assign_by_role"
                            render={({ field }) => (
                                <FormItem className="flex flex-col">
                                    <FormLabel required={required.auto_assign_by_role}>Auto-assign to Group</FormLabel>
                                    <Popover open={groupPopoverOpen} onOpenChange={setGroupPopoverOpen}>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant="outline"
                                                    role="combobox"
                                                    aria-expanded={groupPopoverOpen}
                                                    className={cn(
                                                        "w-full justify-between",
                                                        !field.value && "text-muted-foreground"
                                                    )}
                                                >
                                                    {field.value || "Select group (optional)"}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-full p-0" align="start">
                                            <Command>
                                                <CommandInput
                                                    placeholder="Search groups..."
                                                    value={groupSearch}
                                                    onValueChange={setGroupSearch}
                                                />
                                                <CommandList>
                                                    <CommandEmpty>No groups found.</CommandEmpty>
                                                    <CommandGroup>
                                                        <CommandItem
                                                            onSelect={() => {
                                                                field.onChange(null);
                                                                setGroupPopoverOpen(false);
                                                                setGroupSearch("");
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn(
                                                                    "mr-2 h-4 w-4",
                                                                    !field.value ? "opacity-100" : "opacity-0"
                                                                )}
                                                            />
                                                            None
                                                        </CommandItem>
                                                        {filteredGroups.map((group: { id: string; name: string }) => (
                                                            <CommandItem
                                                                key={group.id}
                                                                value={group.name}
                                                                onSelect={() => {
                                                                    field.onChange(group.name);
                                                                    setGroupPopoverOpen(false);
                                                                    setGroupSearch("");
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn(
                                                                        "mr-2 h-4 w-4",
                                                                        field.value === group.name ? "opacity-100" : "opacity-0"
                                                                    )}
                                                                />
                                                                {group.name}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                    <FormDescription>
                                        Automatically assign approvers from this group
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="allow_self_approval"
                            render={({ field }) => (
                                <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                    <FormControl>
                                        <Checkbox
                                            checked={field.value}
                                            onCheckedChange={field.onChange}
                                        />
                                    </FormControl>
                                    <div className="space-y-1 leading-none">
                                        <FormLabel>Allow Self-Approval</FormLabel>
                                        <FormDescription>
                                            Allow requesters to approve their own requests (requires justification)
                                        </FormDescription>
                                    </div>
                                </FormItem>
                            )}
                        />
                    </div>

                    {/* SLA */}
                    <div className="space-y-4 border-t pt-6">
                        <h2 className="text-lg font-semibold">SLA Settings</h2>

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="default_due_days"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel required={required.default_due_days}>Due Days</FormLabel>
                                        <FormControl>
                                            <Input type="number" min={1} {...field} value={field.value ?? ""} />
                                        </FormControl>
                                        <FormDescription>
                                            Days until approval is due
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="escalation_days"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel required={required.escalation_days}>Escalation Days</FormLabel>
                                        <FormControl>
                                            <Input
                                                type="number"
                                                placeholder="Optional"
                                                {...field}
                                                value={field.value ?? ""}
                                                onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : null)}
                                            />
                                        </FormControl>
                                        <FormDescription>
                                            Days before escalation triggers
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>
                    </div>

                    <div className="flex gap-4 pt-4">
                        <Button
                            type="submit"
                            disabled={createTemplate.isPending || updateTemplate.isPending}
                            className="flex-1"
                        >
                            {mode === "edit"
                                ? updateTemplate.isPending
                                    ? "Saving..."
                                    : "Save Changes"
                                : createTemplate.isPending
                                    ? "Creating..."
                                    : "Create Template"}
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    );
}
