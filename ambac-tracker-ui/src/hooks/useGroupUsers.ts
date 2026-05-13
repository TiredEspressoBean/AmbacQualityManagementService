import { useMutation, useQuery, queryOptions, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export const availableUsersOptions = () => queryOptions({
  queryKey: ["groups", "available-users"] as const,
  queryFn: () => api.api_Groups_available_users_list(),
});

export const useAvailableUsers = (options: any = {}) => {
  return useQuery({
    ...availableUsersOptions(),
    ...options,
  });
};

export const useAddUsersToGroup = (groupId: number | string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userIds: number[]) =>
      api.api_Groups_add_users_create(
        { user_ids: userIds },
        { params: { id: Number(groupId) } }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["group", groupId] as const });
      queryClient.invalidateQueries({ queryKey: ["group", String(groupId)] as const });
      queryClient.invalidateQueries({ queryKey: ["groups"] as const });
      queryClient.invalidateQueries({ queryKey: ["groups", "available-users"] as const });
    },
  });
};

export const useRemoveUsersFromGroup = (groupId: number | string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userIds: number[]) =>
      api.api_Groups_remove_users_create(
        { user_ids: userIds },
        { params: { id: Number(groupId) } }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["group", groupId] as const });
      queryClient.invalidateQueries({ queryKey: ["group", String(groupId)] as const });
      queryClient.invalidateQueries({ queryKey: ["groups"] as const });
      queryClient.invalidateQueries({ queryKey: ["groups", "available-users"] as const });
    },
  });
};
