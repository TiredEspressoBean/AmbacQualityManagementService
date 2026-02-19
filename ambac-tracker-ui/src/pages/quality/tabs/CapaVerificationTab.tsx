import { useState } from "react"
import { schemas } from "@/lib/api/generated"
import { asUserInfo } from "@/lib/extended-types"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { StatusBadge, getStatusIcon } from "@/components/ui/status-badge"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, CheckCircle, User, Calendar, Pencil } from "lucide-react"
import { useCreateCapaVerification } from "@/hooks/useCreateCapaVerification"
import { useUpdateCapaVerification } from "@/hooks/useUpdateCapaVerification"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

type CapaVerificationTabProps = {
    capa: any
}


const effectivenessLabels: Record<string, string> = {
    CONFIRMED: "Effective - Confirmed",
    NOT_EFFECTIVE: "Not Effective",
    INCONCLUSIVE: "Inconclusive",
}

type VerificationFormData = {
    verification_method: string
    verification_criteria: string
    verification_date: string
    effectiveness_result: "CONFIRMED" | "NOT_EFFECTIVE" | "INCONCLUSIVE" | ""
    verification_notes: string
}

const initialFormData: VerificationFormData = {
    verification_method: "",
    verification_criteria: "",
    verification_date: "",
    effectiveness_result: "",
    verification_notes: "",
}

