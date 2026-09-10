import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type AddNoteBody = Parameters<typeof api.api_Orders_add_note_create>[0];

type AddNoteInput = {
    orderId: string;
} & AddNoteBody;

export const useAddOrderNote = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({ orderId, message, visibility }: AddNoteInput) => {
            return api.api_Orders_add_note_create(
                { message, visibility },
                {
                    params: { id: orderId },
                    headers: { "X-CSRFToken": getCookie("csrftoken") },
                }
            );
        },
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({ queryKey: ["order", variables.orderId] });
        },
    });
};
