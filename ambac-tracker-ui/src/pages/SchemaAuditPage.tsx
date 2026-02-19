import { useAllSchemaMetadata, MODELS_WITH_METADATA } from "@/hooks/useSchemaMetadata";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Copy, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { toast } from "sonner";

interface ModelIssue {
    model: string;
    type: "warning" | "info";
    message: string;
    details?: string;
}

export function SchemaAuditPage() {
    const { data: allMetadata, isLoading, error } = useAllSchemaMetadata();

    // Analyze metadata and find issues
    const analyzeMetadata = (): { issues: ModelIssue[]; healthy: string[] } => {
        if (!allMetadata) return { issues: [], healthy: [] };

        const issues: ModelIssue[] = [];
        const healthy: string[] = [];

        for (const model of MODELS_WITH_METADATA) {
            const metadata = allMetadata[model];
            const modelIssues: ModelIssue[] = [];

            if (!metadata || metadata.error) {
                modelIssues.push({
                    model,
                    type: "warning",
                    message: "Failed to load metadata",
                    details: metadata?.error,
                });
                continue;
            }

            const orderingFields = metadata.ordering_fields || [];
            const filterFields = metadata.filterset_fields || [];
            const searchFields = metadata.search_fields || [];
            const filters = metadata.filters || {};

            // Check for models with no sorting
            if (orderingFields.length === 0) {
                modelIssues.push({
                    model,
                    type: "warning",
                    message: "No sortable fields configured",
                });
            }

            // Check for models with no search
            if (searchFields.length === 0) {
                modelIssues.push({
                    model,
                    type: "info",
                    message: "No search fields configured",
                });
            }

            // Check for choice filters not being used (high value filters)
            const unusedChoiceFilters = Object.entries(filters)
                .filter(([_, info]: [string, any]) =>
                    info.type === 'choice' && info.choices?.length > 0
                )
                .map(([name, info]: [string, any]) => ({
                    name,
                    choices: info.choices.map((c: any) => c.label).join(", ")
                }));

            // This is actually info, not a problem - choice filters ARE available
            // The issue would be if the UI isn't rendering them, but ModelEditorPage does this automatically

            // Check for foreignkey filters (potential for dropdowns)
            const fkFilters = Object.entries(filters)
                .filter(([_, info]: [string, any]) => info.type === 'foreignkey')
                .map(([name]) => name);

            if (modelIssues.length > 0) {
                issues.push(...modelIssues);
            } else {
                healthy.push(model);
            }
        }

        return { issues, healthy };
    };

    const copyIssuesReport = async () => {
        const { issues, healthy } = analyzeMetadata();

        const lines = [
            "# Schema Audit Report",
            `Generated: ${new Date().toISOString()}`,
            "",
        ];

        if (issues.length === 0) {
            lines.push("All models are healthy.");
        } else {
            lines.push(`## Issues (${issues.length})`, "");
            for (const issue of issues) {
                lines.push(`- **${issue.model}**: ${issue.message}${issue.details ? ` - ${issue.details}` : ""}`);
            }
        }

        lines.push("", `## Healthy Models (${healthy.length})`, "");
        lines.push(healthy.join(", "));

        await navigator.clipboard.writeText(lines.join("\n"));
        toast.success("Copied audit report");
    };

    if (isLoading) {
        return (
            <div className="p-6 space-y-4">
                <h1 className="text-2xl font-bold">Schema Audit</h1>
                <Skeleton className="h-32 w-full" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
                <h1 className="text-2xl font-bold text-red-600">Error loading metadata</h1>
                <p>{error instanceof Error ? error.message : "Unknown error"}</p>
            </div>
        );
    }

    const { issues, healthy } = analyzeMetadata();
    const warnings = issues.filter(i => i.type === "warning");
    const infos = issues.filter(i => i.type === "info");

    return (
        <div className="p-6 space-y-6 max-w-4xl">
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Schema Audit</h1>
                    <p className="text-muted-foreground">
                        Quick health check - only showing issues
                    </p>
                </div>
                <Button variant="outline" size="sm" onClick={copyIssuesReport}>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy Report
                </Button>
            </div>

            {/* Summary */}
            <div className="flex gap-4">
                <Card className="flex-1">
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-2">
                            <CheckCircle2 className="h-5 w-5 text-green-600" />
                            <span className="text-2xl font-bold">{healthy.length}</span>
                            <span className="text-muted-foreground">Healthy</span>
                        </div>
                    </CardContent>
                </Card>
                <Card className="flex-1">
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-2">
                            <AlertTriangle className="h-5 w-5 text-yellow-600" />
                            <span className="text-2xl font-bold">{warnings.length}</span>
                            <span className="text-muted-foreground">Warnings</span>
                        </div>
                    </CardContent>
                </Card>
                <Card className="flex-1">
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-2">
                            <XCircle className="h-5 w-5 text-blue-600" />
                            <span className="text-2xl font-bold">{infos.length}</span>
                            <span className="text-muted-foreground">Info</span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Issues */}
            {issues.length > 0 ? (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Issues Found</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {issues.map((issue, i) => (
                                <div key={i} className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg">
                                    {issue.type === "warning" ? (
                                        <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                                    ) : (
                                        <XCircle className="h-5 w-5 text-blue-600 mt-0.5" />
                                    )}
                                    <div>
                                        <div className="font-medium">{issue.model}</div>
                                        <div className="text-sm text-muted-foreground">
                                            {issue.message}
                                        </div>
                                        {issue.details && (
                                            <div className="text-xs text-muted-foreground mt-1">
                                                {issue.details}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            ) : (
                <Card>
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-2 text-green-600">
                            <CheckCircle2 className="h-5 w-5" />
                            <span className="font-medium">All models are properly configured</span>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Healthy models list */}
            {healthy.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Healthy Models</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-2">
                            {healthy.map(model => (
                                <Badge key={model} variant="secondary">
                                    {model}
                                </Badge>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
