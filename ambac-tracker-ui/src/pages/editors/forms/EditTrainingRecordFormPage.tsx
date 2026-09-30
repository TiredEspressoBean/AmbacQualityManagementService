"use client";

import { Combobox } from "@/components/ui/combobox";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { Schema } from "@/lib/api/types";
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
import { CalendarIcon } from "lucide-react";
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
    level: true,
    expires_date: true,
    trainer: true,
    notes: true,
});

type FormValues = Pick<Schema<"TrainingRecordRequest">, "user" | "training_type" | "completed_date" | "level" | "expires_date" | "trainer" | "notes">;

// Pre-compute required fields
const required = {
    user: isFieldRequired(formSchema.shape.user),
    training_type: isFieldRequired(formSchema.shape.training_type),
    completed_date: isFieldRequired(formSchema.shape.completed_date),
    level: isFieldRequired(formSchema.shape.level),
    expires_date: isFieldRequired(formSchema.shape.expires_date),
    trainer: isFieldRequired(formSchema.shape.trainer),
    notes: isFieldRequired(formSchema.shape.notes),
};

// Competency scale (mirrors CompetencyLevel on the backend).
const LEVEL_OPTIONS = [
    { value: 1, label: "Level 1 — Trainee", hint: "Supervised only" },
    { value: 2, label: "Level 2 — Assisted", hint: "Output still checked" },
    { value: 3, label: "Level 3 — Qualified", hint: "Independent, to standard" },
    { value: 4, label: "Level 4 — Expert", hint: "Can train / sign off others" },
] as const;

type UserLike = { id: number; username?: string | null; first_name?: string | null; last_name?: string | null };
const userOption = (u: UserLike) => ({
    value: String(u.id),
    label: u.first_name && u.last_name ? `${u.first_name} ${u.last_name}` : (u.username ?? `User #${u.id}`),
    ...(u.first_name && u.last_name && u.username ? { description: u.username } : {}),
});
/** A record's `*_info` block's display name, when it has one. */
const infoName = (info: unknown): string | undefined => {
    const i = info as { name?: string; full_name?: string; username?: string } | null | undefined;
    return i?.full_name || i?.name || i?.username || undefined;
};

export default function EditTrainingRecordFormPage() {
    const params = useParams({ strict: false });
    const navigate = useNavigate();
    const mode = params.id && params.id !== "new" ? "edit" : "create";
    const recordId = params.id !== "new" ? params.id : undefined;

    const [trainingTypeSearch, setTrainingTypeSearch] = useState("");
    const [userSearch, setUserSearch] = useState("");
    const [trainerSearch, setTrainerSearch] = useState("");

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

    const form = useForm<FormValues, any, FormValues>({
        resolver: zodResolver(formSchema) as Resolver<FormValues, any, FormValues>,
        // eslint-disable-next-line local/no-double-cast-via-unknown -- RHF defaultValues: required enum fields must start unset; cast needed to satisfy strict FormValues type
        defaultValues: {
            user: undefined,
            training_type: undefined,
            completed_date: "",
            level: 3,
            expires_date: null,
            trainer: null,
            notes: "",
        } as unknown as FormValues,
    });

    // Reset form when record data loads
    useEffect(() => {
        if (mode === "edit" && record) {
            form.reset({
                user: record.user ?? undefined,
                training_type: record.training_type ?? undefined,
                completed_date: record.completed_date ?? "",
                level: record.level ?? 3,
                expires_date: record.expires_date ?? null,
                trainer: record.trainer ?? null,
                notes: record.notes ?? "",
            } as FormValues);
        }
    }, [mode, record, form]);

    const createRecord = useCreateTrainingRecord();
    const updateRecord = useUpdateTrainingRecord();

    function onSubmit(values: FormValues) {
        const submitData = {
            user: values.user,
            training_type: values.training_type,
            completed_date: values.completed_date,
            level: values.level,
            expires_date: values.expires_date || undefined,
            trainer: values.trainer || undefined,
            notes: values.notes || undefined,
        };

        if (mode === "edit" && recordId) {
            updateRecord.mutate(
                { id: recordId, data: submitData },
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
                                <FormControl>
                                    <Combobox
                                        value={field.value == null ? null : String(field.value)}
                                        onChange={(v) => v && field.onChange(Number(v))}
                                        options={users.map(userOption)}
                                        onSearch={setUserSearch}
                                        selectedLabel={infoName(record?.user_info)}
                                        placeholder="Select trainee"
                                        searchPlaceholder="Search users..."
                                        emptyText="No users found."
                                    />
                                </FormControl>
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
                                <FormControl>
                                    <Combobox
                                        value={field.value || null}
                                        onChange={(v) => v && field.onChange(v)}
                                        options={trainingTypes.map((t) => ({ value: t.id, label: t.name }))}
                                        onSearch={setTrainingTypeSearch}
                                        selectedLabel={infoName(record?.training_type_info)}
                                        placeholder="Select training type"
                                        searchPlaceholder="Search training types..."
                                        emptyText="No training types found."
                                    />
                                </FormControl>
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

                    {/* Competency Level */}
                    <FormField
                        control={form.control}
                        name="level"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel>Competency Level {required.level && "*"}</FormLabel>
                                <Select
                                    value={field.value != null ? String(field.value) : "3"}
                                    onValueChange={(v) => field.onChange(Number(v))}
                                >
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select level" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        {LEVEL_OPTIONS.map((opt) => (
                                            <SelectItem key={opt.value} value={String(opt.value)}>
                                                {opt.label} — <span className="text-muted-foreground">{opt.hint}</span>
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <FormDescription>
                                    Assessed competency reached — Level 3 (Qualified) = works unsupervised.
                                </FormDescription>
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
                                <FormControl>
                                    <Combobox
                                        value={field.value == null ? null : String(field.value)}
                                        onChange={(v) => field.onChange(v === null ? null : Number(v))}
                                        options={users.map(userOption)}
                                        onSearch={setTrainerSearch}
                                        clearLabel="No trainer"
                                        selectedLabel={infoName(record?.trainer_info)}
                                        placeholder="Select trainer (optional)"
                                        searchPlaceholder="Search users..."
                                        emptyText="No users found."
                                    />
                                </FormControl>
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
