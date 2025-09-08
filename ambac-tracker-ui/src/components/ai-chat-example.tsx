// AiChatExample.tsx
import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { useLangGraphRuntime } from "@assistant-ui/react-langgraph";
import { Thread } from "@/components/thread";
import type { LangChainMessage } from "@assistant-ui/react-langgraph";
import { useRef, useState, useEffect } from "react";
import { Client } from "@langchain/langgraph-sdk";
import { useAuthUser } from "@/hooks/useAuthUser";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";



const API_URL = (import.meta.env.VITE_LANGGRAPH_API_URL as string) || `${window.location.origin}/lg`;
console.log('LangGraph API URL:', API_URL);
const ASSISTANT_ID =
    (import.meta.env.VITE_LANGGRAPH_ASSISTANT_ID as string) ?? "agent";

const client = new Client({ apiUrl: API_URL });

async function createThread() {
  const { thread_id } = await client.threads.create();
  return thread_id as string;
}

export function AiChatExample() {
  const threadIdRef = useRef<string | null>(null);
  const [apiToken, setApiToken] = useState<string | null>(null);
  const [isLoadingToken, setIsLoadingToken] = useState(false);
  const { data: user, isLoading: isLoadingUser } = useAuthUser();

  // Fetch API token when component mounts and user is available
  useEffect(() => {
    if (user && !apiToken && !isLoadingToken) {
      setIsLoadingToken(true);
      api.get_user_api_token({}, {
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      })
        .then(response => {
          setApiToken(response.token);
        })
        .catch(error => {
          console.error('Failed to get API token:', error);
        })
        .finally(() => {
          setIsLoadingToken(false);
        });
    }
  }, [user, apiToken]); // Removed isLoadingToken from dependencies to prevent infinite loop

  const runtime = useLangGraphRuntime({
    // Stream a user turn to the server using the SDK (messages mode)
    stream: async (messages: LangChainMessage[]) => {
      if (!threadIdRef.current) {
        threadIdRef.current = await createThread();
      }
      
      // Create client with user token configuration
      const clientConfig = apiToken 
        ? {
            config: { 
              configurable: { 
                user_token: apiToken 
              } 
            }
          }
        : {};
      
      // The SDK returns an AsyncIterable of "messages" events that assistant-ui understands
      return client.runs.stream(threadIdRef.current, ASSISTANT_ID, {
        input: { messages },
        streamMode: "messages",
        ...clientConfig
      });
    },

    // Create a brand-new thread when the UI requests it
    onSwitchToNewThread: async () => {
      threadIdRef.current = await createThread();
    },

    // (Optional) If your UI supports switching to an existing thread id, hydrate its state
    onSwitchToThread: async (threadId) => {
      const state = await client.threads.getState(threadId);
      threadIdRef.current = threadId;
      return {
        messages: state.values?.messages ?? [],
        interrupts: state.tasks?.[0]?.interrupts,
      };
    },
  });

  // Show loading state while fetching user or token
  if (isLoadingUser || (user && isLoadingToken)) {
    return (
      <div className="h-[calc(100vh-7rem)] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-2"></div>
          <p className="text-sm text-gray-600">Setting up AI chat...</p>
        </div>
      </div>
    );
  }

  // Show message if user is not authenticated
  if (!user) {
    return (
      <div className="h-[calc(100vh-7rem)] flex items-center justify-center">
        <p className="text-sm text-gray-600">Please log in to use AI chat.</p>
      </div>
    );
  }

  return (
      <AssistantRuntimeProvider runtime={runtime}>
        <div className="h-[calc(100vh-7rem)]">
          <Thread />
        </div>
      </AssistantRuntimeProvider>
  );
}
