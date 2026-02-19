import { useState, useCallback } from "react";
import { schemas } from "@/lib/api/generated";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    SignatureVerification,
    validateSignatureVerification,
    type SignatureVerificationData,
} from "./SignatureVerification";
import { useSubmitApprovalResponse } from "@/hooks/useSubmitApprovalResponse";
import { useRetrieveUsers } from "@/hooks/useRetrieveUsers";

interface ApprovalResponsePayload {
    decision: 'APPROVED' | 'REJECTED' | 'DELEGATED';
    comments?: string;
    signature_data?: string;
    signature_meaning?: string;
    password?: string;
    delegate_to?: number;
}
import { Loader2, CheckCircle2, XCircle, UserPlus } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface ApprovalResponseModalProps {
    approvalRequestId: string;
    contentTitle: string;
    contentType: string;
    isOpen: boolean;
    onClose: () => void;
    onSuccess?: () => void;
}

export function ApprovalResponseModal({
    approvalRequestId,
    contentTitle,
    contentType,
    isOpen,
    onClose,
    onSuccess,
}: ApprovalResponseModalProps) {
    const [decision, setDecision] = useState<'APPROVED' | 'REJECTED' | 'DELEGATED'>('APPROVED');
    const [comments, setComments] = useState("");
    const [delegateTo, setDelegateTo] = useState<number | null>(null);
    const [signatureVerification, setSignatureVerification] = useState<SignatureVerificationData>({
        signature_data: "",
        password: "",
        confirmed: false,
    });
    const [error, setError] = useState<string | null>(null);

    const { mutate: submitResponse, isPending } = useSubmitApprovalResponse(approvalRequestId);

    // Fetch users for delegation dropdown
    const { data: usersData } = useRetrieveUsers(
        { limit: 100, is_active: true },
        { enabled: decision === 'DELEGATED' }
    );
    const users = usersData?.results || [];

    const handleSignatureChange = useCallback((data: SignatureVerificationData) => {
        setSignatureVerification(data);
    }, []);

    const handleSubmit = () => {
        setError(null);

        // Validation
        if (decision === 'APPROVED') {
            const validationError = validateSignatureVerification(signatureVerification);
            if (validationError) {
                setError(validationError);
                return;
            }
        }

        if (decision === 'REJECTED' && !comments) {
            setError("Comments are required when rejecting");
            return;
        }

        if (decision === 'DELEGATED' && !delegateTo) {
            setError("Please select a user to delegate to");
            return;
        }

        const payload: ApprovalResponsePayload = {
            decision,
            comments: comments || undefined,
            signature_data: decision === 'APPROVED' ? signatureVerification.signature_data : undefined,
            signature_meaning: decision === 'APPROVED' ? "I approve this item and confirm it meets all requirements" : undefined,
            password: decision === 'APPROVED' ? signatureVerification.password : undefined,
            delegate_to: decision === 'DELEGATED' ? delegateTo ?? undefined : undefined,
        };

        submitResponse(payload, {
            onSuccess: () => {
                handleClose();
                onSuccess?.();
            },
            onError: (err: { response?: { data?: Record<string, any> }; message?: string }) => {
                const apiError = err?.response?.data;
                let message = "Failed to submit response";

                if (apiError?.non_field_errors?.[0]) {
                    message = apiError.non_field_errors[0];
                } else if (apiError?.password?.[0]) {
                    message = "Invalid password";
                } else if (apiError?.detail) {
                    message = apiError.detail;
                } else if (err?.message) {
                    message = err.message;
                }

                setError(message);
            },
        });
    };

    const handleClose = () => {
        setDecision('APPROVED');
        setComments("");
        setDelegateTo(null);
        setSignatureVerification({ signature_data: "", password: "", confirmed: false });
        setError(null);
        onClose();
    };

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Submit Approval Response</DialogTitle>
                    <DialogDescription>
                        {contentType} for <span className="font-medium">{contentTitle}</span>
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-6 py-4">
                    {/* Decision Selection */}
                    <div className="space-y-3">
                        <Label>Decision</Label>
                        <RadioGroup
                            value={decision}
                            onValueChange={(v) => setDecision(v as typeof decision)}
                            className="flex gap-4"
                        >
                            <div className="flex items-center space-x-2">
                                <RadioGroupItem value={schemas.DecisionEnum.enum.APPROVED} id="approved" />
                                <Label htmlFor="approved" className="flex items-center gap-1 cursor-pointer">
                                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                                    Approve
                                </Label>
                            </div>
                            <div className="flex items-center space-x-2">
                                <RadioGroupItem value={schemas.DecisionEnum.enum.REJECTED} id="rejected" />
                                <Label htmlFor="rejected" className="flex items-center gap-1 cursor-pointer">
                                    <XCircle className="h-4 w-4 text-red-600" />
                                    Reject
                                </Label>
                            </div>
                            <div className="flex items-center space-x-2">
                                <RadioGroupItem value={schemas.DecisionEnum.enum.DELEGATED} id="delegated" />
                                <Label htmlFor="delegated" className="flex items-center gap-1 cursor-pointer">
                                    <UserPlus className="h-4 w-4 text-blue-600" />
                                    Delegate
                                </Label>
                            </div>
                        </RadioGroup>
                    </div>

                    {/* Comments */}
                    <div className="space-y-2">
                        <Label htmlFor="comments">
                            Comments {decision === 'REJECTED' && <span className="text-destructive">*</span>}
                        </Label>
                        <Textarea
                            id="comments"
                            value={comments}
                            onChange={(e) => setComments(e.target.value)}
                            placeholder={
                                decision === 'REJECTED'
                                    ? "Please explain why you are rejecting..."
                                    : "Optional comments..."
                            }
                            rows={3}
                        />
                    </div>

                    {/* Signature Verification (only for approve) */}
                    {decision === 'APPROVED' && (
                        <SignatureVerification
                            onChange={handleSignatureChange}
                            confirmationText="I confirm this is my signature and I am authorized to approve this item."
                            passwordHelpText="Your password is required to verify your identity for this approval."
                        />
                    )}

                    {/* Delegate user selector */}
                    {decision === 'DELEGATED' && (
                        <div className="space-y-2">
                            <Label htmlFor="delegate-to">
                                Delegate To <span className="text-destructive">*</span>
                            </Label>
                            <Select
                                value={delegateTo?.toString() || ""}
                                onValueChange={(val) => setDelegateTo(val ? parseInt(val) : null)}
                            >
                                <SelectTrigger id="delegate-to">
                                    <SelectValue placeholder="Select a user..." />
                                </SelectTrigger>
                                <SelectContent>
                                    {users.map((user: { id: number; first_name?: string | null; last_name?: string | null; username: string }) => (
                                        <SelectItem key={user.id} value={user.id.toString()}>
                                            {user.first_name && user.last_name
                                                ? `${user.first_name} ${user.last_name} (${user.username})`
                                                : user.username}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <p className="text-sm text-muted-foreground">
                                The selected user will receive this approval request and become the new approver.
                            </p>
                        </div>
                    )}

                    {/* Error message */}
                    {error && (
                        <Alert variant="destructive">
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={handleClose} disabled={isPending}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSubmit}
                        disabled={isPending}
                        variant={decision === 'REJECTED' ? 'destructive' : 'default'}
                    >
                        {isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                        {decision === 'APPROVED' && "Submit Approval"}
                        {decision === 'REJECTED' && "Submit Rejection"}
                        {decision === 'DELEGATED' && "Delegate Approval"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
