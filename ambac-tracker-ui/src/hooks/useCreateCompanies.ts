import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateCompanyInput = Schema<"CompanyRequest">;
type CreateCompanyResponse = Schema<"Company">;

export const useCreateCompanies = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateCompanyResponse, unknown, CreateCompanyInput>({
        mutationFn: (data) =>
            api.api_Companies_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateCompanyResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["Companies"] });
        },
    });
};
