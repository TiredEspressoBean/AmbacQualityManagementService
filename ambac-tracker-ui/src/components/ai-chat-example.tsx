// AiChatExample.tsx
import {AssistantRuntimeProvider, useAssistantRuntime} from "@assistant-ui/react";
import {useLangGraphRuntime} from "@assistant-ui/react-langgraph";
import {Thread} from "@/components/thread";
import type {LangChainMessage} from "@assistant-ui/react-langgraph";
import {useMemo, useRef, useState, useCallback, useEffect} from "react";
import {Client} from "@langchain/langgraph-sdk";
import {useQuery, useQueryClient} from "@tanstack/react-query";
import {useAuthUser} from "@/hooks/useAuthUser";
import {api} from "@/lib/api/generated";
import {getCookie} from "@/lib/utils";
import {EphemeralAttachmentAdapter} from "@/lib/attachmentAdapter";
import {ChatHistorySidebar} from "@/components/chat-history-sidebar";
import {SidebarProvider, SidebarInset} from "@/components/ui/sidebar";
import {useCreateChatSession, useUpdateChatSession, useChatSessions, CHAT_SESSIONS_QUERY_KEY} from "@/hooks/useChatSessions";

// Query key for API token
const API_TOKEN_QUERY_KEY = ['user-api-token'] as const;

// Token refresh interval (4 minutes - assuming 5 min expiry)
const TOKEN_STALE_TIME = 4 * 60 * 1000;
const TOKEN_REFETCH_INTERVAL = 4 * 60 * 1000;

// Fetch function for API token
const fetchApiToken = async () => {
    const response = await api.get_user_api_token(undefined, {
        headers: {"X-CSRFToken": getCookie("csrftoken")},
    });
    return response.token;
};

const API_URL = (import.meta.env.VITE_LANGGRAPH_API_URL as string) || `${window.location.origin}/lg`;
const ASSISTANT_ID = (import.meta.env.VITE_LANGGRAPH_ASSISTANT_ID as string) ?? "agent";

const langGraphClient = new Client({apiUrl: API_URL});

async function createThread() {
    const {thread_id} = await langGraphClient.threads.create();
    return thread_id as string;
}

