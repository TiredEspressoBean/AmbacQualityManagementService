import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

export function useDeleteNotificationPreference() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      api.api_NotificationPreferences_destroy(undefined, {
        params: { id },
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["NotificationPreferences"] });
    },
  });
}
