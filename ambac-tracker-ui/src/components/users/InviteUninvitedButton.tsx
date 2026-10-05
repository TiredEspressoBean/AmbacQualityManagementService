import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Send } from "lucide-react";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
    AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

/**
 * Go-live for staff a migration workbook loaded without invitations: one click invites
 * everyone never invited and never signed in. Hidden when there's nobody to invite; a
 * user whose access was removed is never included.
 */
export function InviteUninvitedButton() {
    const queryClient = useQueryClient();
    const { data } = useQuery({
        queryKey: ["users", "uninvited"],
        queryFn: () => api.api_User_uninvited_retrieve(),
    });
    const invite = useMutation({
        mutationFn: () => api.api_User_invite_uninvited_create(undefined, {
            headers: { "X-CSRFToken": getCookie("csrftoken") },
        }),
        onSuccess: (r) => {
            toast.success(`Invited ${r.invited} user${r.invited === 1 ? "" : "s"}.`);
            queryClient.invalidateQueries({ queryKey: ["users", "uninvited"] });
            queryClient.invalidateQueries({ predicate: (q) => String(q.queryKey[0]).toLowerCase().includes("user") });
        },
        onError: () => toast.error("Couldn't send the invitations."),
    });

    const count = data?.count ?? 0;
    if (count === 0) return null;
    const shown = (data?.emails ?? []).slice(0, 8);

    return (
        <AlertDialog>
            <AlertDialogTrigger asChild>
                <Button variant="outline" disabled={invite.isPending}>
                    <Send className="h-4 w-4 mr-1.5" />
                    Invite {count} not yet invited
                </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Invite {count} user{count === 1 ? "" : "s"}?</AlertDialogTitle>
                    <AlertDialogDescription>
                        Everyone who has never been invited or signed in gets an invitation email,
                        good for 7 days. Users whose access was removed aren&rsquo;t included.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <ul className="max-h-40 space-y-0.5 overflow-y-auto text-sm text-muted-foreground">
                    {shown.map((e) => <li key={e}>{e}</li>)}
                    {count > shown.length && <li>…and {count - shown.length} more</li>}
                </ul>
                <AlertDialogFooter>
                    <AlertDialogCancel>Not yet</AlertDialogCancel>
                    <AlertDialogAction onClick={() => invite.mutate()}>Send invitations</AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
