"use client"
import {useEffect} from "react";
import {toast} from "sonner";
import {useForm} from "react-hook-form";
import {zodResolver} from "@hookform/resolvers/zod";
import {z} from "zod";
import {Button} from "@/components/ui/button";
import {Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage} from "@/components/ui/form";
import {Input} from "@/components/ui/input";
import {Checkbox} from "@/components/ui/checkbox";
import {useParams} from "@tanstack/react-router";

import {useRetrievePartType} from "@/hooks/useRetrievePartType";
import {useCreatePartType} from "@/hooks/useCreatePartType";
import {useUpdatePartType} from "@/hooks/useUpdatePartType";
import {DocumentUploader} from "@/pages/editors/forms/DocumentUploader.tsx";
import {schemas} from "@/lib/api/generated";
import {isFieldRequired} from "@/lib/zod-config";

// Use generated schema - error messages handled by global error map
const formSchema = schemas.PartTypesRequest.pick({
    name: true,
    ID_prefix: true,
    ERP_id: true,
    itar_controlled: true,
    eccn: true,
    usml_category: true,
});

type FormValues = z.infer<typeof formSchema>;

// Pre-compute required fields for labels
const required = {
    name: isFieldRequired(formSchema.shape.name),
    ID_prefix: isFieldRequired(formSchema.shape.ID_prefix),
    ERP_id: isFieldRequired(formSchema.shape.ERP_id),
    itar_controlled: isFieldRequired(formSchema.shape.itar_controlled),
    eccn: isFieldRequired(formSchema.shape.eccn),
    usml_category: isFieldRequired(formSchema.shape.usml_category),
};

export default function PartTypeFormPage() {
    const params = useParams({strict: false});
    const mode = params.id ? "edit" : "create";
    const partTypeId = params.id;

    const {data: partType} = useRetrievePartType({params: {id: partTypeId!}}, {enabled: mode === "edit" && !!partTypeId});

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema), defaultValues: {
            name: "",
            ID_prefix: "",
            ERP_id: "",
            itar_controlled: false,
            eccn: "",
            usml_category: "",
        },
    });

    useEffect(() => {
        if (mode === "edit" && partType) {
            form.reset({
                name: partType.name ?? "",
                ID_prefix: partType.ID_prefix ?? "",
                ERP_id: partType.ERP_id ?? "",
                itar_controlled: partType.itar_controlled ?? false,
                eccn: partType.eccn ?? "",
                usml_category: partType.usml_category ?? "",
            });
        }
    }, [mode, partType, form]);

    const createPartType = useCreatePartType();
    const updatePartType = useUpdatePartType();

    function onSubmit(values: FormValues) {
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
                        <FormLabel required={required.name}>Name</FormLabel>
                        <FormControl>
                            <Input placeholder="e.g. Fuel Rail" {...field} />
                        </FormControl>
                        <FormDescription>The name of this type of part</FormDescription>
                        <FormMessage/>
                    </FormItem>)}
                />

                <div className="grid grid-cols-2 gap-4">
                    <FormField
                        control={form.control}
                        name="ID_prefix"
                        render={({field}) => (<FormItem>
                            <FormLabel required={required.ID_prefix}>ERP ID Prefix</FormLabel>
                            <FormControl>
                                <Input placeholder="e.g. FR" {...field} value={field.value ?? ""} />
                            </FormControl>
                            <FormDescription>Prefix for ERP-generated part numbers</FormDescription>
                            <FormMessage/>
                        </FormItem>)}
                    />

                    <FormField
                        control={form.control}
                        name="ERP_id"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel required={required.ERP_id}>ERP ID</FormLabel>
                                <FormControl>
                                    <Input placeholder="e.g. SV852-8R" {...field} value={field.value ?? ""} />
                                </FormControl>
                                <FormDescription>Unique ERP identifier</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <FormField
                    control={form.control}
                    name="itar_controlled"
                    render={({field}) => (
                        <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                            <FormControl>
                                <Checkbox
                                    checked={field.value ?? false}
                                    onCheckedChange={field.onChange}
                                />
                            </FormControl>
                            <div className="space-y-1 leading-none">
                                <FormLabel>ITAR Controlled</FormLabel>
                                <FormDescription>
                                    This part type is subject to ITAR export controls
                                </FormDescription>
                            </div>
                        </FormItem>
                    )}
                />

                <div className="grid grid-cols-2 gap-4">
                    <FormField
                        control={form.control}
                        name="eccn"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel required={required.eccn}>ECCN</FormLabel>
                                <FormControl>
                                    <Input placeholder="e.g. 9A003.a" {...field} value={field.value ?? ""} />
                                </FormControl>
                                <FormDescription>Export Control Classification Number</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="usml_category"
                        render={({field}) => (
                            <FormItem>
                                <FormLabel required={required.usml_category}>USML Category</FormLabel>
                                <FormControl>
                                    <Input placeholder="e.g. IV(h)" {...field} value={field.value ?? ""} />
                                </FormControl>
                                <FormDescription>US Munitions List category</FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

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
