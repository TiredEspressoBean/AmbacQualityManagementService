/**
 * A machine's latest calibration records, read-only on the equipment form. Records
 * are day-to-day quality work with their own pages; this shows where the machine
 * stands and links through.
 */
import { Link } from "@tanstack/react-router";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCalibrationRecords } from "@/hooks/useCalibrationRecords";

export function EquipmentCalibrationHistory({ equipmentId }: { equipmentId: string }) {
    const { data, isLoading } = useCalibrationRecords({ equipment: equipmentId, ordering: "-calibration_date", limit: 5 });
    const rows = data?.results ?? [];
    const total = data?.count ?? 0;

    return (
        <div className="space-y-3">
            {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
            ) : rows.length === 0 ? (
                <p className="text-sm text-muted-foreground">No calibrations recorded for this machine.</p>
            ) : (
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Calibrated</TableHead>
                            <TableHead>Due</TableHead>
                            <TableHead>Result</TableHead>
                            <TableHead>By</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {rows.map((r) => (
                            <TableRow key={r.id}>
                                <TableCell className="tabular-nums">
                                    <Link to="/CalibrationRecordForm/$id" params={{ id: r.id }} className="hover:underline">
                                        {r.calibration_date}
                                    </Link>
                                </TableCell>
                                <TableCell className="tabular-nums">
                                    {r.due_date}
                                    {r.is_current && r.days_overdue != null && r.days_overdue > 0 && (
                                        <Badge variant="destructive" className="ml-2">Overdue</Badge>
                                    )}
                                </TableCell>
                                <TableCell>{r.result_display}</TableCell>
                                <TableCell className="text-muted-foreground">{r.performed_by || r.external_lab || "—"}</TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            )}
            <div className="flex items-center gap-2">
                <Button asChild variant="outline" size="sm">
                    <Link to="/CalibrationRecordForm/$id" params={{ id: "new" }}>Record a calibration</Link>
                </Button>
                {total > rows.length && (
                    <Button asChild variant="ghost" size="sm">
                        <Link to="/quality/calibrations/records" search={{ equipment: equipmentId } as never}>
                            All {total} records
                        </Link>
                    </Button>
                )}
            </div>
        </div>
    );
}
