import { useState } from "react"
import { schemas } from "@/lib/api/generated"
import { asUserInfo } from "@/lib/extended-types"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/ui/status-badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, Pencil } from "lucide-react"
import { useCreateRcaRecord } from "@/hooks/useCreateRcaRecord"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

type CapaRcaTabProps = {
    capa: any
}

type RcaFormData = {
    rca_method: "FIVE_WHYS" | "FISHBONE"
    problem_description: string
    root_cause_summary: string
    // 5 Whys fields
    why_1_question: string
    why_1_answer: string
    why_2_question: string
    why_2_answer: string
    why_3_question: string
    why_3_answer: string
    why_4_question: string
    why_4_answer: string
    why_5_question: string
    why_5_answer: string
    identified_root_cause: string
    // Fishbone fields
    fishbone_problem_statement: string
    man_causes: string
    machine_causes: string
    material_causes: string
    method_causes: string
    measurement_causes: string
    environment_causes: string
    fishbone_root_cause: string
}

const initialFormData: RcaFormData = {
    rca_method: "FIVE_WHYS",
    problem_description: "",
    root_cause_summary: "",
    why_1_question: "",
    why_1_answer: "",
    why_2_question: "",
    why_2_answer: "",
    why_3_question: "",
    why_3_answer: "",
    why_4_question: "",
    why_4_answer: "",
    why_5_question: "",
    why_5_answer: "",
    identified_root_cause: "",
    fishbone_problem_statement: "",
    man_causes: "",
    machine_causes: "",
    material_causes: "",
    method_causes: "",
    measurement_causes: "",
    environment_causes: "",
    fishbone_root_cause: "",
}

