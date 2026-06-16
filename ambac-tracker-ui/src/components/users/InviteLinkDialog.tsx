/**
 * Shows a user's invitation / access link with a Copy button.
 *
 * Onboarding must work even when email delivery is off (the app's email
 * lane is a no-op during the GCC High migration). Wherever an invite email
 * would have carried the signup link, an admin can instead copy it from here
 * and hand it over directly. The link is `{FRONTEND_URL}/signup?token=…`,
 * already built server-side.
 */
import { Check, Copy } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";

type InviteLinkDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** The signup link to surface. When null the dialog renders nothing. */
  url: string | null;
  /** Optional email shown in the description for context. */
  email?: string;
  title?: string;
  description?: string;
};

export function InviteLinkDialog({
  open,
  onOpenChange,
  url,
  email,
  title = "Invitation link",
  description,
}: InviteLinkDialogProps) {
  const { isCopied, copyToClipboard } = useCopyToClipboard();

  const defaultDescription = email
    ? `Send this link to ${email} so they can set a password and sign in. It expires in 7 days.`
    : "Send this link to the user so they can set a password and sign in. It expires in 7 days.";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description ?? defaultDescription}</DialogDescription>
        </DialogHeader>
        <div className="flex items-center gap-2">
          <Input
            readOnly
            value={url ?? ""}
            onFocus={(e) => e.currentTarget.select()}
            className="font-mono text-xs"
          />
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="shrink-0"
            disabled={!url}
            onClick={() => url && copyToClipboard(url)}
            aria-label="Copy invitation link"
          >
            {isCopied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
