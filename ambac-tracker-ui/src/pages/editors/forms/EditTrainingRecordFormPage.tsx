"use client";

import { useEffect, useState } from "react";
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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { cn } from "@/lib/utils";
import { CalendarIcon, Check, ChevronsUpDown } from "lucide-react";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command";
import { format } from "date-fns";

import { useRetrieveTrainingRecord } from "@/hooks/useRetrieveTrainingRecord";
import { useCreateTrainingRecord } from "@/hooks/useCreateTrainingRecord";
import { useUpdateTrainingRecord } from "@/hooks/useUpdateTrainingRecord";
import { useTrainingTypes } from "@/hooks/useTrainingTypes";
import { useRetrieveUsers } from "@/hooks/useRetrieveUsers";
import { schemas } from "@/lib/api/generated";
import { isFieldRequired } from "@/lib/zod-config";

// Use generated schema
const formSchema = schemas.TrainingRecordRequest.pick({
    user: true,
    training_type: true,
    completed_date: true,
    expires_date: true,
    trainer: true,
    notes: true,
});

type FormValues = z.infer<typeof formSchema>;

// Pre-compute required fields
const required = {
    user: isFieldRequired(formSchema.shape.user),
    training_type: isFieldRequired(formSchema.shape.training_type),
    completed_date: isFieldRequired(formSchema.shape.completed_date),
    expires_date: isFieldRequired(formSchema.shape.expires_date),
    trainer: isFieldRequired(formSchema.shape.trainer),
    notes: isFieldRequired(formSchema.shape.notes),
};

