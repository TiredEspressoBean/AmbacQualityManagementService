"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { ReportButton } from "@/components/reports/ReportButton";
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
import { useParams } from "@tanstack/react-router";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { Check, ChevronsUpDown } from "lucide-react";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command";
import { Checkbox } from "@/components/ui/checkbox";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

import { useRetrieveUser } from "@/hooks/useRetrieveUser";
import { useJobRoles } from "@/hooks/useJobRoles";
import { useTenantGroups } from "@/hooks/useTenantGroups";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import { useCreateUser } from "@/hooks/useCreateUser";
import { useUpdateUser } from "@/hooks/useUpdateUser";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { useAuthUser } from "@/hooks/useAuthUser";
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";

// Use generated schema - error messages handled by global error map
const formSchema = schemas.UserRequest.pick({
    username: true,
    first_name: true,
    last_name: true,
    email: true,
    is_staff: true,
    is_active: true,
    parent_company_id: true,
    job_role: true,
});

type FormValues = z.infer<typeof formSchema>;

// Pre-compute required fields for labels
const required = {
    username: isFieldRequired(formSchema.shape.username),
    first_name: isFieldRequired(formSchema.shape.first_name),
    last_name: isFieldRequired(formSchema.shape.last_name),
    email: isFieldRequired(formSchema.shape.email),
    is_staff: isFieldRequired(formSchema.shape.is_staff),
    is_active: isFieldRequired(formSchema.shape.is_active),
    parent_company_id: isFieldRequired(formSchema.shape.parent_company_id),
};

