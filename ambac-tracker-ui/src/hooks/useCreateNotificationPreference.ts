import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type CreateNotificationPreferenceInput = Parameters<typeof api.api_NotificationPreferences_create>[0];
type CreateNotificationPreferenceResponse = Awaited<ReturnType<typeof api.api_NotificationPreferences_create>>;

export const useCreateNotificationPreference = () => {
  const queryClient = useQueryClient();

  return useMutation<CreateNotificationPreferenceResponse, unknown, CreateNotificationPreferenceInput>({
    mutationFn: (data) =>
      api.api_NotificationPreferences_create(data, {
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["NotificationPreferences"] });
    },
  });
};
