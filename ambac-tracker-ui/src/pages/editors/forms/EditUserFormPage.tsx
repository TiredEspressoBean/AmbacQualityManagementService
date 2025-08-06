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

const formSchema = z.object({
    username: z
        .string()
        .min(1, "Username is required - please enter a unique username for this user")
        .max(150, "Username must be 150 characters or less")
        .regex(/^[\w.@+-]+$/, "Username can only contain letters, digits and @/./+/-/_ characters"),
    first_name: z
        .string()
        .max(150, "First name must be 150 characters or less")
        .optional(),
    last_name: z
        .string()
        .max(150, "Last name must be 150 characters or less")
        .optional(),
    email: z
        .string()
        .email("Please enter a valid email address in the format: user@domain.com")
        .max(254, "Email must be 254 characters or less")
        .optional(),
    is_staff: z.boolean().optional(),
    is_active: z.boolean().optional(),
    parent_company_id: z.number().nullable().optional(),
});

export default function UserFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const userId = params.id ? parseInt(params.id, 10) : undefined;
    const [companySearch, setCompanySearch] = useState("");
    const [open, setOpen] = useState(false);

    const { data: user, isLoading: isLoadingUser } = useRetrieveUser(
        { params: { id: userId! } },
        { enabled: mode === "edit" && !!userId }
    );

    const { data: companies, isLoading: isLoadingCompanies } = useRetrieveCompanies({
        queries: { search: companySearch },
    });

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            username: "",
            first_name: "",
            last_name: "",
            email: "",
            is_staff: false,
            is_active: true,
            parent_company_id: undefined,
        },
    });

    // Reset form when user data loads
    useEffect(() => {
        if (mode === "edit" && user) {
            form.reset({
                username: user.username || "",
                first_name: user.first_name || "",
                last_name: user.last_name || "",
                email: user.email || "",
                is_staff: user.is_staff || false,
                is_active: user.is_active !== undefined ? user.is_active : true,
                parent_company_id: user.parent_company?.id || undefined,
            });
        }
    }, [mode, user, form]);

    const createUser = useCreateUser();
    const updateUser = useUpdateUser();

    function onSubmit(values: z.infer<typeof formSchema>) {
        // Clean up the data before sending
        const submitData = {
            username: values.username,
            first_name: values.first_name || undefined,
            last_name: values.last_name || undefined,
            email: values.email || undefined,
            is_staff: values.is_staff || false,
            is_active: values.is_active !== undefined ? values.is_active : true,
            parent_company_id: values.parent_company_id || undefined,
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
                                <FormLabel>Username *</FormLabel>
                                <FormControl>
                                    <Input
                                        placeholder="e.g. john.doe or user@company.com"
                                        {...field}
                                    />
                                </FormControl>
                                <FormDescription>
                                    Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.
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
                                    <FormLabel>First Name</FormLabel>
                                    <FormControl>
                                        <Input
                                            placeholder="e.g. John"
                                            {...field}
                                        />
                                    </FormControl>
                                    <FormDescription>
                                        Optional. Up to 150 characters.
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
                                    <FormLabel>Last Name</FormLabel>
                                    <FormControl>
                                        <Input
                                            placeholder="e.g. Doe"
                                            {...field}
                                        />
                                    </FormControl>
                                    <FormDescription>
                                        Optional. Up to 150 characters.
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
                                <FormLabel>Email</FormLabel>
                                <FormControl>
                                    <Input
                                        type="email"
                                        placeholder="e.g. john.doe@company.com"
                                        {...field}
                                    />
                                </FormControl>
                                <FormDescription>
                                    Optional. Valid email address up to 254 characters.
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
                                <FormLabel>Company (Optional)</FormLabel>
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