export default function UserFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const userId = params.id ? Number(params.id) : undefined;
    const [companySearch, setCompanySearch] = useState("");
    const [open, setOpen] = useState(false);

    const { data: user, isLoading: isLoadingUser } = useRetrieveUser(
        { params: { id: userId as number } },
        { enabled: mode === "edit" && userId !== undefined }
    );

    const { data: companies, isLoading: isLoadingCompanies } = useRetrieveCompanies({
        search: companySearch,
    });

    const { data: jobRolesData } = useJobRoles({ active: true });
    const { data: groupsData } = useTenantGroups({ offset: 0, limit: 200 });
    const jobRoles = jobRolesData?.results ?? [];

    // Get current user to check staff/superuser status
    const { data: currentUser } = useAuthUser();
    const canEditStaffStatus = currentUser?.is_staff === true || currentUser?.is_superuser === true;

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            username: "",
            first_name: "",
            last_name: "",
            email: "",
            is_staff: false,
            is_active: true,
            parent_company_id: undefined,
            job_role: null,
        },
    });

    // Reset form when user data loads
    useEffect(() => {
        if (mode === "edit" && user) {
            form.reset({
                username: user.username ?? "",
                first_name: user.first_name ?? "",
                last_name: user.last_name ?? "",
                email: user.email ?? "",
                is_staff: user.is_staff ?? false,
                is_active: user.is_active ?? true,
                parent_company_id: user.parent_company?.id ?? undefined,
                job_role: user.job_role ?? null,
            });
        }
    }, [mode, user, form]);

    // Group membership is NOT part of the user payload: `groups` is a
    // SerializerMethodField in read_only_fields on the User serializer, so the
    // API silently ignores it. Membership lives in UserRole and is managed via
    // the TenantGroups members endpoints, so it is tracked separately here and
    // reconciled after the user save succeeds.
    const groupOptions = groupsData?.results ?? [];
    const [groupIds, setGroupIds] = useState<string[]>([]);
    const [initialGroupIds, setInitialGroupIds] = useState<string[]>([]);

    useEffect(() => {
        if (mode === "edit" && user) {
            const ids = ((user.groups ?? []) as { id?: string }[])
                .map((g) => String(g.id))
                .filter(Boolean);
            setGroupIds(ids);
            setInitialGroupIds(ids);
        }
    }, [mode, user]);

    /** Apply the group diff. Additions and removals are independent calls, so a
     *  partial failure is reported rather than silently leaving the user in a
     *  half-assigned state. */
    async function syncGroups(targetUserId: number, desired: string[], current: string[]) {
        const headers = { "X-CSRFToken": getCookie("csrftoken") };
        const toAdd = desired.filter((g) => !current.includes(g));
        const toRemove = current.filter((g) => !desired.includes(g));
        const failed: string[] = [];
        for (const gid of toAdd) {
            try {
                await api.api_TenantGroups_members_create(
                    // eslint-disable-next-line local/no-as-any -- only user_id is read server-side; mirrors useTenantGroupMembers
                    { name: "", user_id: String(targetUserId) } as any,
                    { params: { id: gid }, headers },
                );
            } catch { failed.push(gid); }
        }
        for (const gid of toRemove) {
            try {
                await api.api_TenantGroups_members_destroy(undefined, {
                    params: { id: gid, user_id: String(targetUserId) },
                    headers,
                });
            } catch { failed.push(gid); }
        }
        return failed;
    }

    const createUser = useCreateUser();
    const updateUser = useUpdateUser();

    function onSubmit(values: FormValues) {
        // Clean up the data before sending
        const submitData: Record<string, unknown> = {
            username: values.username,
            first_name: values.first_name || undefined,
            last_name: values.last_name || undefined,
            email: values.email || undefined,
            is_active: values.is_active !== undefined ? values.is_active : true,
            parent_company_id: values.parent_company_id || undefined,
            job_role: values.job_role ?? null,
        };

        // Only staff users can set is_staff field
        if (canEditStaffStatus) {
            submitData.is_staff = values.is_staff || false;
        }

        if (mode === "edit" && userId !== undefined) {
            updateUser.mutate(
                { id: userId, data: submitData },
                {
                    onSuccess: async () => {
                        const failed = await syncGroups(userId, groupIds, initialGroupIds);
                        setInitialGroupIds(groupIds);
                        if (failed.length) {
                            toast.warning(
                                `User updated, but ${failed.length} role change(s) failed. Check permissions and retry.`,
                            );
                        } else {
                            toast.success("User updated successfully!");
                        }
                    },
                    onError: (err) => {
                        console.error("Update failed:", err);
                        toast.error("Failed to update user.");
                    },
                }
            );
        } else {
            createUser.mutate(submitData as Parameters<typeof createUser.mutate>[0], {
                onSuccess: async (created) => {
                    const newId = (created as { id?: number } | undefined)?.id;
                    let failed: string[] = [];
                    if (newId !== undefined && groupIds.length) {
                        failed = await syncGroups(newId, groupIds, []);
                    }
                    if (failed.length) {
                        toast.warning(
                            `User created, but ${failed.length} role assignment(s) failed. Assign them from the group page.`,
                        );
                    } else {
                        toast.success("User created successfully!");
                    }
                    form.reset();
                    setGroupIds([]);
                    setInitialGroupIds([]);
                },
                onError: (err) => {
                    console.error("Creation failed:", err);
                    toast.error("Failed to create user.");
                },
            });
        }
    }

    // Show loading state
    if (mode === "edit" && isLoadingUser) {
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

    const selectedCompany = companies?.results.find((company) => company.id === form.watch("parent_company_id"));

    return (
        <div className="max-w-3xl mx-auto py-10">
            <div className="mb-8 flex items-start justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold">
                        {mode === "edit" ? "Edit User" : "Create User"}
                    </h1>
                    <p className="text-muted-foreground">
                        {mode === "edit"
                            ? "Update the user information below"
                            : "Add a new user to the system"
                        }
                    </p>
                </div>
                {mode === "edit" && userId && (
                    <ReportButton
                        reportType="training_record"
                        label="Training Record"
                        params={{ user_id: userId }}
                    />
                )}
            </div>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    <FormField
                        control={form.control}
                        name="username"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.username}>Username</FormLabel>
                                <FormControl>
                                    <Input
                                        placeholder="e.g. john.doe or user@company.com"
                                        {...field}
                                    />
                                </FormControl>
                                <FormDescription>
                                    150 characters or fewer. Letters, digits and @/./+/-/_ only.
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <FormField
                            control={form.control}
                            name="first_name"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel required={required.first_name}>First Name</FormLabel>
                                    <FormControl>
                                        <Input
                                            placeholder="e.g. John"
                                            {...field}
                                            value={field.value ?? ""}
                                        />
                                    </FormControl>
                                    <FormDescription>
                                        Up to 150 characters.
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="last_name"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel required={required.last_name}>Last Name</FormLabel>
                                    <FormControl>
                                        <Input
                                            placeholder="e.g. Doe"
                                            {...field}
                                            value={field.value ?? ""}
                                        />
                                    </FormControl>
                                    <FormDescription>
                                        Up to 150 characters.
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    <FormField
                        control={form.control}
                        name="email"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel required={required.email}>Email</FormLabel>
                                <FormControl>
                                    <Input
                                        type="email"
                                        placeholder="e.g. john.doe@company.com"
                                        {...field}
                                        value={field.value ?? ""}
                                    />
                                </FormControl>
                                <FormDescription>
                                    Valid email address up to 254 characters.
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="parent_company_id"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel required={required.parent_company_id}>Company</FormLabel>
                                <Popover open={open} onOpenChange={setOpen}>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                aria-expanded={open}
                                                className={cn(
                                                    "w-full justify-between",
                                                    !field.value && "text-muted-foreground"
                                                )}
                                                disabled={isLoadingCompanies}
                                            >
                                                {isLoadingCompanies
                                                    ? "Loading..."
                                                    : selectedCompany
                                                        ? selectedCompany.name
                                                        : "Select a company (optional)"}
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
                                                    {/* Option to clear selection */}
                                                    <CommandItem
                                                        onSelect={() => {
                                                            form.setValue("parent_company_id", undefined);
                                                            setOpen(false);
                                                        }}
                                                    >
                                                        <Check
                                                            className={cn(
                                                                "mr-2 h-4 w-4",
                                                                !field.value ? "opacity-100" : "opacity-0"
                                                            )}
                                                        />
                                                        No company
                                                    </CommandItem>

                                                    {companies?.results.map((company) => (
                                                        <CommandItem
                                                            key={company.id}
                                                            value={company.name}
                                                            onSelect={() => {
                                                                form.setValue("parent_company_id", company.id);
                                                                setOpen(false);
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
                                    Associate this user with a company, or leave blank for no company
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Role = tenant group membership, which is what actually grants
                        permissions (via UserRole). Not part of the user payload -- see
                        syncGroups above. Rendered as plain checkboxes rather than a
                        Select because membership is many-to-many. */}
                    <FormItem className="flex flex-col">
                        <FormLabel>Role</FormLabel>
                        <div className="rounded-md border p-3 space-y-2 max-h-56 overflow-y-auto">
                            {groupOptions.length === 0 ? (
                                <p className="text-sm text-muted-foreground">
                                    No roles defined for this organization yet.
                                </p>
                            ) : (
                                groupOptions.map((g) => {
                                    const gid = String(g.id);
                                    const checked = groupIds.includes(gid);
                                    return (
                                        <label
                                            key={gid}
                                            className="flex items-center gap-2 text-sm cursor-pointer"
                                        >
                                            <Checkbox
                                                checked={checked}
                                                onCheckedChange={(v) =>
                                                    setGroupIds((prev) =>
                                                        v === true
                                                            ? [...prev, gid]
                                                            : prev.filter((x) => x !== gid),
                                                    )
                                                }
                                            />
                                            <span>{g.name}</span>
                                        </label>
                                    );
                                })
                            )}
                        </div>
                        <FormDescription>
                            Controls what this person can do in the app. Applied after the
                            user is saved, so a failure here is reported separately.
                        </FormDescription>
                    </FormItem>

                    <FormField
                        control={form.control}
                        name="job_role"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel>Position</FormLabel>
                                <Select
                                    value={field.value ?? "__none__"}
                                    onValueChange={(v) => field.onChange(v === "__none__" ? null : v)}
                                >
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="No position" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        <SelectItem value="__none__">No position</SelectItem>
                                        {jobRoles.map((r) => (
                                            <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <FormDescription>
                                    Drives the required-competency profile in the training matrix. Separate from Role, which controls permissions.
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className={`grid grid-cols-1 ${canEditStaffStatus ? 'md:grid-cols-2' : ''} gap-6`}>
                        <FormField
                            control={form.control}
                            name="is_active"
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
                                            Active User
                                        </FormLabel>
                                        <FormDescription>
                                            Designates whether this user should be treated as active. Uncheck this instead of deleting accounts.
                                        </FormDescription>
                                    </div>
                                </FormItem>
                            )}
                        />

                        {/* Staff status field - only visible to staff users */}
                        {canEditStaffStatus && (
                            <FormField
                                control={form.control}
                                name="is_staff"
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
                                                Staff Status
                                            </FormLabel>
                                            <FormDescription>
                                                Designates whether the user can log into the admin site.
                                            </FormDescription>
                                        </div>
                                    </FormItem>
                                )}
                            />
                        )}
                    </div>

                    <div className="flex gap-4">
                        <Button
                            type="submit"
                            disabled={createUser.isPending || updateUser.isPending}
                            className="flex-1"
                        >
                            {mode === "edit"
                                ? updateUser.isPending
                                    ? "Saving..."
                                    : "Save Changes"
                                : createUser.isPending
                                    ? "Creating..."
                                    : "Create User"}
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    );
}