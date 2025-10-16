import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type UpdateNotificationPreferenceInput = Parameters<typeof api.api_NotificationPreferences_partial_update>[0];
type UpdateNotificationPreferenceConfig = Parameters<typeof api.api_NotificationPreferences_partial_update>[1];
type UpdateNotificationPreferenceParams = UpdateNotificationPreferenceConfig["params"];
type UpdateNotificationPreferenceResponse = Awaited<ReturnType<typeof api.api_NotificationPreferences_partial_update>>;

type UpdateNotificationPreferenceVariables = {
  id: UpdateNotificationPreferenceParams["id"];
  data: UpdateNotificationPreferenceInput;
};

export const useUpdateNotificationPreference = () => {
  const queryClient = useQueryClient();

  return useMutation<UpdateNotificationPreferenceResponse, unknown, UpdateNotificationPreferenceVariables>({
    mutationFn: ({ id, data }) =>
      api.api_NotificationPreferences_partial_update(data, {
        params: { id },
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["NotificationPreferences"],
        predicate: (query) => query.queryKey[0] === "NotificationPreferences",
      });
    },
  });
};
