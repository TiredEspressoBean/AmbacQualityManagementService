// AiChatExample.tsx
import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { useLangGraphRuntime } from "@assistant-ui/react-langgraph";
import { Thread } from "@/components/thread";
import type { LangChainMessage } from "@assistant-ui/react-langgraph";
import { useRef } from "react";
import { Client } from "@langchain/langgraph-sdk";

const API_URL = `http://10.1.2.205:8123`;
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

  const runtime = useLangGraphRuntime({
    // Stream a user turn to the server using the SDK (messages mode)
    stream: async (messages: LangChainMessage[]) => {
      if (!threadIdRef.current) {
        threadIdRef.current = await createThread();
      }
      // The SDK returns an AsyncIterable of "messages" events that assistant-ui understands
      return client.runs.stream(threadIdRef.current, ASSISTANT_ID, {
        input: { messages },
        streamMode: "messages",
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

  return (
      <AssistantRuntimeProvider runtime={runtime}>
        <div className="h-[calc(100vh-7rem)]">
          <Thread />
        </div>
      </AssistantRuntimeProvider>
  );
}
