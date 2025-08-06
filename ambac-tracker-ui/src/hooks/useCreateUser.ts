import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreateUserInput = Parameters<typeof api.api_User_create>[0];

type CreatePartResponse = Awaited<ReturnType<typeof api.api_User_create>>;

export const useCreateUser = () => {
    const queryClient = useQueryClient();

    return useMutation<CreatePartResponse, unknown, CreateUserInput>({
        mutationFn: (data) =>
            api.api_User_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["User"] });
        },
    });
};
