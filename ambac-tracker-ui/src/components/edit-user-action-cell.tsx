import {
    AlertDialog,
    AlertDialogTrigger,
    AlertDialogContent,
    AlertDialogHeader,
    AlertDialogFooter,
    AlertDialogTitle,
    AlertDialogDescription,
    AlertDialogCancel,
    AlertDialogAction
} from "@/components/ui/alert-dialog.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Pencil, Delete, Mail } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useDeleteUser } from "@/hooks/useDeleteUser.ts";
import { useSendUserInvitation } from "@/hooks/useSendUserInvitation.ts";
import { InviteLinkDialog } from "@/components/users/InviteLinkDialog.tsx";
import { toast } from "sonner";
import { apiErrorBody, apiErrorField } from "@/lib/api/describeApiError";

type Props = {
    userId: number;
};

export function EditUserActionsCell({ userId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const [inviteUrl, setInviteUrl] = useState<string | null>(null);
    const [inviteOpen, setInviteOpen] = useState(false);
    const deleteUser = useDeleteUser();
    const sendInvitation = useSendUserInvitation();

    const handleEditUser = () => {
        navigate({
            to: "/admin/users/$id/edit",
            params: { id: String(userId) },
        });
    };

    const handleDelete = () => {
        deleteUser.mutate(userId, {
            onSuccess: () => {
                setOpen(false);
                toast.success("Access removed. Their records are kept.");
            },
            onError: (error) => {
                console.error("Failed to delete user:", error);
                toast.error("Couldn't remove the user's access.");
            },
        });
    };

    const handleSendInvitation = () => {
        sendInvitation.mutate(userId, {
            onSuccess: (data) => {
                if (data?.invitation_url) {
                    setInviteUrl(data.invitation_url);
                    setInviteOpen(true);
                }
                toast.success(`Invitation created for user #${userId}.`);
            },
            onError: (error) => {
                // A pending invitation already exists — surface its live link
                // (email may be off) instead of dead-ending on an error toast.
                const invitationUrl = apiErrorField(apiErrorBody(error), "invitation_url");
                if (invitationUrl) {
                    setInviteUrl(invitationUrl);
                    setInviteOpen(true);
                    toast.info("User already has a pending invitation — here's the link.");
                    return;
                }
                console.error("Failed to send invitation:", error);
                toast.error("Failed to send invitation.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditUser}
                title="Edit User"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <Button
                variant="ghost"
                size="icon"
                onClick={handleSendInvitation}
                title="Send Invitation"
                disabled={sendInvitation.isPending}
            >
                <Mail className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Remove from this organisation"
                    >
                        <Delete className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Remove this user&rsquo;s access?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            They lose access to this organisation. Their account, and everything they
                            recorded here — training, approvals, signatures — is kept. Reactivate them
                            from User Management to restore access.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDelete}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            Remove access
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
            <InviteLinkDialog
                open={inviteOpen}
                onOpenChange={setInviteOpen}
                url={inviteUrl}
            />
        </div>
    );
}