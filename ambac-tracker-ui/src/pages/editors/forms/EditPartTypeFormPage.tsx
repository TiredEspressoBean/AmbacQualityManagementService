"use client"
import {useEffect} from "react";
import {toast} from "sonner";
import {useForm} from "react-hook-form";
import {zodResolver} from "@hookform/resolvers/zod";
import {z} from "zod";
import {Button} from "@/components/ui/button";
import {Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage} from "@/components/ui/form";
import {Input} from "@/components/ui/input";
import {useParams} from "@tanstack/react-router";

import {useRetrievePartType} from "@/hooks/useRetrievePartType";
import {useCreatePartType} from "@/hooks/useCreatePartType";
import {useUpdatePartType} from "@/hooks/useUpdatePartType";
import {DocumentUploader} from "@/pages/editors/forms/DocumentUploader.tsx";

// 🔐 Schema matching backend POST/PATCH expectations
const formSchema = z.object({
    name: z.string().min(1), ID_prefix: z.string().min(1),
    ERP_id: z.string().min(1),
});

export default function PartTypeFormPage() {
    const params = useParams({strict: false});
    const mode = params.id ? "edit" : "create";
    const partTypeId = params.id ? parseInt(params.id, 10) : undefined;

    const {data: partType} = useRetrievePartType({params: {id: partTypeId!}}, {enabled: mode === "edit" && !!partTypeId});

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema), defaultValues: {
            name: "", ID_prefix: "", ERP_id: ""
        },
    });

    useEffect(() => {
        if (mode === "edit" && partType) {
            form.reset({
                name: partType.name ?? "", ID_prefix: partType.ID_prefix ?? "", ERP_id: partType.ERP_id ?? "",
            });
        }
    }, [mode, partType, form]);

    const createPartType = useCreatePartType();
    const updatePartType = useUpdatePartType();

    function onSubmit(values: z.infer<typeof formSchema>) {
        if (mode === "edit" && partTypeId) {
            updatePartType.mutate({id: partTypeId, data: values}, {
                onSuccess: () => {
                    toast.success("Part Type updated successfully!");
                }, onError: (error) => {
                    console.error("Failed to update part type:", error);
                    toast.error("Failed to update the part type.");
                },
            });
        } else {
            createPartType.mutate(values, {
                onSuccess: () => {
                    toast.success("Part Type created successfully!");
                    form.reset();
                }, onError: (error) => {
                    console.error("Failed to create part type:", error);
                    toast.error("Failed to create the part type.");
                },
            });
        }
    }

    return (<div>
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8 max-w-3xl mx-auto py-10">
                <FormField
                    control={form.control}
                    name="name"
                    render={({field}) => (<FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                            <Input placeholder="e.g. Fuel Rail" {...field} />
                        </FormControl>
                        <FormDescription>The name of this type of part</FormDescription>
                        <FormMessage/>
                    </FormItem>)}
                />

                <FormField
                    control={form.control}
                    name="ID_prefix"
                    render={({field}) => (<FormItem>
                        <FormLabel>ERP ID Prefix</FormLabel>
                        <FormControl>
                            <Input placeholder="e.g. FR" {...field} />
                        </FormControl>
                        <FormDescription>The prefix for ERP-generated part numbers</FormDescription>
                        <FormMessage/>
                    </FormItem>)}
                />

                <FormField
                    control={form.control}
                    name="ERP_id"
                    render={({field}) => (
                        <FormItem>
                            <FormLabel>ERP ID</FormLabel>
                            <FormControl>
                                <Input placeholder="e.g. SV852-8R" {...field} />
                            </FormControl>
                            <FormDescription>The unique ERP identifier for this part type</FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <Button type="submit" disabled={createPartType.isPending || updatePartType.isPending}>
                    {mode === "edit" ? updatePartType.isPending ? "Saving..." : "Save Changes" : createPartType.isPending ? "Creating..." : "Create Part Type"}
                </Button>
            </form>
        </Form>
        {mode === "edit" && partTypeId && (

            <div className="max-w-3xl mx-auto py-6">
                <h3 className="text-lg font-semibold">Attach Documents</h3>
                <DocumentUploader objectId={partTypeId} contentType="parttypes"/>
            </div>)}
    </div>);
}
