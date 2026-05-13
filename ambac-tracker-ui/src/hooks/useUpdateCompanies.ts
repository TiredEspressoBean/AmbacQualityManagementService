import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateCompaniesInput = Schema<"PatchedCompanyRequest">;
type UpdateCompaniesResponse = Schema<"Company">;

type UpdateCompaniesVariables = {
    id: string;
    data: UpdateCompaniesInput;
};

export const useUpdateCompanies = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateCompaniesResponse, unknown, UpdateCompaniesVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Companies_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateCompaniesResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["Companies"],
                predicate: (query) => query.queryKey[0] === "equipment",
            });
        },
    });
};
