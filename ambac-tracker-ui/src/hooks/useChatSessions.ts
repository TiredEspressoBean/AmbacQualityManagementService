import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type PaginatedChatSessionList } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

export const CHAT_SESSIONS_QUERY_KEY = ["chatSessions"];

const csrfHeaders = () => ({
  headers: { "X-CSRFToken": getCookie("csrftoken") },
});

// Infer types from the API
type CreateChatSessionInput = Parameters<typeof api.api_ChatSessions_create>[0];
type CreateChatSessionResponse = Awaited<ReturnType<typeof api.api_ChatSessions_create>>;

type UpdateChatSessionInput = Parameters<typeof api.api_ChatSessions_partial_update>[0];
type UpdateChatSessionConfig = Parameters<typeof api.api_ChatSessions_partial_update>[1];
type UpdateChatSessionParams = UpdateChatSessionConfig["params"];
type UpdateChatSessionResponse = Awaited<ReturnType<typeof api.api_ChatSessions_partial_update>>;

type UpdateChatSessionVariables = {
  id: UpdateChatSessionParams["id"];
  data: UpdateChatSessionInput;
};

/**
 * Hook to list all chat sessions for the current user
 */
export function useChatSessions() {
  return useQuery<PaginatedChatSessionList, Error>({
    queryKey: CHAT_SESSIONS_QUERY_KEY,
    queryFn: () => api.api_ChatSessions_list({}),
  });
}

/**
 * Hook to create a new chat session
 */
export function useCreateChatSession() {
  const queryClient = useQueryClient();

  return useMutation<CreateChatSessionResponse, unknown, CreateChatSessionInput>({
    mutationFn: (data) =>
      api.api_ChatSessions_create(data, csrfHeaders()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHAT_SESSIONS_QUERY_KEY });
    },
  });
}

/**
 * Hook to update a chat session (e.g., rename)
 */
export function useUpdateChatSession() {
  const queryClient = useQueryClient();

  return useMutation<UpdateChatSessionResponse, unknown, UpdateChatSessionVariables>({
    mutationFn: ({ id, data }) =>
      api.api_ChatSessions_partial_update(data, { params: { id }, ...csrfHeaders() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHAT_SESSIONS_QUERY_KEY });
    },
  });
}

/**
 * Hook to delete a chat session
 */
export function useDeleteChatSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.api_ChatSessions_destroy(undefined, { id, ...csrfHeaders() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHAT_SESSIONS_QUERY_KEY });
    },
  });
}

/**
 * Hook to archive a chat session
 */
export function useArchiveChatSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.api_ChatSessions_archive_create(undefined, { id, ...csrfHeaders() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHAT_SESSIONS_QUERY_KEY });
    },
  });
}

/**
 * Hook to unarchive a chat session
 */
export function useUnarchiveChatSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.api_ChatSessions_unarchive_create(undefined, { id, ...csrfHeaders() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHAT_SESSIONS_QUERY_KEY });
    },
  });
}
