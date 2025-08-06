import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact input (body) that the partial-update endpoint wants:
type UpdateUserInput = Parameters<typeof api.api_User_partial_update>[0];

// 2️⃣ Infer the shape of the `params` object:
type UpdateUserConfig = Parameters<typeof api.api_User_partial_update>[1];
type UpdateUserParams = UpdateUserConfig["params"];

// 3️⃣ Infer the response type, if you need it:
type UpdateUserResponse = Awaited<ReturnType<typeof api.api_User_partial_update>>;

// 4️⃣ Compose the variables your hook will accept:
type UpdateUserVariables = {
    id: UpdateUserParams["id"];   // number
    data: UpdateUserInput;        // exactly the patched-part payload
};

export const useUpdateUser = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateUserResponse, unknown, UpdateUserVariables>({
        mutationFn: ({ id, data }) =>
            api.api_User_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["User"],
                predicate: (query) => query.queryKey[0] === "User",
            });
        },
    });
};
