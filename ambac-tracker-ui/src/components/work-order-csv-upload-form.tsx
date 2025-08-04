import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useUploadWorkOrdersCsv } from '@/hooks/useUploadWorkOrdersCsv'
import { toast } from 'sonner'
import { useState, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Upload, File, X } from 'lucide-react'

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

export function CompactWorkOrderUploadForm() {
    const form = useForm<FormValues>({
        resolver: zodResolver(schema),
    })

    const upload = useUploadWorkOrdersCsv()
    const [selectedFile, setSelectedFile] = useState<File | null>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)

    const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        if (file) {
            setSelectedFile(file)
            form.setValue('file', file)
            form.clearErrors('file')
        }
    }

    const handleRemoveFile = () => {
        setSelectedFile(null)
        form.setValue('file', undefined as any)
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }

    const onSubmit = ({ file }: FormValues) => {
        upload.mutate(file, {
            onSuccess: (data) => {
                const success = data.results.filter((r: any) => r.status === 'success').length
                const failed = data.results.filter((r: any) => r.status === 'error').length

                toast.success(`Upload complete: ${success} succeeded, ${failed} failed`)
                form.reset()
                setSelectedFile(null)
                if (fileInputRef.current) {
                    fileInputRef.current.value = ''
                }
            },
            onError: (err) => {
                console.error('❌ Upload error:', err)
                toast.error('Upload failed')
            },
        })
    }

    const error = form.formState.errors.file?.message

    return (
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex items-center gap-2">
            {/* Hidden file input */}
            <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleFileSelect}
                className="hidden"
            />

            {/* File selection area */}
            {!selectedFile ? (
                <Button
                    type="button"
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    className="h-9 px-3"
                >
                    <Upload className="h-4 w-4 mr-2" />
                    Choose File
                </Button>
            ) : (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-muted rounded-md text-sm">
                    <File className="h-4 w-4 text-muted-foreground" />
                    <span className="truncate max-w-32">{selectedFile.name}</span>
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={handleRemoveFile}
                        className="h-5 w-5 p-0 hover:bg-destructive hover:text-destructive-foreground"
                    >
                        <X className="h-3 w-3" />
                    </Button>
                </div>
            )}

            {/* Upload button */}
            <Button
                type="submit"
                disabled={!selectedFile || upload.isPending}
                size="sm"
            >
                {upload.isPending ? 'Uploading...' : 'Upload'}
            </Button>

            {/* Error message */}
            {error && (
                <span className="text-sm text-destructive">{error}</span>
            )}
        </form>
    )
}