export function CapaVerificationTab({ capa }: CapaVerificationTabProps) {
    const [dialogOpen, setDialogOpen] = useState(false)
    const [editingVerification, setEditingVerification] = useState<any>(null)
    const [formData, setFormData] = useState<VerificationFormData>(initialFormData)
    const [completeDialogOpen, setCompleteDialogOpen] = useState(false)
    const [completingVerification, setCompletingVerification] = useState<any>(null)

    const createVerificationMutation = useCreateCapaVerification()
    const updateVerificationMutation = useUpdateCapaVerification()
    const queryClient = useQueryClient()

    if (!capa) {
        return null
    }

    const verifications = capa.verifications || []

    const handleOpenDialog = (verification?: any) => {
        if (verification) {
            setEditingVerification(verification)
            setFormData({
                verification_method: verification.verification_method || "",
                verification_criteria: verification.verification_criteria || "",
                verification_date: verification.verification_date || "",
                effectiveness_result: verification.effectiveness_result || "",
                verification_notes: verification.verification_notes || "",
            })
        } else {
            setEditingVerification(null)
            setFormData(initialFormData)
        }
        setDialogOpen(true)
    }

    const handleSubmit = async () => {
        try {
            const payload: any = {
                capa: capa?.id,
                verification_method: formData.verification_method,
                verification_criteria: formData.verification_criteria,
                verification_date: formData.verification_date || null,
                effectiveness_result: formData.effectiveness_result || null,
                verification_notes: formData.verification_notes || null,
            }

            if (editingVerification) {
                await updateVerificationMutation.mutateAsync({ id: editingVerification.id, data: payload })
                toast.success("Verification updated successfully")
            } else {
                await createVerificationMutation.mutateAsync(payload)
                toast.success("Verification record created successfully")
            }
            queryClient.invalidateQueries({ queryKey: ["capa", capa?.id] })
            setDialogOpen(false)
        } catch (error) {
            toast.error(editingVerification ? "Failed to update verification" : "Failed to create verification")
            console.error(error)
        }
    }

    const handleOpenCompleteDialog = (verification: any) => {
        setCompletingVerification(verification)
        setFormData({
            verification_method: verification.verification_method || "",
            verification_criteria: verification.verification_criteria || "",
            verification_date: new Date().toISOString().split('T')[0],
            effectiveness_result: "",
            verification_notes: "",
        })
        setCompleteDialogOpen(true)
    }

    const handleCompleteVerification = async () => {
        if (!completingVerification || !formData.effectiveness_result) {
            toast.error("Please select an effectiveness result")
            return
        }
        try {
            await updateVerificationMutation.mutateAsync({
                id: completingVerification.id,
                data: {
                    capa: capa?.id,
                    verification_method: completingVerification.verification_method,
                    verification_criteria: completingVerification.verification_criteria,
                    verification_date: formData.verification_date,
                    effectiveness_result: formData.effectiveness_result,
                    verification_notes: formData.verification_notes,
                }
            })
            queryClient.invalidateQueries({ queryKey: ["capa", capa?.id] })
            toast.success("Verification completed successfully")
            setCompleteDialogOpen(false)
        } catch (error) {
            toast.error("Failed to complete verification")
            console.error(error)
        }
    }

    const updateField = (field: keyof VerificationFormData, value: string) => {
        setFormData((prev) => ({ ...prev, [field]: value }))
    }

    const VerificationDialog = () => (
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>{editingVerification ? "Edit Verification" : "Add Verification Plan"}</DialogTitle>
                    <DialogDescription>
                        {editingVerification
                            ? "Update verification details"
                            : "Define how you will verify the effectiveness of corrective actions"
                        }
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label>Verification Method *</Label>
                        <Textarea
                            value={formData.verification_method}
                            onChange={(e) => updateField("verification_method", e.target.value)}
                            placeholder="How will effectiveness be verified? (e.g., process audit, data review, etc.)"
                            rows={2}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label>Success Criteria *</Label>
                        <Textarea
                            value={formData.verification_criteria}
                            onChange={(e) => updateField("verification_criteria", e.target.value)}
                            placeholder="What defines success? (e.g., zero defects over 30 days, process capability > 1.33)"
                            rows={3}
                        />
                    </div>

                    {editingVerification && (
                        <>
                            <div className="space-y-2">
                                <Label>Verification Date</Label>
                                <Input
                                    type="date"
                                    value={formData.verification_date}
                                    onChange={(e) => updateField("verification_date", e.target.value)}
                                />
                            </div>

                            <div className="space-y-2">
                                <Label>Effectiveness Result</Label>
                                <Select
                                    value={formData.effectiveness_result}
                                    onValueChange={(v) => updateField("effectiveness_result", v)}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select result..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {schemas.EffectivenessResultEnum.options.map((result) => (
                                            <SelectItem key={result} value={result}>
                                                {effectivenessLabels[result] ?? result}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label>Verification Notes</Label>
                                <Textarea
                                    value={formData.verification_notes}
                                    onChange={(e) => updateField("verification_notes", e.target.value)}
                                    placeholder="Notes about the verification process and findings..."
                                    rows={3}
                                />
                            </div>
                        </>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => setDialogOpen(false)}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSubmit}
                        disabled={
                            !formData.verification_method ||
                            !formData.verification_criteria ||
                            createVerificationMutation.isPending ||
                            updateVerificationMutation.isPending
                        }
                    >
                        {createVerificationMutation.isPending || updateVerificationMutation.isPending
                            ? "Saving..."
                            : editingVerification ? "Update" : "Create"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )

    const CompleteVerificationDialog = () => (
        <Dialog open={completeDialogOpen} onOpenChange={setCompleteDialogOpen}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>Complete Verification</DialogTitle>
                    <DialogDescription>
                        Record the results of the effectiveness verification
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="p-3 bg-muted/50 rounded-lg space-y-2">
                        <p className="text-sm font-medium">Verification Method:</p>
                        <p className="text-sm text-muted-foreground">{completingVerification?.verification_method}</p>
                        <p className="text-sm font-medium mt-2">Success Criteria:</p>
                        <p className="text-sm text-muted-foreground">{completingVerification?.verification_criteria}</p>
                    </div>

                    <div className="space-y-2">
                        <Label>Verification Date</Label>
                        <Input
                            type="date"
                            value={formData.verification_date}
                            onChange={(e) => updateField("verification_date", e.target.value)}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label>Effectiveness Result *</Label>
                        <Select
                            value={formData.effectiveness_result}
                            onValueChange={(v) => updateField("effectiveness_result", v)}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Select result..." />
                            </SelectTrigger>
                            <SelectContent>
                                {schemas.EffectivenessResultEnum.options.map((result) => {
                                    const Icon = getStatusIcon(result)
                                    const iconColor = result === "CONFIRMED" ? "text-green-600"
                                        : result === "NOT_EFFECTIVE" ? "text-red-600"
                                        : "text-yellow-600"
                                    return (
                                        <SelectItem key={result} value={result}>
                                            <div className="flex items-center gap-2">
                                                <Icon className={`h-4 w-4 ${iconColor}`} />
                                                {effectivenessLabels[result] ?? result}
                                            </div>
                                        </SelectItem>
                                    )
                                })}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <Label>Verification Notes</Label>
                        <Textarea
                            value={formData.verification_notes}
                            onChange={(e) => updateField("verification_notes", e.target.value)}
                            placeholder="Document the verification findings, evidence reviewed, and conclusions..."
                            rows={4}
                        />
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => setCompleteDialogOpen(false)}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleCompleteVerification}
                        disabled={!formData.effectiveness_result || updateVerificationMutation.isPending}
                    >
                        {updateVerificationMutation.isPending ? "Saving..." : "Complete Verification"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )

    return (
        <>
            <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle>Effectiveness Verification</CardTitle>
                        <CardDescription>
                            Verify that corrective/preventive actions have been effective
                        </CardDescription>
                    </div>
                    <Button onClick={() => handleOpenDialog()}>
                        <Plus className="h-4 w-4 mr-2" />
                        Add Verification
                    </Button>
                </CardHeader>
                <CardContent>
                    {verifications.length === 0 ? (
                        <div className="text-center py-8">
                            <p className="text-muted-foreground mb-4">
                                No verifications have been recorded yet.
                            </p>
                            <p className="text-sm text-muted-foreground">
                                Add a verification plan to define how you will measure effectiveness of the corrective actions.
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {verifications.map((verification: any) => {
                                const verifiedByInfo = asUserInfo(verification.verified_by_info)

                                return (
                                    <div key={verification.id} className="p-4 rounded-lg border space-y-4">
                                        <div className="flex items-start justify-between">
                                            <div className="space-y-1">
                                                <h4 className="font-medium">Verification Method</h4>
                                                <p>{verification.verification_method}</p>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <StatusBadge
                                                    status={verification.effectiveness_result || "PENDING"}
                                                    label={verification.effectiveness_result_display}
                                                />
                                                <Button variant="ghost" size="icon" onClick={() => handleOpenDialog(verification)}>
                                                    <Pencil className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </div>

                                        <div>
                                            <h4 className="font-medium text-sm text-muted-foreground mb-1">
                                                Success Criteria
                                            </h4>
                                            <p className="text-sm">{verification.verification_criteria}</p>
                                        </div>

                                        {verification.verification_notes && (
                                            <div>
                                                <h4 className="font-medium text-sm text-muted-foreground mb-1">
                                                    Verification Notes
                                                </h4>
                                                <p className="text-sm whitespace-pre-wrap p-2 bg-muted/50 rounded">
                                                    {verification.verification_notes}
                                                </p>
                                            </div>
                                        )}

                                        <div className="flex items-center justify-between pt-2 border-t">
                                            <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                                {verifiedByInfo?.username && (
                                                    <div className="flex items-center gap-1">
                                                        <User className="h-3 w-3" />
                                                        Verified by {verifiedByInfo.username}
                                                    </div>
                                                )}
                                                {verification.verification_date && (
                                                    <div className="flex items-center gap-1">
                                                        <Calendar className="h-3 w-3" />
                                                        {new Date(verification.verification_date).toLocaleDateString()}
                                                    </div>
                                                )}
                                                {verification.self_verified && (
                                                    <Badge variant="secondary" className="text-xs">
                                                        Self-verified
                                                    </Badge>
                                                )}
                                            </div>
                                            {!verification.effectiveness_result && (
                                                <Button size="sm" onClick={() => handleOpenCompleteDialog(verification)}>
                                                    <CheckCircle className="h-4 w-4 mr-2" />
                                                    Complete Verification
                                                </Button>
                                            )}
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    )}

                    {/* Self-verification info */}
                    {capa?.allow_self_verification && (
                        <div className="mt-4 p-3 bg-muted/50 rounded-lg">
                            <p className="text-sm text-muted-foreground">
                                <strong>Note:</strong> Self-verification is enabled for this CAPA.
                                The initiator or assignee may verify their own work with justification.
                            </p>
                        </div>
                    )}
                </CardContent>
            </Card>
            <VerificationDialog />
            <CompleteVerificationDialog />
        </>
    )
}
