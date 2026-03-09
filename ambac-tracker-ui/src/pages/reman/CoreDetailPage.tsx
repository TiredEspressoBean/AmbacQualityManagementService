import { useParams, Link, useNavigate } from "@tanstack/react-router";
import { useRetrieveCore } from "@/hooks/useRetrieveCore";
import { useRetrieveHarvestedComponents } from "@/hooks/useRetrieveHarvestedComponents";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { format } from "date-fns";
import { ArrowLeft, Play, CheckCircle, Trash2, DollarSign, Package } from "lucide-react";

// Status badge variants
function getStatusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
    switch (status) {
        case 'RECEIVED': return 'secondary';
        case 'IN_DISASSEMBLY': return 'default';
        case 'DISASSEMBLED': return 'outline';
        case 'SCRAPPED': return 'destructive';
        default: return 'outline';
    }
}

function getConditionVariant(grade: string): "default" | "secondary" | "destructive" | "outline" {
    switch (grade) {
        case 'A': return 'default';
        case 'B': return 'secondary';
        case 'C': return 'outline';
        case 'SCRAP': return 'destructive';
        default: return 'outline';
    }
}

const statusLabels: Record<string, string> = {
    'RECEIVED': 'Received',
    'IN_DISASSEMBLY': 'In Disassembly',
    'DISASSEMBLED': 'Disassembled',
    'SCRAPPED': 'Scrapped',
};

const conditionLabels: Record<string, string> = {
    'A': 'Grade A - Excellent',
    'B': 'Grade B - Good',
    'C': 'Grade C - Fair',
    'scrap': 'Scrap - Not Usable',
};

const sourceLabels: Record<string, string> = {
    'customer_return': 'Customer Return',
    'purchased': 'Purchased Core',
    'warranty': 'Warranty Return',
    'trade_in': 'Trade-In',
};

