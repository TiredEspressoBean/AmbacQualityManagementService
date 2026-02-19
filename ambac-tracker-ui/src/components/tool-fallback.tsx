import { CheckIcon, ChevronDownIcon, ChevronUpIcon, Loader2Icon } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

type ToolFallbackProps = {
  toolName: string;
  argsText: string;
  result?: any;
};

export const ToolFallback = ({
  toolName,
  argsText,
  result,
}: ToolFallbackProps) => {
  const [isCollapsed, setIsCollapsed] = useState(true);
  const isRunning = result === undefined;

  return (
    <div className="mb-4 flex w-full flex-col gap-3 rounded-lg border py-3">
      <div className="flex items-center gap-2 px-4">
        {isRunning ? (
          <Loader2Icon className="size-4 animate-spin" />
        ) : (
          <CheckIcon className="size-4" />
        )}
        <p className="flex-grow">
          {isRunning ? "Running" : "Used"} tool: <b>{toolName}</b>
        </p>
        <Button size="sm" variant="ghost" onClick={() => setIsCollapsed(!isCollapsed)}>
          {isCollapsed ? <ChevronDownIcon /> : <ChevronUpIcon />}
        </Button>
      </div>
      {!isCollapsed && (
        <div className="flex flex-col gap-2 border-t pt-2">
          <div className="px-4">
            <pre className="whitespace-pre-wrap">{argsText}</pre>
          </div>
          {result !== undefined && (
            <div className="border-t border-dashed px-4 pt-2">
              <p className="font-semibold">Result:</p>
              <pre className="whitespace-pre-wrap">
                {typeof result === "string"
                  ? result
                  : JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
