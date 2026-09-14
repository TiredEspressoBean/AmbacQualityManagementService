import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type TestConnectionParams = Parameters<typeof api.api_integrations_test_connection_create>[1]["params"];

export const useTestIntegrationConnection = () => {
    return useMutation<any, unknown, { id: TestConnectionParams["id"] }>({
        mutationFn: ({ id }) =>
            api.api_integrations_test_connection_create(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
    });
};
