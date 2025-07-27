"use client";

import {useEffect, useState} from "react";
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

import { useRetrieveErrorType } from "@/hooks/useRetrieveErrorType";
import { useCreateErrorType } from "@/hooks/useCreateErrorType";
import { useUpdateErrorType } from "@/hooks/useUpdateErrorType";
import {Popover, PopoverContent, PopoverTrigger} from "@/components/ui/popover.tsx";
import {cn} from "@/lib/utils.ts";
import {Check, ChevronsUpDown} from "lucide-react";
import {Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList} from "@/components/ui/command.tsx";
import {useRetrievePartTypes} from "@/hooks/useRetrievePartTypes.ts";

const formSchema = z.object({
    error_name: z.string().min(1, "Name is required"),
    error_example:z.string().min(1, "A basic example is required"),
    part_type: z.number()
});

export default function ErrorTypeFormPage() {
    const params = useParams({ strict: false });
    const mode = params.id ? "edit" : "create";
    const errorTypeId = params.id ? parseInt(params.id, 10) : undefined;
    const [partTypeSearch, setPartTypeSearch] = useState("")

    const { data: errorType } = useRetrieveErrorType(
        { params: { id: errorTypeId! } },
        { enabled: mode === "edit" && !!errorTypeId }
    );

    const { data: partTypes } = useRetrievePartTypes({ queries: { search: partTypeSearch } })

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            error_name: "",
            error_example: "",
            part_type: undefined,
        },
    });

    useEffect(() => {
        if (mode === "edit" && errorType) {
            form.reset({
                error_name: errorType.error_name ?? "",
            });
        }
    }, [mode, errorType, form]);

    const createErrorType = useCreateErrorType();
    const updateErrorType = useUpdateErrorType();

    function onSubmit(values: z.infer<typeof formSchema>) {
        if (mode === "edit" && errorTypeId) {
            updateErrorType.mutate(
                { id: errorTypeId, data: values },
                {
                    onSuccess: () => toast.success("Error type updated successfully!"),
                    onError: (err) => {
                        console.error("Update failed:", err);
                        toast.error("Failed to update error type.");
                    },
                }
            );
        } else {
            createErrorType.mutate(values, {
                onSuccess: () => {
                    toast.success("Error type created successfully!");
                    form.reset();
                },
                onError: (err) => {
                    console.error("Creation failed:", err);
                    toast.error("Failed to create error type.");
                },
            });
        }
    }

    return (
        <Form {...form}>
            <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-8 max-w-3xl mx-auto py-10"
            >
                <FormField
                    control={form.control}
                    name="error_name"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Name</FormLabel>
                            <FormControl>
                                <Input placeholder="e.g. CNC Lathe, CMM, Robot Arm" {...field} />
                            </FormControl>
                            <FormDescription>The category or type of error</FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="part_type"
                    render={({field}) => {
                        const selected = partTypes?.results.find(pt => pt.id === field.value)
                        return (
                            <FormItem className="flex flex-col">
                                <FormLabel>Part Type</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                className={cn("w-[300px] justify-between", !field.value && "text-muted-foreground")}
                                            >
                                                {selected?.name ?? "Select a part type"}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50"/>
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-[300px] p-0">
                                        <Command>
                                            <CommandInput
                                                value={partTypeSearch}
                                                onValueChange={setPartTypeSearch}
                                                placeholder="Search part types..."
                                            />
                                            <CommandList>
                                                <CommandEmpty>No part types found.</CommandEmpty>
                                                <CommandGroup>
                                                    {partTypes?.results.map((pt) => (
                                                        <CommandItem
                                                            key={pt.id}
                                                            value={pt.name}
                                                            onSelect={() => {
                                                                form.setValue("part_type", pt.id)
                                                                setPartTypeSearch("")
                                                            }}
                                                        >
                                                            <Check
                                                                className={cn("mr-2 h-4 w-4", pt.id === field.value ? "opacity-100" : "opacity-0")}
                                                            />
                                                            {pt.name}
                                                        </CommandItem>
                                                    ))}
                                                </CommandGroup>
                                            </CommandList>
                                        </Command>
                                    </PopoverContent>
                                </Popover>
                                <FormDescription>Choose the part type this step belongs to</FormDescription>
                                <FormMessage/>
                            </FormItem>
                        )
                    }}
                />

                <Button
                    type="submit"
                    disabled={createErrorType.isPending || updateErrorType.isPending}
                >
                    {mode === "edit"
                        ? updateErrorType.isPending
                            ? "Saving..."
                            : "Save Changes"
                        : createErrorType.isPending
                            ? "Creating..."
                            : "Create Error Type"}
                </Button>
            </form>
        </Form>
    );
}
