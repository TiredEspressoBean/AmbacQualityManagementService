import {
  ThreadPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  ActionBarPrimitive,
  BranchPickerPrimitive,
  ErrorPrimitive,
} from "@assistant-ui/react";
import type { FC } from "react";
import {
  ArrowDownIcon,
  ArrowUpIcon,
  PlusIcon,
  CopyIcon,
  CheckIcon,
  PencilIcon,
  RefreshCwIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  Square,
} from "lucide-react";

import { TooltipIconButton } from "@/components/tooltip-icon-button";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { MarkdownText } from "./markdown-text";
import { ToolFallback } from "./tool-fallback";

export const Thread: FC = () => {
  return (
      <ThreadPrimitive.Root
          // Root should be allowed to shrink; parent provides the height
          className="bg-background flex h-full min-h-0 flex-col"
          style={{
            ["--thread-max-width" as string]: "48rem",
            ["--thread-padding-x" as string]: "1rem",
          }}
      >
        {/* Viewport = scrollable area per docs */}
        <ThreadPrimitive.Viewport className="relative flex min-w-0 flex-1 min-h-0 flex-col gap-4 overflow-y-auto scroll-smooth">
          <ThreadWelcome />

          <ThreadPrimitive.Messages
              components={{
                UserMessage,
                EditComposer,
                AssistantMessage,
              }}
          />

          {/* spacer so last bubble isn’t kissing the composer */}
          <ThreadPrimitive.If empty={false}>
            <motion.div className="min-h-6 min-w-6 shrink-0" />
          </ThreadPrimitive.If>

          <ThreadScrollToBottom />
        </ThreadPrimitive.Viewport>

        <Composer />
      </ThreadPrimitive.Root>
  );
};

const ThreadScrollToBottom: FC = () => {
  return (
      <ThreadPrimitive.ScrollToBottom asChild>
        <TooltipIconButton
            tooltip="Scroll to bottom"
            variant="outline"
            // anchored inside the viewport, floating above the composer
            className="absolute bottom-24 right-4 z-10 rounded-full border bg-background/90 p-3 shadow-lg backdrop-blur disabled:opacity-0"
        >
          <ArrowDownIcon />
        </TooltipIconButton>
      </ThreadPrimitive.ScrollToBottom>
  );
};

const ThreadWelcome: FC = () => {
  return (
      <ThreadPrimitive.Empty>
        <div className="mx-auto flex w-full max-w-[var(--thread-max-width)] flex-grow flex-col px-[var(--thread-padding-x)]">
          <div className="flex w-full flex-grow flex-col items-center justify-center">
            <div className="flex size-full flex-col justify-center px-8 md:mt-20">
              <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={{ delay: 0.5 }}
                  className="text-2xl font-semibold"
              >
                Hello there!
              </motion.div>
              <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={{ delay: 0.6 }}
                  className="text-2xl text-muted-foreground/65"
              >
                How can I help you today?
              </motion.div>
            </div>
          </div>
        </div>
      </ThreadPrimitive.Empty>
  );
};

const ThreadWelcomeSuggestions: FC = () => {
  return (
      <div className="grid w-full gap-2 sm:grid-cols-2">
        {[
          { title: "Help me analyze", label: "quality control data", action: "Help me analyze quality control data and identify trends" },
          { title: "Create a report", label: "for production metrics", action: "Create a report summarizing production metrics and efficiency" },
          { title: "Explain the process", label: "for part documentation", action: "Explain the process for part documentation and compliance tracking" },
          { title: "Draft an email", label: "about order status", action: "Draft a professional email about order status updates" },
        ].map((suggestedAction, index) => (
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                transition={{ delay: 0.05 * index }}
                key={`suggested-action-${suggestedAction.title}-${index}`}
                className="[&:nth-child(n+3)]:hidden sm:[&:nth-child(n+3)]:block"
            >
              <ThreadPrimitive.Suggestion prompt={suggestedAction.action} method="replace" autoSend asChild>
                <Button
                    variant="ghost"
                    className="h-auto w-full flex-1 flex-wrap items-start justify-start gap-1 rounded-xl border px-4 py-3.5 text-left text-sm dark:hover:bg-accent/60 sm:flex-col"
                    aria-label={suggestedAction.action}
                >
                  <span className="font-medium">{suggestedAction.title}</span>
                  <p className="text-muted-foreground">{suggestedAction.label}</p>
                </Button>
              </ThreadPrimitive.Suggestion>
            </motion.div>
        ))}
      </div>
  );
};

