import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateNotificationPreferenceInput = Schema<"NotificationPreferenceRequest">;
type CreateNotificationPreferenceResponse = Schema<"NotificationPreference">;

export const useCreateNotificationPreference = () => {
  const queryClient = useQueryClient();

  return useMutation<CreateNotificationPreferenceResponse, unknown, CreateNotificationPreferenceInput>({
    mutationFn: (data) =>
      api.api_NotificationPreferences_create(data as never, {
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      }) as Promise<CreateNotificationPreferenceResponse>,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["NotificationPreferences"] });
    },
  });
};
