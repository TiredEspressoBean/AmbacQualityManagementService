import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateUserInput = Schema<"PatchedUserRequest">;
type UpdateUserResponse = Schema<"User">;

type UpdateUserVariables = {
    id: number;
    data: UpdateUserInput;
};

export const useUpdateUser = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateUserResponse, unknown, UpdateUserVariables>({
        mutationFn: ({ id, data }) =>
            api.api_User_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateUserResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["User"],
                predicate: (query) => query.queryKey[0] === "User",
            });
        },
    });
};
