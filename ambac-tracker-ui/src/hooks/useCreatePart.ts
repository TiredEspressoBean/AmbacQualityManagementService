import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact “body” type that your create endpoint wants:
type CreatePartInput = Parameters<typeof api.api_Parts_create>[0];

// 2️⃣ (Optionally) infer the return type, if you need it:
type CreatePartResponse = Awaited<ReturnType<typeof api.api_Parts_create>>;

export const useCreatePart = () => {
    const queryClient = useQueryClient();

    return useMutation<CreatePartResponse, unknown, CreatePartInput>({
        mutationFn: (data) =>
            api.api_Parts_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["parts"] });
        },
    });
};
