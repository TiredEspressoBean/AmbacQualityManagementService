"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useForm, useWatch, type UseFormReturn } from "react-hook-form";
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
import { useNavigate, useParams } from "@tanstack/react-router";

import { useRetrieveApprovalTemplate } from "@/hooks/useRetrieveApprovalTemplate";
import { useCreateApprovalTemplate } from "@/hooks/useCreateApprovalTemplate";
import { useUpdateApprovalTemplate } from "@/hooks/useUpdateApprovalTemplate";
import { useTenantGroups } from "@/hooks/useTenantGroups";
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";
import { RequiredApproversField } from "@/components/approval-templates/RequiredApproversField";
import { EscalationTargetField } from "@/components/approval-templates/EscalationTargetField";

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
}).extend({
    // M2M + FK fields the underlying serializer accepts but the
    // generated schema's `ApprovalTemplateRequest` lists with various
    // optional/nullable shapes. Coerce to local form values that we
    // control directly.
    default_approvers: z.array(z.number()).default([]),
    default_groups: z.array(z.string()).default([]),
    escalate_to: z.number().nullable().default(null),
});

type FormValues = z.infer<typeof formSchema>;

/**
 * Small bridge that turns the two flat M2M form fields
 * (`default_approvers`, `default_groups`) into the unified value the
 * RequiredApproversField widget expects. Uses `useWatch` so the widget
 * re-renders when the form values change (e.g. after `form.reset()`
 * fires on template load).
 */
function ApproversFormBridge({ form }: { form: UseFormReturn<FormValues> }) {
    const approvers = useWatch({ control: form.control, name: "default_approvers" });
    const groups = useWatch({ control: form.control, name: "default_groups" });
    return (
        <>
            <RequiredApproversField
                value={{
                    approvers: approvers ?? [],
                    groups: groups ?? [],
                }}
                onChange={(next) => {
                    form.setValue("default_approvers", next.approvers, { shouldDirty: true });
                    form.setValue("default_groups", next.groups, { shouldDirty: true });
                }}
            />
        </>
    );
}


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
    const navigate = useNavigate();
    const mode = params.id ? "edit" : "create";
    const templateId = params.id;

    const { data: template, isLoading: isLoadingTemplate } = useRetrieveApprovalTemplate(
        { params: { id: templateId! } },
        { enabled: mode === "edit" && !!templateId }
    );

    const [groupSearch, setGroupSearch] = useState("");
    const [groupPopoverOpen, setGroupPopoverOpen] = useState(false);

    const { data: groups } = useTenantGroups();
    const groupsList = Array.isArray(groups?.results) ? groups.results : groups?.results || [];

    // Filter groups based on search
    const filteredGroups = groupsList.filter((group: { name: string }) =>
        group.name.toLowerCase().includes(groupSearch.toLowerCase())
    );

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            template_name: "",
            // eslint-disable-next-line local/no-double-cast-via-unknown -- RHF defaultValues: approval_type is required enum but must start unset before user selects
            approval_type: undefined as unknown as FormValues["approval_type"],
            approval_flow_type: "ALL_REQUIRED",
            approval_sequence: "PARALLEL",
            delegation_policy: "DISABLED",
            allow_self_approval: false,
            default_due_days: 5,
            escalation_days: null,
            default_threshold: null,
            auto_assign_by_role: null,
            default_approvers: [],
            default_groups: [],
            escalate_to: null,
        },
    });

    // Reset form when template data loads
    useEffect(() => {
        if (mode === "edit" && template) {
            const t = template as typeof template & {
                default_approvers?: number[];
                default_groups?: string[];
                escalate_to?: number | null;
            };
            form.reset({
                template_name: t.template_name || "",
                approval_type: t.approval_type,
                approval_flow_type: t.approval_flow_type || "ALL_REQUIRED",
                approval_sequence: t.approval_sequence || "PARALLEL",
                delegation_policy: t.delegation_policy || "DISABLED",
                allow_self_approval: t.allow_self_approval || false,
                default_due_days: t.default_due_days || 5,
                escalation_days: t.escalation_days ?? null,
                default_threshold: t.default_threshold ?? null,
                auto_assign_by_role: t.auto_assign_by_role ?? null,
                default_approvers: t.default_approvers ?? [],
                default_groups: t.default_groups ?? [],
                escalate_to: t.escalate_to ?? null,
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
                    onSuccess: (updated) => {
                        toast.success("Approval template updated successfully!");
                        // The backend versions on every content edit — the
                        // response is a freshly created row with a new id.
                        // Navigate to it so the URL doesn't leave the user
                        // pointing at the now-stale prior version.
                        const newId = (updated as { id?: string })?.id;
                        if (newId && newId !== templateId) {
                            navigate({
                                to: "/ApprovalTemplateForm/edit/$id",
                                params: { id: newId },
                                replace: true,
                            });
                        }
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
                                    {/* Re-key on the field value so Radix Select shows
                                        the loaded value after `form.reset()` fires on
                                        template load. Without this, the trigger renders
                                        with the placeholder even though `value` is set. */}
                                    <Select
                                        key={`approval-type-${field.value ?? "empty"}`}
                                        onValueChange={field.onChange}
                                        value={field.value}
                                        defaultValue={field.value}
                                    >
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

                    {/* Required Approvers — who has to sign off */}
                    <div className="space-y-3 border-t pt-6">
                        <div>
                            <h2 className="text-lg font-semibold">Required Approvers</h2>
                            <p className="text-sm text-muted-foreground">
                                Specific people, role groups, or both. Applies in both
                                simplified and regulated change-control modes — the mode
                                only affects whether signatures must be collected before
                                state advances.
                            </p>
                        </div>
                        <ApproversFormBridge form={form} />
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
                                                        {filteredGroups.map((group) => (
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

                        <FormField
                            control={form.control}
                            name="escalate_to"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Escalation Target</FormLabel>
                                    <FormControl>
                                        <EscalationTargetField
                                            value={field.value ?? null}
                                            onChange={field.onChange}
                                        />
                                    </FormControl>
                                    <FormDescription>
                                        User who gets notified when escalation triggers.
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
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
