import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateNotificationPreferenceInput = Schema<"PatchedNotificationPreferenceRequest">;
type UpdateNotificationPreferenceResponse = Schema<"NotificationPreference">;

type UpdateNotificationPreferenceVariables = {
  id: number;
  data: UpdateNotificationPreferenceInput;
};

export const useUpdateNotificationPreference = () => {
  const queryClient = useQueryClient();

  return useMutation<UpdateNotificationPreferenceResponse, unknown, UpdateNotificationPreferenceVariables>({
    mutationFn: ({ id, data }) =>
      api.api_NotificationPreferences_partial_update(data as never, {
        params: { id },
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      }) as Promise<UpdateNotificationPreferenceResponse>,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["NotificationPreferences"],
        predicate: (query) => query.queryKey[0] === "NotificationPreferences",
      });
    },
  });
};