export function CapaRcaTab({ capa }: CapaRcaTabProps) {
    const [dialogOpen, setDialogOpen] = useState(false)
    const [formData, setFormData] = useState<RcaFormData>(initialFormData)
    const createRcaMutation = useCreateRcaRecord()
    const queryClient = useQueryClient()

    if (!capa) {
        return null
    }

    const rcaRecords = capa.rca_records || []

    const handleOpenDialog = () => {
        setFormData(initialFormData)
        setDialogOpen(true)
    }

    const handleSubmit = async () => {
        try {
            const payload: any = {
                capa: capa?.id,
                rca_method: formData.rca_method,
                problem_description: formData.problem_description,
                root_cause_summary: formData.root_cause_summary,
            }

            if (formData.rca_method === "FIVE_WHYS") {
                payload.five_whys_data = {
                    why_1_question: formData.why_1_question,
                    why_1_answer: formData.why_1_answer,
                    why_2_question: formData.why_2_question,
                    why_2_answer: formData.why_2_answer,
                    why_3_question: formData.why_3_question,
                    why_3_answer: formData.why_3_answer,
                    why_4_question: formData.why_4_question,
                    why_4_answer: formData.why_4_answer,
                    why_5_question: formData.why_5_question,
                    why_5_answer: formData.why_5_answer,
                    identified_root_cause: formData.identified_root_cause,
                }
            } else {
                payload.fishbone_data = {
                    problem_statement: formData.fishbone_problem_statement,
                    man_causes: formData.man_causes,
                    machine_causes: formData.machine_causes,
                    material_causes: formData.material_causes,
                    method_causes: formData.method_causes,
                    measurement_causes: formData.measurement_causes,
                    environment_causes: formData.environment_causes,
                    identified_root_cause: formData.fishbone_root_cause,
                }
            }

            await createRcaMutation.mutateAsync(payload)
            queryClient.invalidateQueries({ queryKey: ["capa", capa?.id] })
            toast.success("RCA record created successfully")
            setDialogOpen(false)
        } catch (error) {
            toast.error("Failed to create RCA record")
            console.error(error)
        }
    }

    const updateField = (field: keyof RcaFormData, value: string) => {
        setFormData((prev) => ({ ...prev, [field]: value }))
    }

    const RcaDialog = () => (
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Add Root Cause Analysis</DialogTitle>
                    <DialogDescription>
                        Document the root cause analysis for this CAPA
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-6 py-4">
                    {/* RCA Method Selection */}
                    <div className="space-y-2">
                        <Label>RCA Method</Label>
                        <Select
                            value={formData.rca_method}
                            onValueChange={(v) => updateField("rca_method", v as "FIVE_WHYS" | "FISHBONE")}
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value={schemas.RcaMethodEnum.enum.FIVE_WHYS}>5 Whys</SelectItem>
                                <SelectItem value={schemas.RcaMethodEnum.enum.FISHBONE}>Fishbone (6M)</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Problem Description */}
                    <div className="space-y-2">
                        <Label>Problem Description</Label>
                        <Textarea
                            value={formData.problem_description}
                            onChange={(e) => updateField("problem_description", e.target.value)}
                            placeholder="Describe the problem being analyzed..."
                            rows={3}
                        />
                    </div>

                    {/* 5 Whys Form */}
                    {formData.rca_method === "FIVE_WHYS" && (
                        <div className="space-y-4 border rounded-lg p-4">
                            <h4 className="font-medium">5 Whys Analysis</h4>
                            {[1, 2, 3, 4, 5].map((num) => (
                                <div key={num} className="grid gap-4 sm:grid-cols-2">
                                    <div className="space-y-2">
                                        <Label>Why {num} - Question</Label>
                                        <Input
                                            value={formData[`why_${num}_question` as keyof RcaFormData] as string}
                                            onChange={(e) => updateField(`why_${num}_question` as keyof RcaFormData, e.target.value)}
                                            placeholder={`Why ${num}?`}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Why {num} - Answer</Label>
                                        <Input
                                            value={formData[`why_${num}_answer` as keyof RcaFormData] as string}
                                            onChange={(e) => updateField(`why_${num}_answer` as keyof RcaFormData, e.target.value)}
                                            placeholder="Answer..."
                                        />
                                    </div>
                                </div>
                            ))}
                            <div className="space-y-2">
                                <Label>Identified Root Cause</Label>
                                <Textarea
                                    value={formData.identified_root_cause}
                                    onChange={(e) => updateField("identified_root_cause", e.target.value)}
                                    placeholder="Based on the 5 Whys, the root cause is..."
                                    rows={2}
                                />
                            </div>
                        </div>
                    )}

                    {/* Fishbone Form */}
                    {formData.rca_method === "FISHBONE" && (
                        <div className="space-y-4 border rounded-lg p-4">
                            <h4 className="font-medium">Fishbone (6M) Analysis</h4>
                            <div className="space-y-2">
                                <Label>Problem Statement</Label>
                                <Input
                                    value={formData.fishbone_problem_statement}
                                    onChange={(e) => updateField("fishbone_problem_statement", e.target.value)}
                                    placeholder="State the problem (fish head)"
                                />
                            </div>
                            <div className="grid gap-4 sm:grid-cols-2">
                                <div className="space-y-2">
                                    <Label>Man (People) Causes</Label>
                                    <Textarea
                                        value={formData.man_causes}
                                        onChange={(e) => updateField("man_causes", e.target.value)}
                                        placeholder="One cause per line..."
                                        rows={2}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>Machine Causes</Label>
                                    <Textarea
                                        value={formData.machine_causes}
                                        onChange={(e) => updateField("machine_causes", e.target.value)}
                                        placeholder="One cause per line..."
                                        rows={2}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>Material Causes</Label>
                                    <Textarea
                                        value={formData.material_causes}
                                        onChange={(e) => updateField("material_causes", e.target.value)}
                                        placeholder="One cause per line..."
                                        rows={2}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>Method Causes</Label>
                                    <Textarea
                                        value={formData.method_causes}
                                        onChange={(e) => updateField("method_causes", e.target.value)}
                                        placeholder="One cause per line..."
                                        rows={2}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>Measurement Causes</Label>
                                    <Textarea
                                        value={formData.measurement_causes}
                                        onChange={(e) => updateField("measurement_causes", e.target.value)}
                                        placeholder="One cause per line..."
                                        rows={2}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>Environment Causes</Label>
                                    <Textarea
                                        value={formData.environment_causes}
                                        onChange={(e) => updateField("environment_causes", e.target.value)}
                                        placeholder="One cause per line..."
                                        rows={2}
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label>Identified Root Cause</Label>
                                <Textarea
                                    value={formData.fishbone_root_cause}
                                    onChange={(e) => updateField("fishbone_root_cause", e.target.value)}
                                    placeholder="Based on the fishbone analysis, the root cause is..."
                                    rows={2}
                                />
                            </div>
                        </div>
                    )}

                    {/* Root Cause Summary */}
                    <div className="space-y-2">
                        <Label>Root Cause Summary</Label>
                        <Textarea
                            value={formData.root_cause_summary}
                            onChange={(e) => updateField("root_cause_summary", e.target.value)}
                            placeholder="Summary of the root cause findings..."
                            rows={3}
                        />
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => setDialogOpen(false)}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={createRcaMutation.isPending}>
                        {createRcaMutation.isPending ? "Creating..." : "Create RCA"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )

    if (rcaRecords.length === 0) {
        return (
            <>
                <Card>
                    <CardHeader>
                        <CardTitle>Root Cause Analysis</CardTitle>
                        <CardDescription>No root cause analysis has been performed yet</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Button onClick={handleOpenDialog}>
                            <Plus className="h-4 w-4 mr-2" />
                            Start RCA
                        </Button>
                    </CardContent>
                </Card>
                <RcaDialog />
            </>
        )
    }

    return (
        <>
            <div className="space-y-4">
                <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold">Root Cause Analysis Records</h3>
                    <Button variant="outline" size="sm" onClick={handleOpenDialog}>
                        <Plus className="h-4 w-4 mr-2" />
                        Add RCA
                    </Button>
                </div>

                {rcaRecords.map((rca: any) => (
                    <Card key={rca.id}>
                        <CardHeader>
                            <div className="flex justify-between items-start">
                                <div>
                                    <CardTitle className="flex items-center gap-2">
                                        {rca.rca_method_display}
                                        <StatusBadge status={rca.root_cause_verification_status} label={rca.root_cause_verification_status_display} />
                                    </CardTitle>
                                    <CardDescription>
                                        {asUserInfo(rca.conducted_by_info)?.username && (
                                            <>Conducted by {asUserInfo(rca.conducted_by_info)?.username}</>
                                        )}
                                        {rca.conducted_date && (
                                            <> on {new Date(rca.conducted_date).toLocaleDateString()}</>
                                        )}
                                    </CardDescription>
                                </div>
                                <div className="flex gap-2">
                                    <Button variant="ghost" size="icon">
                                        <Pencil className="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {/* Problem Description */}
                            <div>
                                <h4 className="text-sm font-medium text-muted-foreground mb-2">Problem Description</h4>
                                <p className="whitespace-pre-wrap">{rca.problem_description}</p>
                            </div>

                            {/* 5 Whys Analysis */}
                            {rca.rca_method === "FIVE_WHYS" && rca.five_whys && (
                                <div>
                                    <h4 className="text-sm font-medium text-muted-foreground mb-3">5 Whys Analysis</h4>
                                    <div className="space-y-3 pl-4 border-l-2 border-muted">
                                        {[
                                            { label: "Why 1", question: rca.five_whys?.why_1_question, answer: rca.five_whys?.why_1_answer },
                                            { label: "Why 2", question: rca.five_whys?.why_2_question, answer: rca.five_whys?.why_2_answer },
                                            { label: "Why 3", question: rca.five_whys?.why_3_question, answer: rca.five_whys?.why_3_answer },
                                            { label: "Why 4", question: rca.five_whys?.why_4_question, answer: rca.five_whys?.why_4_answer },
                                            { label: "Why 5", question: rca.five_whys?.why_5_question, answer: rca.five_whys?.why_5_answer },
                                        ]
                                            .filter((w) => w.question || w.answer)
                                            .map((why, idx) => (
                                                <div key={idx} className="pl-4">
                                                    <span className="text-sm font-medium text-muted-foreground">
                                                        {why.label}:
                                                    </span>
                                                    {why.question && <p className="mt-1 font-medium">{why.question}</p>}
                                                    {why.answer && <p className="mt-1 text-muted-foreground">{why.answer}</p>}
                                                </div>
                                            ))}
                                    </div>
                                    {rca.five_whys?.identified_root_cause && (
                                        <div className="mt-4 p-3 bg-primary/10 rounded-lg">
                                            <h5 className="text-sm font-medium mb-1">Identified Root Cause</h5>
                                            <p>{rca.five_whys.identified_root_cause}</p>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Fishbone Analysis */}
                            {rca.rca_method === "FISHBONE" && rca.fishbone && (
                                <div>
                                    <h4 className="text-sm font-medium text-muted-foreground mb-3">Fishbone Analysis (6M)</h4>
                                    {rca.fishbone.problem_statement && (
                                        <div className="mb-4 p-3 bg-muted/50 rounded-lg">
                                            <h5 className="text-sm font-medium mb-1">Problem Statement</h5>
                                            <p>{rca.fishbone.problem_statement}</p>
                                        </div>
                                    )}
                                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                                        {[
                                            { label: "Man (People)", value: rca.fishbone?.man_causes },
                                            { label: "Machine", value: rca.fishbone?.machine_causes },
                                            { label: "Material", value: rca.fishbone?.material_causes },
                                            { label: "Method", value: rca.fishbone?.method_causes },
                                            { label: "Measurement", value: rca.fishbone?.measurement_causes },
                                            { label: "Environment (Mother Nature)", value: rca.fishbone?.environment_causes },
                                        ]
                                            .filter((f) => f.value && (Array.isArray(f.value) ? f.value.length > 0 : f.value))
                                            .map((field, idx) => (
                                                <Card key={idx} className="p-3">
                                                    <h5 className="text-sm font-medium">{field.label}</h5>
                                                    <ul className="text-sm text-muted-foreground mt-1 list-disc list-inside">
                                                        {(Array.isArray(field.value) ? field.value : [field.value]).map((cause: string, i: number) => (
                                                            <li key={i}>{cause}</li>
                                                        ))}
                                                    </ul>
                                                </Card>
                                            ))}
                                    </div>
                                    {rca.fishbone?.identified_root_cause && (
                                        <div className="mt-4 p-3 bg-primary/10 rounded-lg">
                                            <h5 className="text-sm font-medium mb-1">Identified Root Cause</h5>
                                            <p>{rca.fishbone.identified_root_cause}</p>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Root Causes */}
                            {rca.root_causes && rca.root_causes.length > 0 && (
                                <div>
                                    <h4 className="text-sm font-medium text-muted-foreground mb-3">Identified Root Causes</h4>
                                    <div className="space-y-2">
                                        {rca.root_causes.map((cause: any, idx: number) => (
                                            <div key={cause.id} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                                                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-medium">
                                                    {idx + 1}
                                                </span>
                                                <div className="flex-1">
                                                    <p>{cause.description}</p>
                                                    <div className="flex gap-2 mt-2">
                                                        <Badge variant="outline">{cause.category_display}</Badge>
                                                        {cause.role && (
                                                            <Badge variant="secondary">{cause.role_display}</Badge>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Root Cause Summary */}
                            {rca.root_cause_summary && (
                                <div>
                                    <h4 className="text-sm font-medium text-muted-foreground mb-2">Root Cause Summary</h4>
                                    <p className="whitespace-pre-wrap p-3 bg-muted/50 rounded-lg">
                                        {rca.root_cause_summary}
                                    </p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                ))}
            </div>
            <RcaDialog />
        </>
    )
}
