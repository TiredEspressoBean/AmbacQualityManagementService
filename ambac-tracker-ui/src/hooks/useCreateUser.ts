import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateUserInput = Schema<"UserRequest">;
type CreateUserResponse = Schema<"User">;

export const useCreateUser = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateUserResponse, unknown, CreateUserInput>({
        mutationFn: (data) =>
            api.api_User_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateUserResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["User"] });
        },
    });
};