// Inner component that has access to the runtime context
function ChatContent({
    currentThreadId,
    onThreadChange,
}: {
    currentThreadId: string | null;
    onThreadChange: (threadId: string | null) => void;
}) {
    const runtime = useAssistantRuntime();
    const initializedRef = useRef(false);

    const handleSwitchThread = useCallback(async (threadId: string) => {
        try {
            // Try the new API first, fall back to legacy
            if (runtime.threads?.switchToThread) {
                await runtime.threads.switchToThread(threadId);
            } else if ((runtime as any).switchToThread) {
                await (runtime as any).switchToThread(threadId);
            }
            onThreadChange(threadId);
        } catch (error) {
            console.error('Failed to switch thread:', error);
        }
    }, [runtime, onThreadChange]);

    const handleNewThread = useCallback(async () => {
        try {
            // Try the new API first, fall back to legacy
            if (runtime.threads?.switchToNewThread) {
                await runtime.threads.switchToNewThread();
            } else if ((runtime as any).switchToNewThread) {
                await (runtime as any).switchToNewThread();
            }
            onThreadChange(null); // Will be set when first message is sent
        } catch (error) {
            console.error('Failed to create new thread:', error);
        }
    }, [runtime, onThreadChange]);

    // Initialize with a new thread on mount to enable the composer
    useEffect(() => {
        if (initializedRef.current) return;
        initializedRef.current = true;

        // Only initialize a new thread if no thread is currently selected
        if (!currentThreadId) {
            console.log("[AI Chat] Initializing with new thread on mount");
            // Use the runtime API directly to avoid dependency issues
            const switchToNew = runtime.threads?.switchToNewThread ?? (runtime as any).switchToNewThread;
            if (switchToNew) {
                switchToNew().catch((error: unknown) => {
                    console.error('Failed to initialize new thread:', error);
                });
            }
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // Run only on mount

    return (
        <SidebarProvider defaultOpen={true}>
            <SidebarInset className="h-[calc(100vh-7rem)]">
                <Thread />
            </SidebarInset>
            <ChatHistorySidebar
                side="right"
                currentThreadId={currentThreadId}
                onSwitchThread={handleSwitchThread}
                onNewThread={handleNewThread}
            />
        </SidebarProvider>
    );
}

export function AiChatExample() {
    const threadIdRef = useRef<string | null>(null);
    const sessionIdRef = useRef<number | null>(null);
    const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
    const {data: user, isLoading: isLoadingUser} = useAuthUser();
    const createChatSession = useCreateChatSession();
    const updateChatSession = useUpdateChatSession();
    // Keep sessions query active so cache stays fresh for callbacks
    useChatSessions();
    const queryClient = useQueryClient();

    // API token with auto-refresh via React Query
    // Note: apiToken is not used directly - the query keeps the cache warm for fetchQuery calls in stream()
    const { data: _apiToken, isLoading: isLoadingToken } = useQuery({
        queryKey: API_TOKEN_QUERY_KEY,
        queryFn: fetchApiToken,
        enabled: !!user,
        staleTime: TOKEN_STALE_TIME,
        refetchInterval: TOKEN_REFETCH_INTERVAL,
        refetchOnWindowFocus: true,
        retry: 2,
    });

    // Save session to Django after first message (or find existing)
    const saveSessionToDjango = useCallback((threadId: string, firstMessage?: string) => {
        if (sessionIdRef.current) return; // Already have session ID

        // Get fresh sessions data from cache to avoid stale closure
        const freshSessionsData = queryClient.getQueryData(CHAT_SESSIONS_QUERY_KEY);
        const freshSessions: Array<{ id: number; langgraph_thread_id: string }> = freshSessionsData?.results ?? [];

        // Check if session already exists for this thread
        const existingSession = freshSessions.find((s) => s.langgraph_thread_id === threadId);
        if (existingSession) {
            sessionIdRef.current = existingSession.id;
            setCurrentThreadId(threadId);
            // Touch to update timestamp
            updateChatSession.mutate({ id: existingSession.id, data: {} });
            return;
        }

        const title = firstMessage
            ? (firstMessage.length > 50 ? firstMessage.substring(0, 47) + "..." : firstMessage)
            : "New Chat";

        createChatSession.mutate(
            { langgraph_thread_id: threadId, title },
            {
                onSuccess: (session) => {
                    sessionIdRef.current = session.id;
                    setCurrentThreadId(threadId);
                },
                onError: (error) => {
                    console.error('Failed to save chat session:', error);
                },
            }
        );
    }, [createChatSession, queryClient, updateChatSession]);

    // Touch session to update its timestamp (for reordering)
    const touchSession = useCallback(() => {
        if (!sessionIdRef.current) return;

        // Update with empty data just to trigger updated_at change
        updateChatSession.mutate({
            id: sessionIdRef.current,
            data: {}
        });
    }, [updateChatSession]);

    const attachmentAdapter = useMemo(() => new EphemeralAttachmentAdapter(), []);

    const runtime = useLangGraphRuntime({
        adapters: {
            attachments: attachmentAdapter,
        },
        // Create a brand-new thread when the UI requests it
        create: async () => {
            console.log("[AI Chat] create() called");
            try {
                const threadId = await createThread();
                console.log("[AI Chat] create() succeeded, threadId:", threadId);
                threadIdRef.current = threadId;
                sessionIdRef.current = null; // Reset session for new thread
                setCurrentThreadId(null);
                return { externalId: threadId };
            } catch (error) {
                console.error("[AI Chat] create() failed:", error);
                throw new Error("Unable to start chat. Please check your connection and try again.");
            }
        },

        // Load an existing thread
        load: async (externalId: string) => {
            console.log("[AI Chat] load() called with externalId:", externalId);
            try {
                const state = await langGraphClient.threads.getState(externalId);
                console.log("[AI Chat] load() got state, messages count:", state.values?.messages?.length ?? 0);
                threadIdRef.current = externalId;
                setCurrentThreadId(externalId);

                // Get fresh sessions data from cache to avoid stale closure
                const freshSessionsData = queryClient.getQueryData(CHAT_SESSIONS_QUERY_KEY);
                const freshSessions = freshSessionsData?.results ?? [];
                const session = freshSessions.find((s) => s.langgraph_thread_id === externalId);
                sessionIdRef.current = session?.id ?? null;

                const result = {
                    externalId,
                    messages: state.values?.messages ?? [],
                    interrupts: state.tasks?.[0]?.interrupts,
                };
                console.log("[AI Chat] load() returning:", { externalId, messagesCount: result.messages.length });
                return result;
            } catch (error) {
                console.error("[AI Chat] load() failed:", error);
                throw new Error("Unable to load conversation. It may have been deleted.");
            }
        },

        // Stream a user turn to the server using the SDK (messages mode)
        stream: async (messages: LangChainMessage[], { initialize }) => {
            console.log("[AI Chat] stream() called with", messages.length, "messages");
            // Initialize handles thread creation/loading automatically
            console.log("[AI Chat] stream() calling initialize()...");
            const initResult = await initialize();
            console.log("[AI Chat] stream() initialize() returned:", initResult);
            let { externalId } = initResult;

            // Workaround: If initialize() didn't create a thread, create one manually
            if (!externalId) {
                console.log("[AI Chat] stream() externalId is undefined, creating thread manually...");
                const threadId = await createThread();
                console.log("[AI Chat] stream() manually created thread:", threadId);
                externalId = threadId;
                threadIdRef.current = threadId;
                sessionIdRef.current = null;
            }
            console.log("[AI Chat] stream() proceeding with externalId:", externalId);

            threadIdRef.current = externalId;

            // Save to Django on first message, or touch existing session
            const firstUserMessage = messages.find(m => m.type === "human");
            const messageContent = typeof firstUserMessage?.content === "string"
                ? firstUserMessage.content
                : "";

            if (!sessionIdRef.current) {
                saveSessionToDjango(externalId, messageContent);
            } else {
                // Update timestamp for existing session
                touchSession();
            }

            // Get fresh token (uses cache if fresh, fetches if stale)
            let freshToken: string | null = null;
            try {
                freshToken = await queryClient.fetchQuery({
                    queryKey: API_TOKEN_QUERY_KEY,
                    queryFn: fetchApiToken,
                    staleTime: TOKEN_STALE_TIME,
                });
            } catch (tokenError) {
                console.error("Failed to fetch API token:", tokenError);
                // Continue without token - server will reject if auth required
            }

            const clientConfig = freshToken ? {
                config: {
                    configurable: {
                        user_token: freshToken
                    }
                }
            } : {};

            // Invalidate chat sessions query to reorder sidebar
            queryClient.invalidateQueries({ queryKey: CHAT_SESSIONS_QUERY_KEY });

            // Stream with error handling
            try {
                return langGraphClient.runs.stream(externalId, ASSISTANT_ID, {
                    input: {messages}, streamMode: "messages", ...clientConfig
                });
            } catch (error) {
                console.error("Failed to stream message:", error);
                throw new Error(
                    error instanceof Error
                        ? `Chat error: ${error.message}`
                        : "Failed to send message. Please try again."
                );
            }
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
            <ChatContent
                currentThreadId={currentThreadId}
                onThreadChange={setCurrentThreadId}
            />
        </AssistantRuntimeProvider>
    );
}
