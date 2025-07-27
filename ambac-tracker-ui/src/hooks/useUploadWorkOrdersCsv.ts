import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api/generated'
import { getCookie } from '@/lib/utils'

export function useUploadWorkOrdersCsv() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: async (file: File) => {
            // 🔧 Ensure File is from the correct module context
            const fixedFile = new File([file], file.name, {
                type: file.type,
                lastModified: file.lastModified,
            })

            console.log(fixedFile)

            return await api.api_WorkOrders_upload_csv_create(
                { file: fixedFile }, // ✅ Must be passed as an object with `file` key
                {
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                }
            )
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['workorders'] })
        },
    })
}
