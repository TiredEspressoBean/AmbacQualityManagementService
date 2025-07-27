'use client'

import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useUploadWorkOrdersCsv } from '@/hooks/useUploadWorkOrdersCsv'
import { toast } from 'sonner'
import { useState } from 'react'
import {
    Form,
    FormField,
    FormItem,
    FormLabel,
    FormControl,
    FormMessage,
} from '@/components/ui/form'
import {
    FileUploader,
    FileInput,
    FileUploaderContent,
    FileUploaderItem,
} from '@/components/ui/file-upload'
import { CloudUpload, Paperclip } from 'lucide-react'
import { Button } from '@/components/ui/button'

const schema = z.object({
    file: z
        .custom<File>((val) => val instanceof File, 'Please upload a file')
        .refine(
            (f) =>
                f.name.toLowerCase().endsWith('.csv') ||
                f.name.toLowerCase().endsWith('.xlsx') ||
                f.name.toLowerCase().endsWith('.xls'),
            { message: 'File must be .csv, .xlsx, or .xls' }
        ),
})

type FormValues = z.infer<typeof schema>

export function WorkOrderUploadForm() {
    const form = useForm<FormValues>({
        resolver: zodResolver(schema),
        defaultValues: {
            file: undefined,
        },
    })

    const upload = useUploadWorkOrdersCsv()
    const [files, setFiles] = useState<File[] | null>(null)

    const onSubmit = ({ file }: FormValues) => {
        upload.mutate(file, {
            onSuccess: (data) => {
                const success = data.results.filter((r: any) => r.status === 'success').length
                const failed = data.results.filter((r: any) => r.status === 'error').length

                toast.success(`Upload complete: ${success} succeeded, ${failed} failed`)
                form.reset()
                setFiles(null)
            },
            onError: (err) => {
                console.error('❌ Upload error:', err)
                toast.error('Upload failed')
            },
        })
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6 max-w-xl">
                <FormField
                    control={form.control}
                    name="file"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Upload Work Orders</FormLabel>
                            <FormControl>
                                <FileUploader
                                    value={files}
                                    onValueChange={(files) => {
                                        const file = files?.[0]
                                        setFiles(files)
                                        if (file) {
                                            field.onChange(file)
                                        }
                                    }}
                                    dropzoneOptions={{ maxFiles: 1, maxSize: 10 * 1024 * 1024 }}
                                    className="rounded-lg bg-background p-2"
                                >
                                    <FileInput className="outline-dashed outline-1 outline-slate-500">
                                        <div className="flex flex-col items-center justify-center p-8 w-full">
                                            <CloudUpload className="w-10 h-10 text-gray-500" />
                                            <p className="text-sm text-gray-500">
                                                <span className="font-semibold">Click to upload</span> or drag and drop
                                            </p>
                                            <p className="text-xs text-gray-500">CSV, XLSX, or XLS</p>
                                        </div>
                                    </FileInput>
                                    <FileUploaderContent>
                                        {files?.map((file, i) => (
                                            <FileUploaderItem key={i} index={i}>
                                                <Paperclip className="h-4 w-4" />
                                                <span>{file.name}</span>
                                            </FileUploaderItem>
                                        ))}
                                    </FileUploaderContent>
                                </FileUploader>
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />
                <Button type="submit" disabled={upload.isPending}>
                    {upload.isPending ? 'Uploading...' : 'Upload'}
                </Button>
            </form>
        </Form>
    )
}