export function CoreDetailPage() {
    const { id } = useParams({ from: '/reman/cores/$id' });
    const navigate = useNavigate();
    const { data: core, isLoading, error } = useRetrieveCore(id);
    const { data: componentsData } = useRetrieveHarvestedComponents({ core: id });

    if (isLoading) {
        return (
            <div className="space-y-4">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-32 w-full" />
            </div>
        );
    }

    if (error || !core) {
        return (
            <div className="text-center py-8">
                <p className="text-destructive">Failed to load core details</p>
                <Button variant="outline" className="mt-4" asChild>
                    <Link to="/reman/cores">Back to Cores</Link>
                </Button>
            </div>
        );
    }

    const components = componentsData?.results ?? [];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" asChild>
                        <Link to="/reman/cores">
                            <ArrowLeft className="h-4 w-4" />
                        </Link>
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2">
                            Core {core.core_number}
                            <Badge variant={getStatusVariant(core.status || '')}>
                                {statusLabels[core.status || ''] || core.status}
                            </Badge>
                        </h1>
                        <p className="text-muted-foreground">{core.core_type_name}</p>
                    </div>
                </div>
                <div className="flex gap-2">
                    {core.status === 'RECEIVED' && (
                        <>
                            <Button
                                variant="default"
                                onClick={() => navigate({ to: `/reman/cores/${id}/disassembly` })}
                            >
                                <Play className="mr-2 h-4 w-4" />
                                Start Disassembly
                            </Button>
                            <Button
                                variant="destructive"
                                onClick={() => navigate({ to: `/reman/cores/${id}/scrap` })}
                            >
                                <Trash2 className="mr-2 h-4 w-4" />
                                Scrap
                            </Button>
                        </>
                    )}
                    {core.status === 'IN_DISASSEMBLY' && (
                        <Button
                            variant="default"
                            onClick={() => navigate({ to: `/reman/cores/${id}/disassembly` })}
                        >
                            <CheckCircle className="mr-2 h-4 w-4" />
                            Continue Disassembly
                        </Button>
                    )}
                    {!core.core_credit_issued && core.core_credit_value && (
                        <Button variant="outline">
                            <DollarSign className="mr-2 h-4 w-4" />
                            Issue Credit
                        </Button>
                    )}
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                {/* Core Information */}
                <Card>
                    <CardHeader>
                        <CardTitle>Core Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-sm text-muted-foreground">Core Number</p>
                                <p className="font-mono font-medium">{core.core_number}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Serial Number</p>
                                <p className="font-mono">{core.serial_number || "—"}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Core Type</p>
                                <p>{core.core_type_name}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Condition</p>
                                <Badge variant={getConditionVariant(core.condition_grade)}>
                                    {conditionLabels[core.condition_grade] || core.condition_grade}
                                </Badge>
                            </div>
                        </div>
                        {core.condition_notes && (
                            <div>
                                <p className="text-sm text-muted-foreground">Condition Notes</p>
                                <p className="text-sm">{core.condition_notes}</p>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Source Information */}
                <Card>
                    <CardHeader>
                        <CardTitle>Source & Receipt</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-sm text-muted-foreground">Source Type</p>
                                <p>{sourceLabels[core.source_type || ''] || core.source_type}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Reference</p>
                                <p>{core.source_reference || "—"}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Customer</p>
                                <p>{core.customer_name || "—"}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Received Date</p>
                                <p>{format(new Date(core.received_date), "PPP")}</p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Received By</p>
                                <p>{core.received_by_name || "—"}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Credit Information */}
                <Card>
                    <CardHeader>
                        <CardTitle>Core Credit</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-sm text-muted-foreground">Credit Value</p>
                                <p className="text-xl font-bold">
                                    {core.core_credit_value
                                        ? `$${parseFloat(core.core_credit_value).toFixed(2)}`
                                        : "Not set"}
                                </p>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Credit Status</p>
                                <Badge variant={core.core_credit_issued ? "default" : "secondary"}>
                                    {core.core_credit_issued ? "Issued" : "Pending"}
                                </Badge>
                            </div>
                            {core.core_credit_issued_at && (
                                <div>
                                    <p className="text-sm text-muted-foreground">Issued At</p>
                                    <p>{format(new Date(core.core_credit_issued_at), "PPP p")}</p>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Disassembly Status */}
                <Card>
                    <CardHeader>
                        <CardTitle>Disassembly Status</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-sm text-muted-foreground">Status</p>
                                <Badge variant={getStatusVariant(core.status || '')}>
                                    {statusLabels[core.status || ''] || core.status}
                                </Badge>
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">Components Harvested</p>
                                <p className="text-xl font-bold">{components.length}</p>
                            </div>
                            {core.disassembly_started_at && (
                                <div>
                                    <p className="text-sm text-muted-foreground">Started</p>
                                    <p>{format(new Date(core.disassembly_started_at), "PPP p")}</p>
                                </div>
                            )}
                            {core.disassembly_completed_at && (
                                <div>
                                    <p className="text-sm text-muted-foreground">Completed</p>
                                    <p>{format(new Date(core.disassembly_completed_at), "PPP p")}</p>
                                </div>
                            )}
                            {core.disassembled_by_name && (
                                <div>
                                    <p className="text-sm text-muted-foreground">Disassembled By</p>
                                    <p>{core.disassembled_by_name}</p>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Harvested Components */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Package className="h-5 w-5" />
                        Harvested Components ({components.length})
                    </CardTitle>
                    <CardDescription>
                        Components extracted during disassembly
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {components.length === 0 ? (
                        <p className="text-center py-8 text-muted-foreground">
                            No components harvested yet
                        </p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Component Type</TableHead>
                                    <TableHead>Position</TableHead>
                                    <TableHead>Condition</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Part ID</TableHead>
                                    <TableHead>Harvested</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {components.map((component: any) => (
                                    <TableRow key={component.id}>
                                        <TableCell className="font-medium">
                                            {component.component_type_name}
                                        </TableCell>
                                        <TableCell>{component.position || "—"}</TableCell>
                                        <TableCell>
                                            <Badge variant={getConditionVariant(component.condition_grade)}>
                                                {component.condition_grade}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            {component.is_scrapped ? (
                                                <Badge variant="destructive">Scrapped</Badge>
                                            ) : component.component_part ? (
                                                <Badge variant="default">In Inventory</Badge>
                                            ) : (
                                                <Badge variant="secondary">Pending</Badge>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            {component.component_part_erp_id ? (
                                                <Link
                                                    to={`/details/Parts/${component.component_part}`}
                                                    className="font-mono text-primary hover:underline"
                                                >
                                                    {component.component_part_erp_id}
                                                </Link>
                                            ) : (
                                                "—"
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            {format(new Date(component.disassembled_at), "MMM d, yyyy")}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

export default CoreDetailPage;
