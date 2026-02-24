import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { CheckCircle, XCircle, AlertCircle, Loader2 } from "lucide-react";
import { useRequiredMeasurements, useBulkRecordMeasurements } from "@/hooks/useStepExecutionMeasurements";
import { toast } from "sonner";

type MeasurementRecordingFormProps = {
    stepExecutionId: string;
    /** Called when measurements are saved */
    onSave?: () => void;
    /** Show as compact inline form */
    compact?: boolean;
};

type MeasurementValue = {
    definitionId: string;
    value: string;
    stringValue: string;
};

function evaluateSpec(
    value: string,
    type: "NUMERIC" | "PASS_FAIL",
    nominal: number | null,
    upperTol: number | null,
    lowerTol: number | null
): "pass" | "fail" | "na" {
    if (type === "PASS_FAIL") {
        const upper = value.toUpperCase();
        if (upper === "PASS") return "pass";
        if (upper === "FAIL") return "fail";
        return "na";
    }

    if (type === "NUMERIC") {
        const numValue = parseFloat(value);
        if (isNaN(numValue)) return "na";
        if (nominal === null || upperTol === null || lowerTol === null) return "na";

        const lower = nominal - lowerTol;
        const upper = nominal + upperTol;

        if (numValue >= lower && numValue <= upper) return "pass";
        return "fail";
    }

    return "na";
}