export default function EditTrainingRecordFormPage() {
    const params = useParams({ strict: false });
    const navigate = useNavigate();
    const mode = params.id && params.id !== "new" ? "edit" : "create";
    const recordId = params.id !== "new" ? params.id : undefined;

    const [trainingTypeSearch, setTrainingTypeSearch] = useState("");
    const [trainingTypeOpen, setTrainingTypeOpen] = useState(false);
    const [userSearch, setUserSearch] = useState("");
    const [userOpen, setUserOpen] = useState(false);
    const [trainerSearch, setTrainerSearch] = useState("");
    const [trainerOpen, setTrainerOpen] = useState(false);

    const { data: record, isLoading: isLoadingRecord } = useRetrieveTrainingRecord(recordId || "");

    const { data: trainingTypesData } = useTrainingTypes({
        search: trainingTypeSearch,
    });
    const trainingTypes = trainingTypesData?.results ?? [];

    const { data: usersData } = useRetrieveUsers(
        {
            search: userSearch || trainerSearch,
        }
    );
    const users = usersData?.results ?? [];

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            user: undefined,
            training_type: undefined,
            completed_date: "",
            expires_date: null,
            trainer: null,
            notes: "",
        },
    });

    // Reset form when record data loads
    useEffect(() => {
        if (mode === "edit" && record) {
            form.reset({
                user: record.user ?? undefined,
                training_type: record.training_type ?? undefined,
                completed_date: record.completed_date ?? "",
                expires_date: record.expires_date ?? null,
                trainer: record.trainer ?? null,
                notes: record.notes ?? "",
            });
        }
    }, [mode, record, form]);

    const createRecord = useCreateTrainingRecord();
    const updateRecord = useUpdateTrainingRecord();

    function onSubmit(values: FormValues) {
        const submitData = {
            user: values.user,
            training_type: values.training_type,
            completed_date: values.completed_date,
            expires_date: values.expires_date || undefined,
            trainer: values.trainer || undefined,
            notes: values.notes || undefined,
        };

        if (mode === "edit" && recordId) {
            updateRecord.mutate(
                { params: { id: recordId }, ...submitData },
                {
                    onSuccess: () => {
                        toast.success("Training record updated successfully!");
                        navigate({ to: "/quality/training/records" });
                    },
                    onError: (err) => {
                        console.error("Update failed:", err);
                        toast.error("Failed to update training record.");
                    },
                }
            );
        } else {
            createRecord.mutate(submitData, {
                onSuccess: () => {
                    toast.success("Training record created successfully!");
                    navigate({ to: "/quality/training/records" });
                },
                onError: (err) => {
                    console.error("Creation failed:", err);
                    toast.error("Failed to create training record.");
                },
            });
        }
    }

    if (mode === "edit" && isLoadingRecord) {
        return <div className="container mx-auto p-6">Loading...</div>;
    }

    return (
        <div className="container mx-auto p-6 max-w-2xl">
            <h1 className="text-2xl font-bold mb-6">
                {mode === "edit" ? "Edit Training Record" : "New Training Record"}
            </h1>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    {/* User (Trainee) */}
                    <FormField
                        control={form.control}
                        name="user"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel>Trainee {required.user && "*"}</FormLabel>
                                <Popover open={userOpen} onOpenChange={setUserOpen}>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                className={cn(
                                                    "justify-between",
                                                    !field.value && "text-muted-foreground"
                                                )}
                                            >
                                                {field.value
                                                    ? users.find((u: any) => u.id === field.value)?.username ||
                                                      `User ${field.value}`
                                                    : "Select trainee"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-full p-0">
                                        <Command>
                                            <CommandInput
                                                placeholder="Search users..."
                                                value={userSearch}
                                                onValueChange={setUserSearch}
                                            />
                                            <CommandList>
                                                <CommandEmpty>No users found.</CommandEmpty>
                                                <CommandGroup>
                                                    {users.map((user: any) => (
                                                        <CommandItem
                                                            key={user.id}
                                                            value={user.username}
                                                            onSelect={() => {
                                                                field.onChange(user.id);
                                                                setUserOpen(false);
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn(
                                                                    "mr-2 h-4 w-4",
                                                                    field.value === user.id ? "opacity-100" : "opacity-0"
                                                                )}
                                                            />
                                                            {user.first_name && user.last_name
                                                                ? `${user.first_name} ${user.last_name} (${user.username})`
                                                                : user.username}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>The person who completed the training</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Training Type */}
                    <FormField
                        control={form.control}
                        name="training_type"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel>Training Type {required.training_type && "*"}</FormLabel>
                                <Popover open={trainingTypeOpen} onOpenChange={setTrainingTypeOpen}>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                className={cn(
                                                    "justify-between",
                                                    !field.value && "text-muted-foreground"
                                                )}
                                            >
                                                {field.value
                                                    ? trainingTypes.find((t: any) => t.id === field.value)?.name ||
                                                      "Select type"
                                                    : "Select training type"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-full p-0">
                                        <Command>
                                            <CommandInput
                                                placeholder="Search training types..."
                                                value={trainingTypeSearch}
                                                onValueChange={setTrainingTypeSearch}
                                            />
                                            <CommandList>
                                                <CommandEmpty>No training types found.</CommandEmpty>
                                                <CommandGroup>
                                                    {trainingTypes.map((type: any) => (
                                                        <CommandItem
                                                            key={type.id}
                                                            value={type.name}
                                                            onSelect={() => {
                                                                field.onChange(type.id);
                                                                setTrainingTypeOpen(false);
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn(
                                                                    "mr-2 h-4 w-4",
                                                                    field.value === type.id ? "opacity-100" : "opacity-0"
                                                                )}
                                                            />
                                                            {type.name}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Completed Date */}
                    <FormField
                        control={form.control}
                        name="completed_date"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel>Completion Date {required.completed_date && "*"}</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                className={cn(
                                                    "pl-3 text-left font-normal",
                                                    !field.value && "text-muted-foreground"
                                                )}
                                            >
                                                {field.value ? format(new Date(field.value), "PPP") : "Pick a date"}
                                                <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-auto p-0" align="start">
                                        <Calendar
                                            mode="single"
                                            selected={field.value ? new Date(field.value) : undefined}
                                            onSelect={(date) => field.onChange(date ? format(date, "yyyy-MM-dd") : "")}
                                            initialFocus
                                        />
                                    </PopoverContent>
                                </Popover>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Expires Date */}
                    <FormField
                        control={form.control}
                        name="expires_date"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel>Expiration Date</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                className={cn(
                                                    "pl-3 text-left font-normal",
                                                    !field.value && "text-muted-foreground"
                                                )}
                                            >
                                                {field.value ? format(new Date(field.value), "PPP") : "No expiration"}
                                                <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-auto p-0" align="start">
                                        <Calendar
                                            mode="single"
                                            selected={field.value ? new Date(field.value) : undefined}
                                            onSelect={(date) => field.onChange(date ? format(date, "yyyy-MM-dd") : null)}
                                            initialFocus
                                        />
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>
                                    Leave empty if training never expires. Auto-calculated from training type if not set.
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Trainer */}
                    <FormField
                        control={form.control}
                        name="trainer"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel>Trainer</FormLabel>
                                <Popover open={trainerOpen} onOpenChange={setTrainerOpen}>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                className={cn(
                                                    "justify-between",
                                                    !field.value && "text-muted-foreground"
                                                )}
                                            >
                                                {field.value
                                                    ? users.find((u: any) => u.id === field.value)?.username ||
                                                      `User ${field.value}`
                                                    : "Select trainer (optional)"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-full p-0">
                                        <Command>
                                            <CommandInput
                                                placeholder="Search users..."
                                                value={trainerSearch}
                                                onValueChange={setTrainerSearch}
                                            />
                                            <CommandList>
                                                <CommandEmpty>No users found.</CommandEmpty>
                                                <CommandGroup>
                                                    <CommandItem
                                                        value=""
                                                        onSelect={() => {
                                                            field.onChange(null);
                                                            setTrainerOpen(false);
                                                        }}
                                                    >
                                                        <Check
                                                            className={cn(
                                                                "mr-2 h-4 w-4",
                                                                !field.value ? "opacity-100" : "opacity-0"
                                                            )}
                                                        />
                                                        No trainer
                                                    </CommandItem>
                                                    {users.map((user: any) => (
                                                        <CommandItem
                                                            key={user.id}
                                                            value={user.username}
                                                            onSelect={() => {
                                                                field.onChange(user.id);
                                                                setTrainerOpen(false);
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn(
                                                                    "mr-2 h-4 w-4",
                                                                    field.value === user.id ? "opacity-100" : "opacity-0"
                                                                )}
                                                            />
                                                            {user.first_name && user.last_name
                                                                ? `${user.first_name} ${user.last_name} (${user.username})`
                                                                : user.username}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>Person who conducted the training</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    {/* Notes */}
                    <FormField
                        control={form.control}
                        name="notes"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Notes</FormLabel>
                                <FormControl>
                                    <Textarea
                                        placeholder="Additional notes about the training..."
                                        {...field}
                                        value={field.value ?? ""}
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <div className="flex gap-4">
                        <Button
                            type="submit"
                            disabled={createRecord.isPending || updateRecord.isPending}
                        >
                            {createRecord.isPending || updateRecord.isPending
                                ? "Saving..."
                                : mode === "edit"
                                ? "Update Training Record"
                                : "Create Training Record"}
                        </Button>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => navigate({ to: "/quality/training/records" })}
                        >
                            Cancel
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    );
}
