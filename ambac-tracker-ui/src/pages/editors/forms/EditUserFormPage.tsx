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

import { useRetrieveUser } from "@/hooks/useRetrieveUser";
import { useCreateUser } from "@/hooks/useCreateUser";
import { useUpdateUser } from "@/hooks/useUpdateUser";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { useRetrieveGroups } from "@/hooks/useRetrieveGroups";
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
    group_ids: true,
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
    group_ids: isFieldRequired(formSchema.shape.group_ids),
};

export default function UserFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const userId = params.id;
    const [companySearch, setCompanySearch] = useState("");
    const [open, setOpen] = useState(false);
    const [groupSearch, setGroupSearch] = useState("");
    const [groupsOpen, setGroupsOpen] = useState(false);

    const { data: user, isLoading: isLoadingUser } = useRetrieveUser(
        { params: { id: userId! } },
        { enabled: mode === "edit" && !!userId }
    );

    const { data: companies, isLoading: isLoadingCompanies } = useRetrieveCompanies({
        search: companySearch,
    });

    const { data: groups, isLoading: isLoadingGroups } = useRetrieveGroups({
        search: groupSearch,
    });

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
            group_ids: [],
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
                group_ids: user.groups?.map(group => group.id) ?? [],
            });
        }
    }, [mode, user, form]);

    const createUser = useCreateUser();
    const updateUser = useUpdateUser();

    function onSubmit(values: FormValues) {
        // Clean up the data before sending
        const submitData = {
            username: values.username,
            first_name: values.first_name || undefined,
            last_name: values.last_name || undefined,
            email: values.email || undefined,
            is_staff: values.is_staff || false,
            is_active: values.is_active !== undefined ? values.is_active : true,
            parent_company_id: values.parent_company_id || undefined,
            group_ids: values.group_ids || [],
        };

        if (mode === "edit" && userId) {
            updateUser.mutate(
                { id: userId, data: submitData },
                {
                    onSuccess: () => {
                        toast.success("User updated successfully!");
                    },
                    onError: (err) => {
                        console.error("Update failed:", err);
                        toast.error("Failed to update user.");
                    },
                }
            );
        } else {
            createUser.mutate(submitData, {
                onSuccess: () => {
                    toast.success("User created successfully!");
                    form.reset();
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
    const selectedGroups = groups?.results.filter((group) => form.watch("group_ids")?.includes(group.id)) || [];

    return (
        <div className="max-w-3xl mx-auto py-10">
            <div className="mb-8">
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

                    <FormField
                        control={form.control}
                        name="group_ids"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel required={required.group_ids}>Groups</FormLabel>
                                <Popover open={groupsOpen} onOpenChange={setGroupsOpen}>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                aria-expanded={groupsOpen}
                                                className={cn(
                                                    "w-full justify-between",
                                                    (!field.value || field.value.length === 0) && "text-muted-foreground"
                                                )}
                                                disabled={isLoadingGroups}
                                            >
                                                {isLoadingGroups
                                                    ? "Loading..."
                                                    : selectedGroups.length > 0
                                                        ? `${selectedGroups.length} group${selectedGroups.length > 1 ? 's' : ''} selected`
                                                        : "Select groups (optional)"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-full p-0" align="start">
                                        <Command>
                                            <CommandInput
                                                value={groupSearch}
                                                onValueChange={setGroupSearch}
                                                placeholder="Search groups..."
                                            />
                                            <CommandList>
                                                <CommandEmpty>No groups found.</CommandEmpty>
                                                <CommandGroup>
                                                    {groups?.results.map((group) => {
                                                        const isSelected = field.value?.includes(group.id);
                                                        return (
                                                            <CommandItem
                                                                key={group.id}
                                                                value={group.name}
                                                                onSelect={() => {
                                                                    const currentGroups = field.value || [];
                                                                    if (isSelected) {
                                                                        // Remove group
                                                                        form.setValue("group_ids", currentGroups.filter(id => id !== group.id));
                                                                    } else {
                                                                        // Add group
                                                                        form.setValue("group_ids", [...currentGroups, group.id]);
                                                                    }
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn(
                                                                        "mr-2 h-4 w-4",
                                                                        isSelected ? "opacity-100" : "opacity-0"
                                                                    )}
                                                                />
                                                                {group.name}
                                                            </CommandItem>
                                                        );
                                                    })}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>
                                    Select user groups for permissions and role-based access control
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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