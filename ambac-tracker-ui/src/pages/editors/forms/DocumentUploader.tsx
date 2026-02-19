import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import {
    Form,
    FormField,
    FormItem,
    FormLabel,
    FormControl,
    FormMessage,
} from "@/components/ui/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectTrigger,
    SelectValue,
    SelectContent,
    SelectItem,
} from "@/components/ui/select";

import { useCreateDocument } from "@/hooks/useCreateDocument";
import { schemas } from "@/lib/api/generated.ts";

const formSchema = z.object({
    file: z.instanceof(File),
    classification: schemas.ClassificationEnum,
});

type FormValues = z.infer<typeof formSchema>;

export function DocumentUploader({
                                     objectId,
                                     contentType,
                                     documentTypeCode,
                                     title = "Attach Document",
                                     compact = false,
                                 }: {
    objectId: string | number;
    contentType: string;
    documentTypeCode?: string; // e.g., "CUST_APPR" for customer approval evidence
    title?: string;
    compact?: boolean;
}) {
    const [fileInputKey, setFileInputKey] = useState(Date.now());

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            classification: "internal",
        },
    });

    const { mutate: uploadDocument, isPending, isSuccess } = useCreateDocument();

    function onSubmit(values: FormValues) {
        const formData = new FormData();
        formData.append("file", values.file);
        formData.append("classification", values.classification);
        formData.append("object_id", String(objectId));
        formData.append("content_type", contentType);
        if (documentTypeCode) {
            formData.append("document_type_code", documentTypeCode);
        }

        // backend now fills file_name automatically from the file if omitted

        uploadDocument(formData, {
            onSuccess: () => {
                form.reset();
                setFileInputKey(Date.now()); // reset file input
            },
        });
    }

    return (
        <div className={compact ? "space-y-2" : "space-y-4"}>
            {!compact && <h4 className="font-medium">{title}</h4>}
            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className={compact ? "flex items-end gap-2" : "space-y-4"}>
                    <FormField
                        control={form.control}
                        name="file"
                        render={({ field: { onChange } }) => (
                            <FormItem>
                                <FormLabel>File</FormLabel>
                                <FormControl>
                                    <Input
                                        key={fileInputKey}
                                        type="file"
                                        accept="*/*"
                                        onChange={(e) => onChange(e.target.files?.[0])}
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="classification"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Classification</FormLabel>
                                <FormControl>
                                    <Select onValueChange={field.onChange} value={field.value}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select classification" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {schemas.ClassificationEnum.options.map((level) => (
                                                <SelectItem key={level} value={level}>
                                                    {level.charAt(0).toUpperCase() + level.slice(1)}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <Button type="submit" disabled={isPending}>
                        {isPending ? "Uploading..." : "Upload"}
                    </Button>
                </form>
            </Form>
            {isSuccess && (
                <p className="text-green-600 text-sm">Upload successful!</p>
            )}
        </div>
    );
}