const Composer: FC = () => {
  return (
      <div className="bg-background relative mx-auto w-full max-w-[var(--thread-max-width)] px-[var(--thread-padding-x)] pb-4 md:pb-6">
        <ThreadPrimitive.Empty>
          <div className="mb-3">
            <ThreadWelcomeSuggestions />
          </div>
        </ThreadPrimitive.Empty>

        {/* Unified surface: border & rounding on the wrapper, not the input */}
        <ComposerPrimitive.Root
            className="relative flex w-full flex-col rounded-2xl border border-border bg-muted"
        >
          <ComposerPrimitive.Input
              placeholder="Send a message..."
              rows={1}
              autoFocus
              aria-label="Message input"
              className="
            max-h-[calc(50dvh)] min-h-16 w-full resize-none
            bg-transparent px-4 pb-3 pt-2 text-[14px] text-foreground
            outline-none ring-0 focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0
          "
          />

          <ComposerAction />
        </ComposerPrimitive.Root>
      </div>
  );
};

const ComposerAction: FC = () => {
  return (
      <div className="relative flex items-center justify-between border-t border-border bg-muted p-2 rounded-b-2xl">
        <TooltipIconButton
            tooltip="Attach file"
            variant="ghost"
            className="p-3.5 hover:bg-foreground/15 dark:hover:bg-background/50"
            onClick={() => console.log("Attachment clicked - not implemented")}
        >
          <PlusIcon />
        </TooltipIconButton>

        <ThreadPrimitive.If running={false}>
          <ComposerPrimitive.Send asChild>
            <Button
                type="submit"
                variant="default"
                className="size-8 rounded-full border border-muted-foreground/60 hover:bg-primary/75 dark:border-muted-foreground/90"
                aria-label="Send message"
            >
              <ArrowUpIcon className="size-5" />
            </Button>
          </ComposerPrimitive.Send>
        </ThreadPrimitive.If>

        <ThreadPrimitive.If running>
          <ComposerPrimitive.Cancel asChild>
            <Button
                type="button"
                variant="default"
                className="size-8 rounded-full border border-muted-foreground/60 hover:bg-primary/75 dark:border-muted-foreground/90"
                aria-label="Stop generating"
            >
              <Square className="size-3.5 fill-white dark:size-4 dark:fill-black" />
            </Button>
          </ComposerPrimitive.Cancel>
        </ThreadPrimitive.If>
      </div>
  );
};


const MessageError: FC = () => {
  return (
      <MessagePrimitive.Error>
        <ErrorPrimitive.Root className="mt-2 rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive dark:bg-destructive/5 dark:text-red-200">
          <ErrorPrimitive.Message className="line-clamp-2" />
        </ErrorPrimitive.Root>
      </MessagePrimitive.Error>
  );
};

