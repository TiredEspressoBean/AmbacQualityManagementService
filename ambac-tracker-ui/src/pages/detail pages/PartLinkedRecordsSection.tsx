import { Link } from "@tanstack/react-router";
import { useQualityReports } from "@/hooks/useQualityReports";
import { useRetrieveQuarantineDispositions } from "@/hooks/useRetrieveQuarantineDispositions";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

// Compact list of QRs + Dispositions filtered by part id, rendered under the
// info sections on the part-detail page. Each row deep-links into the
// underlying record so a QA inspector opening a quarantined part can jump
// straight to the failing report or the pending disposition without hunting.
// The whole section stays hidden when the part has neither — clean parts stay
// clean.
export function PartLinkedRecordsSection({ modelData }: { modelData: { id?: string | number } }) {
    const partId = modelData?.id ? String(modelData.id) : undefined;

    const { data: qrData, isLoading: qrLoading } = useQualityReports(
        partId ? ({ part: partId, limit: 10 } as never) : undefined,
        undefined,
        { enabled: !!partId } as never,
    );
    const { data: dispositionData, isLoading: dispositionLoading } = useRetrieveQuarantineDispositions(
        partId ? ({ part: partId, limit: 10 } as never) : undefined,
        undefined,
        { enabled: !!partId } as never,
    );

    if (!partId) return null;

    // Loose typing — the OpenAPI schemas type these as passthrough objects; the
    // actual runtime fields are read directly.
    const qrs = ((qrData as { results?: Array<Record<string, unknown>> } | undefined)?.results) ?? [];
    const dispositions =
        ((dispositionData as { results?: Array<Record<string, unknown>> } | undefined)?.results) ?? [];

    const stillLoading = qrLoading || dispositionLoading;
    if (stillLoading && qrs.length === 0 && dispositions.length === 0) {
        return null; // Nothing to show yet; skip a loading blip.
    }
    if (qrs.length === 0 && dispositions.length === 0) {
        return null; // Clean part — no need for the section at all.
    }

    return (
        <>
            <Separator />
            {qrs.length > 0 && (
                <section className="space-y-3">
                    <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                            Quality Reports
                        </h3>
                        <Badge variant="secondary">{qrs.length}</Badge>
                    </div>
                    <div className="space-y-1">
                        {qrs.map((qr) => {
                            const id = String(qr.id ?? "");
                            const reportNumber = (qr.report_number as string | undefined) ?? id.slice(0, 8);
                            const status = (qr.status as string | undefined) ?? "—";
                            const stepInfo = qr.step_info as { name?: string } | undefined;
                            const stepName = stepInfo?.name ?? "";
                            const createdAt = qr.created_at as string | undefined;
                            return (
                                <Link
                                    key={id}
                                    to="/details/$model/$id"
                                    params={{ model: "QualityReports", id }}
                                    className="flex items-center gap-3 rounded-md border p-2 text-sm hover:bg-muted/50"
                                >
                                    <span className="font-mono text-primary">{reportNumber}</span>
                                    <QRStatusBadge status={status} />
                                    {stepName && (
                                        <span className="text-muted-foreground truncate">{stepName}</span>
                                    )}
                                    {createdAt && (
                                        <span className="ml-auto text-xs text-muted-foreground">
                                            {new Date(createdAt).toLocaleDateString()}
                                        </span>
                                    )}
                                </Link>
                            );
                        })}
                    </div>
                </section>
            )}
            {dispositions.length > 0 && (
                <>
                    {qrs.length > 0 && <Separator />}
                    <section className="space-y-3">
                        <div className="flex items-center gap-2">
                            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                Dispositions
                            </h3>
                            <Badge variant="secondary">{dispositions.length}</Badge>
                        </div>
                        <div className="space-y-1">
                            {dispositions.map((d) => {
                                const id = String(d.id ?? "");
                                const dispNumber = (d.disposition_number as string | undefined) ?? id.slice(0, 8);
                                const state = (d.current_state as string | undefined) ?? "—";
                                const type = (d.disposition_type as string | undefined) ?? "";
                                const severity = (d.severity as string | undefined) ?? "";
                                const updatedAt = d.updated_at as string | undefined;
                                return (
                                    <Link
                                        key={id}
                                        to="/details/$model/$id"
                                        params={{ model: "QuarantineDisposition", id }}
                                        className="flex items-center gap-3 rounded-md border p-2 text-sm hover:bg-muted/50"
                                    >
                                        <span className="font-mono text-primary">{dispNumber}</span>
                                        <DispositionStateBadge state={state} />
                                        {type && <span className="text-muted-foreground">{type}</span>}
                                        {severity && severity !== "—" && (
                                            <Badge variant="outline" className="text-xs">{severity}</Badge>
                                        )}
                                        {updatedAt && (
                                            <span className="ml-auto text-xs text-muted-foreground">
                                                {new Date(updatedAt).toLocaleDateString()}
                                            </span>
                                        )}
                                    </Link>
                                );
                            })}
                        </div>
                    </section>
                </>
            )}
        </>
    );
}

// Colour-coded status pill for a QR row — mirrors the shop-floor convention
// (green = pass, red = fail, gray = pending). Keeps this file self-contained
// rather than importing a shared StatusBadge whose exact API varies.
function QRStatusBadge({ status }: { status: string }) {
    const tone =
        status === "PASS"
            ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
            : status === "FAIL"
                ? "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
                : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300";
    return <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${tone}`}>{status}</span>;
}

function DispositionStateBadge({ state }: { state: string }) {
    const tone =
        state === "CLOSED"
            ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
            : state === "IN_PROGRESS"
                ? "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300"
                : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300";
    return <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${tone}`}>{state}</span>;
}
