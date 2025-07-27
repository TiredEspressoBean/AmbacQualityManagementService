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
                                 }: {
    objectId: number;
    contentType: string;
}) {
    const [fileInputKey, setFileInputKey] = useState(Date.now());

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            classification: "internal",
        },
    });

    const { mutate: uploadDocument, isLoading, isSuccess } = useCreateDocument();

    function onSubmit(values: FormValues) {
        const formData = new FormData();
        formData.append("file", values.file);
        formData.append("classification", values.classification);
        formData.append("object_id", String(objectId));
        formData.append("content_type", contentType);

        // backend now fills file_name automatically from the file if omitted

        uploadDocument(formData, {
            onSuccess: () => {
                form.reset();
                setFileInputKey(Date.now()); // reset file input
            },
        });
    }

    return (
        <div className="border p-4 rounded-xl space-y-4">
            <h3 className="text-lg font-medium">Attach Document</h3>
            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                    <FormField
                        control={form.control}
                        name="file"
                        render={({ field: { onChange, ...field } }) => (
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

                    <Button type="submit" disabled={isLoading}>
                        {isLoading ? "Uploading..." : "Upload"}
                    </Button>
                </form>
            </Form>
            {isSuccess && (
                <p className="text-green-600 text-sm">Upload successful!</p>
            )}
        </div>
    );
}
