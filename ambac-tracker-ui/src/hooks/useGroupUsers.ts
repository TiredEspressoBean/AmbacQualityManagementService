import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export const useAvailableUsers = (options: any = {}) => {
  return useQuery({
    queryKey: ["groups", "available-users"],
    queryFn: () => api.api_Groups_available_users_list(),
    ...options,
  });
};

export const useAddUsersToGroup = (groupId: number | string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userIds: number[]) =>
      api.api_Groups_add_users_create(
        { user_ids: userIds },
        { params: { id: groupId } }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["group", groupId] });
      queryClient.invalidateQueries({ queryKey: ["group", String(groupId)] });
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      queryClient.invalidateQueries({ queryKey: ["groups", "available-users"] });
    },
  });
};

export const useRemoveUsersFromGroup = (groupId: number | string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userIds: number[]) =>
      api.api_Groups_remove_users_create(
        { user_ids: userIds },
        { params: { id: groupId } }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["group", groupId] });
      queryClient.invalidateQueries({ queryKey: ["group", String(groupId)] });
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      queryClient.invalidateQueries({ queryKey: ["groups", "available-users"] });
    },
  });
};