const AssistantMessage: FC = () => {
  return (
      <MessagePrimitive.Root asChild>
        <motion.div
            className="relative mx-auto grid w-full max-w-[var(--thread-max-width)] grid-cols-[auto_auto_1fr] grid-rows-[auto_1fr] px-[var(--thread-padding-x)] py-4"
            initial={{ y: 5, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            data-role="assistant"
        >
          {/* Avatar */}
          <div className="col-start-1 row-start-1 flex size-8 shrink-0 items-center justify-center rounded-full ring-1 ring-border bg-background">
            <StarIcon size={14} />
          </div>

          {/* Bubble */}
          <div className="col-span-2 col-start-2 row-start-1 ml-4">
            <div className="break-words rounded-3xl bg-muted/40 px-5 py-2.5 leading-6 text-[14px] text-foreground dark:bg-muted/20">
              <MessagePrimitive.Parts
                  components={{
                    Text: MarkdownText,
                    tools: { Fallback: ToolFallback },
                  }}
              />
            </div>
            <MessageError />
          </div>

          <AssistantActionBar />
          <BranchPicker className="col-start-2 row-start-2 -ml-2 mr-2" />
        </motion.div>
      </MessagePrimitive.Root>
  );
};

const AssistantActionBar: FC = () => {
  return (
      <ActionBarPrimitive.Root
          hideWhenRunning
          autohide="not-last"
          autohideFloat="single-branch"
          className="col-start-3 row-start-2 ml-3 mt-3 flex gap-1 text-muted-foreground
                 data-floating:absolute data-floating:mt-2 data-floating:rounded-md data-floating:border data-floating:bg-background data-floating:p-1 data-floating:shadow-sm"
      >
        <ActionBarPrimitive.Copy asChild>
          <TooltipIconButton tooltip="Copy">
            <MessagePrimitive.If copied>
              <CheckIcon />
            </MessagePrimitive.If>
            <MessagePrimitive.If copied={false}>
              <CopyIcon />
            </MessagePrimitive.If>
          </TooltipIconButton>
        </ActionBarPrimitive.Copy>

        <ActionBarPrimitive.Reload asChild>
          <TooltipIconButton tooltip="Refresh">
            <RefreshCwIcon />
          </TooltipIconButton>
        </ActionBarPrimitive.Reload>
      </ActionBarPrimitive.Root>
  );
};

const UserMessage: FC = () => {
  return (
      <MessagePrimitive.Root asChild>
        <motion.div
            className="mx-auto grid w-full max-w-[var(--thread-max-width)] auto-rows-auto grid-cols-[minmax(72px,1fr)_auto] gap-y-1 px-[var(--thread-padding-x)] py-4 [&:where(>*)]:col-start-2"
            initial={{ y: 5, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            data-role="user"
        >
          <UserActionBar />

          <div className="col-start-2 break-words rounded-3xl bg-muted px-5 py-2.5 text-[14px] text-foreground">
            <MessagePrimitive.Content components={{ Text: MarkdownText }} />
          </div>

          <BranchPicker className="col-span-full col-start-1 row-start-3 -mr-1 justify-end" />
        </motion.div>
      </MessagePrimitive.Root>
  );
};

const UserActionBar: FC = () => {
  return (
      <ActionBarPrimitive.Root
          hideWhenRunning
          autohide="not-last"
          className="col-start-1 mr-3 mt-2.5 flex flex-col items-end"
      >
        <ActionBarPrimitive.Edit asChild>
          <TooltipIconButton tooltip="Edit">
            <PencilIcon />
          </TooltipIconButton>
        </ActionBarPrimitive.Edit>
      </ActionBarPrimitive.Root>
  );
};

const EditComposer: FC = () => {
  return (
      <div className="mx-auto w-full max-w-[var(--thread-max-width)] px-[var(--thread-padding-x)]">
        <ComposerPrimitive.Root className="ml-auto flex w-full max-w-[87.5%] flex-col rounded-xl bg-muted">
          <ComposerPrimitive.Input
              className="text-foreground flex min-h-[60px] w-full resize-none bg-transparent p-4 outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              autoFocus
          />

          <div className="mx-3 mb-3 flex items-center justify-center gap-2 self-end">
            <ComposerPrimitive.Cancel asChild>
              <Button variant="ghost" size="sm" aria-label="Cancel edit">
                Cancel
              </Button>
            </ComposerPrimitive.Cancel>
            <ComposerPrimitive.Send asChild>
              <Button size="sm" aria-label="Update message">
                Update
              </Button>
            </ComposerPrimitive.Send>
          </div>
        </ComposerPrimitive.Root>
      </div>
  );
};

const BranchPicker: FC<BranchPickerPrimitive.Root.Props> = ({ className, ...rest }) => {
  return (
      <BranchPickerPrimitive.Root
          hideWhenSingleBranch
          className={cn("inline-flex items-center text-xs text-muted-foreground", className)}
          {...rest}
      >
        <BranchPickerPrimitive.Previous asChild>
          <TooltipIconButton tooltip="Previous">
            <ChevronLeftIcon />
          </TooltipIconButton>
        </BranchPickerPrimitive.Previous>
        <span className="font-medium">
        <BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
      </span>
        <BranchPickerPrimitive.Next asChild>
          <TooltipIconButton tooltip="Next">
            <ChevronRightIcon />
          </TooltipIconButton>
        </BranchPickerPrimitive.Next>
      </BranchPickerPrimitive.Root>
  );
};

const StarIcon = ({ size = 14 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 0L9.79611 6.20389L16 8L9.79611 9.79611L8 16L6.20389 9.79611L0 8L6.20389 6.20389L8 0Z" fill="currentColor" />
    </svg>
);
