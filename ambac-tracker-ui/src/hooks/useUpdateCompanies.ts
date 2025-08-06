import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact input (body) that the partial-update endpoint wants:
type UpdateCompaniesInput = Parameters<typeof api.api_Companies_partial_update>[0];

// 2️⃣ Infer the shape of the `params` object:
type UpdateCompaniesConfig = Parameters<typeof api.api_Companies_partial_update>[1];
type UpdateCompaniesParams = UpdateCompaniesConfig["params"];

// 3️⃣ Infer the response type, if you need it:
type UpdateCompaniesResponse = Awaited<ReturnType<typeof api.api_Companies_partial_update>>;

// 4️⃣ Compose the variables your hook will accept:
type UpdateCompaniesVariables = {
    id: UpdateCompaniesParams["id"];   // number
    data: UpdateCompaniesInput;        // exactly the patched-part payload
};

export const useUpdateCompanies = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateCompaniesResponse, unknown, UpdateCompaniesVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Companies_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["Companies"],
                predicate: (query) => query.queryKey[0] === "equipment",
            });
        },
    });
};
