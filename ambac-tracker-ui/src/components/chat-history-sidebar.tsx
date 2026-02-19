import type { FC } from "react";
import { Plus, Archive, Trash2, MessageSquare, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import { useChatSessions, useDeleteChatSession, useArchiveChatSession } from "@/hooks/useChatSessions";

interface ChatHistorySidebarProps extends React.ComponentProps<typeof Sidebar> {
  currentThreadId: string | null;
  onSwitchThread: (threadId: string) => void;
  onNewThread: () => void;
}

export const ChatHistorySidebar: FC<ChatHistorySidebarProps> = ({
  currentThreadId,
  onSwitchThread,
  onNewThread,
  ...props
}) => {
  const { data: sessionsData, isLoading } = useChatSessions();
  const deleteSession = useDeleteChatSession();
  const archiveSession = useArchiveChatSession();

  // Handle paginated response
  const sessions = sessionsData?.results ?? [];

  // Filter out archived sessions for display
  const activeSessions = sessions.filter((s: { is_archived?: boolean }) => !s.is_archived);

  return (
    <Sidebar {...props}>
      <SidebarHeader className="mb-2 border-b">
        <div className="flex items-center justify-between p-2">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton size="lg" onClick={onNewThread}>
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                  <Plus className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">New Chat</span>
                </div>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </div>
      </SidebarHeader>

      <SidebarContent className="px-2">
        <ScrollArea className="flex-1">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : activeSessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <MessageSquare className="h-8 w-8 text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">No chat history yet</p>
              <p className="text-xs text-muted-foreground">Start a conversation!</p>
            </div>
          ) : (
            <div className="flex flex-col gap-1">
              {activeSessions.map((session: { id: number; langgraph_thread_id: string }) => (
                <ChatSessionItem
                  key={session.id}
                  session={session}
                  isActive={currentThreadId === session.langgraph_thread_id}
                  onSelect={() => onSwitchThread(session.langgraph_thread_id)}
                  onArchive={() => archiveSession.mutate(session.id)}
                  onDelete={() => deleteSession.mutate(session.id)}
                />
              ))}
            </div>
          )}
        </ScrollArea>
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  );
};

interface ChatSessionItemProps {
  session: {
    id: number;
    title: string;
    langgraph_thread_id: string;
    updated_at: string;
  };
  isActive: boolean;
  onSelect: () => void;
  onArchive: () => void;
  onDelete: () => void;
}

const ChatSessionItem: FC<ChatSessionItemProps> = ({
  session,
  isActive,
  onSelect,
  onArchive,
  onDelete,
}) => {
  return (
    <div
      className={cn(
        "group flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-muted/50 cursor-pointer",
        isActive && "bg-accent"
      )}
      onClick={onSelect}
    >
      <MessageSquare className="h-4 w-4 shrink-0 opacity-50" />
      <span className="truncate flex-1">{session.title || "New Chat"}</span>

      <div className="flex items-center shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="icon"
              variant="ghost"
              className="h-6 w-6"
              onClick={(e) => {
                e.stopPropagation();
                onArchive();
              }}
            >
              <Archive className="h-3 w-3" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">Archive</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="icon"
              variant="ghost"
              className="h-6 w-6 text-muted-foreground hover:text-destructive"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">Delete</TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
};
