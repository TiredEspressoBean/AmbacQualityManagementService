import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { QRMeasurementsSection } from "./QRMeasurementsSection";
import { CAPA_DECISION_LABEL } from "@/lib/quality-labels";

const LABEL = CAPA_DECISION_LABEL;

/**
 * The NCR a failed record is on. What's wrong, the decision on each part and whether it
 * needs a CAPA are all the NCR's — made on its page, not here.
 */
function NcrCard({ report }: { report: Record<string, unknown> }) {
    const ncrId = report.ncr ? String(report.ncr) : null;
    const decision = (report.capa_decision as string | null) ?? null;
    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                    NCR
                    {ncrId && (decision
                        ? <Badge variant={decision === "PROMOTED" ? "default" : "outline"}>{LABEL[decision] ?? decision}</Badge>
                        : <Badge variant="secondary">CAPA not decided</Badge>)}
                </CardTitle>
            </CardHeader>
            <CardContent className="text-sm">
                {ncrId ? (
                    <p>
                        This failure is on{" "}
                        <Link to="/quality/ncrs/$ncrId" params={{ ncrId }}
                              className="font-mono text-primary underline-offset-2 hover:underline">
                            {String(report.ncr_number ?? "its NCR")}
                        </Link>
                        . The decision on the part, and whether a CAPA is needed, are made there.
                    </p>
                ) : (
                    <p className="text-muted-foreground">Not on an NCR.</p>
                )}
            </CardContent>
        </Card>
    );
}

/** The inspection record's lower section: its NCR (failures only), then the
 *  measurements. */
export function QRDetailSections({ modelData }: { modelData: Record<string, unknown> }) {
    return (
        <div className="space-y-4">
            {modelData.status === "FAIL" && <NcrCard report={modelData} />}
            <QRMeasurementsSection modelData={modelData} />
        </div>
    );
}
