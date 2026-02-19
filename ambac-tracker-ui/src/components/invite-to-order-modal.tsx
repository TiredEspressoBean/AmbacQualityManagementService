import { useState } from "react";
import { toast } from "sonner";
import { Loader2, Mail, UserPlus } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useInviteToOrder } from "@/hooks/useInviteToOrder";

interface InviteToOrderModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    orderId: string;
}

export function InviteToOrderModal({ open, onOpenChange, orderId }: InviteToOrderModalProps) {
    const [email, setEmail] = useState("");
    const inviteMutation = useInviteToOrder();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!email.trim()) {
            toast.error("Please enter an email address");
            return;
        }

        // Basic email validation
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            toast.error("Please enter a valid email address");
            return;
        }

        inviteMutation.mutate(
            { orderId, email },
            {
                onSuccess: () => {
                    toast.success(`Invitation sent to ${email}`);
                    setEmail("");
                    onOpenChange(false);
                },
                onError: (error: any) => {
                    console.error("Failed to send invitation:", error);
                    const detail = error?.detail || "Failed to send invitation. Please try again.";
                    toast.error(detail);
                },
            }
        );
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <UserPlus className="h-5 w-5" />
                        Invite to Order
                    </DialogTitle>
                    <DialogDescription>
                        Send an invitation to view this order. They will have read-only access.
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit}>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="email">Email address</Label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="customer@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="pl-10"
                                    disabled={inviteMutation.isPending}
                                    autoFocus
                                />
                            </div>
                        </div>
                    </div>

                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={inviteMutation.isPending}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={inviteMutation.isPending}>
                            {inviteMutation.isPending ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Sending...
                                </>
                            ) : (
                                <>
                                    <Mail className="h-4 w-4 mr-2" />
                                    Send Invite
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
