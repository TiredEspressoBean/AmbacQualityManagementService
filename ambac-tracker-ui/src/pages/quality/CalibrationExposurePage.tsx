/**
 * What a gauge measured while it may have been out of tolerance (ISO 9001 7.1.5.2).
 *
 * A failed calibration takes the gauge out of service, which protects the next part; it
 * says nothing about the parts already measured. A gauge drifts during the interval, so
 * everything it measured since its last good calibration is in question. This page is
 * that list, and the window it was drawn from — the window is the finding, so it leads.
 *
 * It doesn't act on the list. Re-inspecting, accepting on other evidence, telling a
 * customer or raising an NCR are decisions for whoever reads it.
 */
import { useState } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { queryOptions, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Download } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api/generated";
import { blobErrorMessage, downloadBlob } from "@/lib/download";

const calibrationExposureOptions = (id: string) =>
    queryOptions({
        queryKey: ["calibration-exposure", id],
        queryFn: () => api.api_CalibrationRecords_exposure_retrieve({ params: { id } }),
        retry: false,  // a 400 ("found it in tolerance") is an answer, not a blip
    });

export function CalibrationExposurePage() {
    const { id } = useParams({ from: "/quality/calibrations/records/$id/exposure" });
    const [busy, setBusy] = useState(false);
    const { data, isLoading, error } = useQuery(calibrationExposureOptions(id));

    const download = async () => {
        if (!data) return;
        setBusy(true);
        try {
            const resp = await api.axios.get(`/api/CalibrationRecords/${id}/exposure-export/`, {
                responseType: "blob",
            });
            downloadBlob(resp.data, `measured_by_${data.equipment_name}_${data.window_end}.xlsx`);
        } catch (e) {
            toast.error(await blobErrorMessage(e, "Couldn't build the sheet."));
        } finally {
            setBusy(false);
        }
    };

    const detail = (error as { response?: { data?: { detail?: string } } } | null)?.response?.data?.detail;

    return (
        <div className="container mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
            <Button asChild variant="ghost" size="sm" className="-ml-2">
                <Link to="/quality/calibrations/records">
                    <ArrowLeft className="mr-1.5 h-4 w-4" />
                    Calibration records
                </Link>
            </Button>

            {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
            ) : error || !data ? (
                <Card>
                    <CardContent className="py-6 text-sm text-muted-foreground">
                        {detail ?? "Couldn't load what this gauge measured."}
                    </CardContent>
                </Card>
            ) : (
                <>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="space-y-1">
                            <h1 className="text-2xl font-semibold">What {data.equipment_name} measured</h1>
                            <p className="text-balance text-muted-foreground">{data.window_sentence}</p>
                        </div>
                        <Button onClick={download} disabled={busy || data.count === 0}>
                            <Download className="mr-1.5 h-4 w-4" />
                            {busy ? "Building…" : "Download"}
                        </Button>
                    </div>

                    <Card>
                        <CardHeader>
                            <CardTitle className="tabular-nums">
                                {data.count} quality report{data.count === 1 ? "" : "s"}
                            </CardTitle>
                            <CardDescription>
                                {data.result === "FAIL"
                                    ? "This gauge failed calibration."
                                    : "This gauge was found out of tolerance before adjustment."}{" "}
                                It may have been out of tolerance for any of these measurements. Whether
                                to re-inspect, accept on other evidence, tell a customer or raise an NCR
                                is decided outside this list.
                                {data.window_start == null && (
                                    <> There is no earlier passing calibration on record, so this is
                                        everything it measured up to the check.</>
                                )}
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="overflow-x-auto">
                            {data.count === 0 ? (
                                <p className="text-sm text-muted-foreground">
                                    This gauge wasn&rsquo;t recorded on any quality report in the window.
                                </p>
                            ) : (
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Report</TableHead>
                                            <TableHead>Part / lot</TableHead>
                                            <TableHead>Step</TableHead>
                                            <TableHead>Filed</TableHead>
                                            <TableHead>Inspector</TableHead>
                                            <TableHead>Result</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {data.reports.map((r) => (
                                            <TableRow key={r.id}>
                                                <TableCell className="font-medium tabular-nums">
                                                    {r.report_number || "—"}
                                                </TableCell>
                                                <TableCell>{r.part || "—"}</TableCell>
                                                <TableCell>{r.step || "—"}</TableCell>
                                                <TableCell className="tabular-nums">
                                                    {new Date(r.created_at).toLocaleDateString()}
                                                </TableCell>
                                                <TableCell>{r.inspector || "—"}</TableCell>
                                                <TableCell>
                                                    <Badge variant={r.status === "FAIL" ? "destructive" : r.status === "PASS" ? "secondary" : "outline"}>
                                                        {r.status}
                                                    </Badge>
                                                    {r.role && r.role !== "GAUGE" && (
                                                        <span className="ml-2 text-xs text-muted-foreground">as {r.role.toLowerCase()}</span>
                                                    )}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            )}
                        </CardContent>
                    </Card>
                </>
            )}
        </div>
    );
}