export function MeasurementRecordingForm({
    stepExecutionId,
    onSave,
    compact = false
}: MeasurementRecordingFormProps) {
    const { data: requiredData, isLoading } = useRequiredMeasurements(stepExecutionId);
    const bulkRecordMutation = useBulkRecordMeasurements();

    const [values, setValues] = useState<Record<string, MeasurementValue>>({});

    // Initialize values from definitions
    const definitions = requiredData?.definitions ?? [];

    const handleValueChange = (defId: string, value: string, isStringValue = false) => {
        setValues(prev => ({
            ...prev,
            [defId]: {
                definitionId: defId,
                value: isStringValue ? "" : value,
                stringValue: isStringValue ? value : ""
            }
        }));
    };

    // Compute spec status for each measurement
    const specStatuses = useMemo(() => {
        const statuses: Record<string, "pass" | "fail" | "na" | "empty"> = {};

        for (const def of definitions) {
            const val = values[def.id];
            if (!val || (!val.value && !val.stringValue)) {
                statuses[def.id] = "empty";
            } else {
                const inputValue = def.type === "PASS_FAIL" ? val.stringValue : val.value;
                statuses[def.id] = evaluateSpec(
                    inputValue,
                    def.type,
                    def.nominal,
                    def.upper_tol,
                    def.lower_tol
                );
            }
        }

        return statuses;
    }, [definitions, values]);

    // Check if all required measurements have values
    const allRequiredFilled = useMemo(() => {
        return definitions
            .filter(d => d.required && !d.is_recorded)
            .every(d => {
                const val = values[d.id];
                return val && (val.value || val.stringValue);
            });
    }, [definitions, values]);

    const handleSave = async () => {
        const measurements = Object.values(values)
            .filter(v => v.value || v.stringValue)
            .map(v => ({
                measurement_definition: v.definitionId,
                value: v.value ? parseFloat(v.value) : undefined,
                string_value: v.stringValue || undefined
            }));

        if (measurements.length === 0) {
            toast.error("No measurements to save");
            return;
        }

        try {
            const result = await bulkRecordMutation.mutateAsync({
                step_execution: stepExecutionId,
                measurements
            });

            if (result.error_count > 0) {
                toast.warning(`Saved ${result.created_count} measurements with ${result.error_count} errors`);
            } else {
                toast.success(`Saved ${result.created_count} measurements`);
            }

            setValues({});
            onSave?.();
        } catch (error) {
            toast.error("Failed to save measurements");
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-4">
                <Loader2 className="h-6 w-6 animate-spin" />
            </div>
        );
    }

    if (!definitions.length) {
        return (
            <div className="text-sm text-muted-foreground p-4 text-center">
                No measurements defined for this step.
            </div>
        );
    }

    // Filter to only show unrecorded measurements
    const unrecordedDefinitions = definitions.filter(d => !d.is_recorded);

    if (unrecordedDefinitions.length === 0) {
        return (
            <div className="rounded-lg p-3 border bg-green-500/10 border-green-500/50">
                <div className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-600" />
                    <span className="text-sm font-medium">All measurements recorded</span>
                </div>
            </div>
        );
    }

    const getStatusIcon = (status: "pass" | "fail" | "na" | "empty") => {
        switch (status) {
            case "pass":
                return <CheckCircle className="h-4 w-4 text-green-600" />;
            case "fail":
                return <XCircle className="h-4 w-4 text-red-600" />;
            case "na":
                return <AlertCircle className="h-4 w-4 text-gray-400" />;
            default:
                return null;
        }
    };

    if (compact) {
        return (
            <div className="space-y-2">
                {unrecordedDefinitions.map(def => (
                    <div key={def.id} className="flex items-center gap-2">
                        <span className="text-sm font-medium w-32 truncate" title={def.label}>
                            {def.label}
                            {def.required && <span className="text-red-500">*</span>}
                        </span>

                        {def.type === "NUMERIC" ? (
                            <Input
                                type="number"
                                step="any"
                                placeholder={def.nominal ? `${def.nominal}` : "Value"}
                                value={values[def.id]?.value ?? ""}
                                onChange={(e) => handleValueChange(def.id, e.target.value)}
                                className="w-24"
                            />
                        ) : (
                            <Select
                                value={values[def.id]?.stringValue ?? ""}
                                onValueChange={(v) => handleValueChange(def.id, v, true)}
                            >
                                <SelectTrigger className="w-24">
                                    <SelectValue placeholder="Select" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="PASS">Pass</SelectItem>
                                    <SelectItem value="FAIL">Fail</SelectItem>
                                </SelectContent>
                            </Select>
                        )}

                        {def.unit && <span className="text-xs text-muted-foreground">{def.unit}</span>}
                        {getStatusIcon(specStatuses[def.id])}
                    </div>
                ))}

                <Button
                    size="sm"
                    onClick={handleSave}
                    disabled={!allRequiredFilled || bulkRecordMutation.isPending}
                >
                    {bulkRecordMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-1" />
                    ) : null}
                    Save Measurements
                </Button>
            </div>
        );
    }

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center justify-between">
                    <span>Measurements</span>
                    <Badge variant="outline">
                        {definitions.filter(d => d.is_recorded).length} / {definitions.length} recorded
                    </Badge>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {unrecordedDefinitions.map(def => (
                    <div key={def.id} className="border rounded-lg p-3 space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="font-medium">
                                {def.label}
                                {def.required && <span className="text-red-500 ml-1">*</span>}
                            </span>
                            <Badge variant={def.type === "NUMERIC" ? "default" : "secondary"}>
                                {def.type === "NUMERIC" ? "Numeric" : "Pass/Fail"}
                            </Badge>
                        </div>

                        {def.type === "NUMERIC" && def.nominal !== null && (
                            <div className="text-xs text-muted-foreground">
                                Target: {def.nominal} {def.unit}
                                {def.lower_tol !== null && def.upper_tol !== null && (
                                    <span className="ml-2">
                                        (Range: {def.nominal - def.lower_tol} - {def.nominal + def.upper_tol})
                                    </span>
                                )}
                            </div>
                        )}

                        <div className="flex items-center gap-2">
                            {def.type === "NUMERIC" ? (
                                <Input
                                    type="number"
                                    step="any"
                                    placeholder={def.nominal ? `${def.nominal}` : "Enter value"}
                                    value={values[def.id]?.value ?? ""}
                                    onChange={(e) => handleValueChange(def.id, e.target.value)}
                                    className="flex-1"
                                />
                            ) : (
                                <Select
                                    value={values[def.id]?.stringValue ?? ""}
                                    onValueChange={(v) => handleValueChange(def.id, v, true)}
                                >
                                    <SelectTrigger className="flex-1">
                                        <SelectValue placeholder="Select result" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="PASS">Pass</SelectItem>
                                        <SelectItem value="FAIL">Fail</SelectItem>
                                    </SelectContent>
                                </Select>
                            )}

                            {def.unit && (
                                <span className="text-sm text-muted-foreground min-w-[40px]">
                                    {def.unit}
                                </span>
                            )}

                            <div className="w-6">
                                {getStatusIcon(specStatuses[def.id])}
                            </div>
                        </div>

                        {specStatuses[def.id] === "fail" && (
                            <div className="text-xs text-red-600 flex items-center gap-1">
                                <XCircle className="h-3 w-3" />
                                Out of specification
                            </div>
                        )}
                    </div>
                ))}

                <Button
                    className="w-full"
                    onClick={handleSave}
                    disabled={!allRequiredFilled || bulkRecordMutation.isPending}
                >
                    {bulkRecordMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                        <CheckCircle className="h-4 w-4 mr-2" />
                    )}
                    Save All Measurements
                </Button>
            </CardContent>
        </Card>
    );
}
