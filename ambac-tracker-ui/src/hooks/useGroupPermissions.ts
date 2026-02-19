import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export type AvailablePermission = {
  id: string;
  codename: string;
  name: string;
  content_type: string;
};

export const useAvailablePermissions = (options: any = {}) => {
  return useQuery<AvailablePermission[]>({
    queryKey: ["groups", "available-permissions"],
    queryFn: () => api.api_Groups_available_permissions_list() as Promise<AvailablePermission[]>,
    ...options,
  });
};

export const useAddPermissionsToGroup = (groupId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (permissionIds: string[]) =>
      api.api_Groups_add_permissions_create(
        { permission_ids: permissionIds },
        { params: { id: groupId } }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["group", groupId] });
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      queryClient.invalidateQueries({ queryKey: ["groups", "available-permissions"] });
    },
  });
};

export const useRemovePermissionsFromGroup = (groupId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (permissionIds: string[]) =>
      api.api_Groups_remove_permissions_create(
        { permission_ids: permissionIds },
        { params: { id: groupId } }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["group", groupId] });
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      queryClient.invalidateQueries({ queryKey: ["groups", "available-permissions"] });
    },
  });
};

export const useSetGroupPermissions = (groupId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (permissionIds: string[]) =>
      api.api_Groups_set_permissions_create(
        { permission_ids: permissionIds },
        { params: { id: groupId } }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["group", groupId] });
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      queryClient.invalidateQueries({ queryKey: ["groups", "available-permissions"] });
    },
  });
};
