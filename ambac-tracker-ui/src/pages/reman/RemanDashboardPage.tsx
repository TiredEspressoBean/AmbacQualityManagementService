import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Link } from "@tanstack/react-router";
import { useRetrieveCores } from "@/hooks/useRetrieveCores";
import { useRetrieveHarvestedComponents } from "@/hooks/useRetrieveHarvestedComponents";
import { Package, Wrench, CheckCircle, AlertTriangle, ArrowRight, Boxes } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export function RemanDashboardPage() {
    // Fetch summary data
    const { data: coresData, isLoading: coresLoading } = useRetrieveCores({ limit: 1 });
    const { data: receivedCores } = useRetrieveCores({ status: "received", limit: 1 });
    const { data: inDisassemblyCores } = useRetrieveCores({ status: "in_disassembly", limit: 1 });
    const { data: componentsData, isLoading: componentsLoading } = useRetrieveHarvestedComponents({ limit: 1 });
    const { data: usableComponents } = useRetrieveHarvestedComponents({ is_scrapped: "false", limit: 1 });

    const totalCores = coresData?.count ?? 0;
    const awaitingDisassembly = receivedCores?.count ?? 0;
    const inProgress = inDisassemblyCores?.count ?? 0;
    const totalComponents = componentsData?.count ?? 0;
    const usable = usableComponents?.count ?? 0;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Remanufacturing</h1>
                    <p className="text-muted-foreground">
                        Core receiving, disassembly, and component harvesting
                    </p>
                </div>
                <Button asChild>
                    <Link to="/reman/cores/receive">
                        <Package className="mr-2 h-4 w-4" />
                        Receive Core
                    </Link>
                </Button>
            </div>

            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            Total Cores
                        </CardTitle>
                        <Package className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {coresLoading ? (
                            <Skeleton className="h-8 w-20" />
                        ) : (
                            <div className="text-2xl font-bold">{totalCores}</div>
                        )}
                        <p className="text-xs text-muted-foreground">
                            All time received
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            Awaiting Disassembly
                        </CardTitle>
                        <AlertTriangle className="h-4 w-4 text-yellow-500" />
                    </CardHeader>
                    <CardContent>
                        {coresLoading ? (
                            <Skeleton className="h-8 w-20" />
                        ) : (
                            <div className="text-2xl font-bold">{awaitingDisassembly}</div>
                        )}
                        <p className="text-xs text-muted-foreground">
                            Cores ready to process
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            In Disassembly
                        </CardTitle>
                        <Wrench className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        {coresLoading ? (
                            <Skeleton className="h-8 w-20" />
                        ) : (
                            <div className="text-2xl font-bold">{inProgress}</div>
                        )}
                        <p className="text-xs text-muted-foreground">
                            Currently being processed
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            Usable Components
                        </CardTitle>
                        <CheckCircle className="h-4 w-4 text-green-500" />
                    </CardHeader>
                    <CardContent>
                        {componentsLoading ? (
                            <Skeleton className="h-8 w-20" />
                        ) : (
                            <div className="text-2xl font-bold">
                                {usable} <span className="text-sm text-muted-foreground">/ {totalComponents}</span>
                            </div>
                        )}
                        <p className="text-xs text-muted-foreground">
                            Available for inventory
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Quick Actions */}
            <div className="grid gap-4 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Core Management</CardTitle>
                        <CardDescription>
                            Receive and process incoming cores
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <Button variant="outline" className="w-full justify-between" asChild>
                            <Link to="/reman/cores">
                                View All Cores
                                <ArrowRight className="h-4 w-4" />
                            </Link>
                        </Button>
                        <Button variant="outline" className="w-full justify-between" asChild>
                            <Link to="/reman/cores" search={{ status: "received" }}>
                                Cores Awaiting Disassembly ({awaitingDisassembly})
                                <ArrowRight className="h-4 w-4" />
                            </Link>
                        </Button>
                        <Button variant="outline" className="w-full justify-between" asChild>
                            <Link to="/reman/cores" search={{ status: "in_disassembly" }}>
                                Cores In Progress ({inProgress})
                                <ArrowRight className="h-4 w-4" />
                            </Link>
                        </Button>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Harvested Components</CardTitle>
                        <CardDescription>
                            Components extracted from cores
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <Button variant="outline" className="w-full justify-between" asChild>
                            <Link to="/reman/components">
                                View All Components
                                <ArrowRight className="h-4 w-4" />
                            </Link>
                        </Button>
                        <Button variant="outline" className="w-full justify-between" asChild>
                            <Link to="/reman/components" search={{ is_scrapped: "false" }}>
                                Usable Components ({usable})
                                <ArrowRight className="h-4 w-4" />
                            </Link>
                        </Button>
                        <Button variant="outline" className="w-full justify-between" asChild>
                            <Link to="/reman/components" search={{ component_part__isnull: "true", is_scrapped: "false" }}>
                                Pending Inventory Acceptance
                                <Boxes className="h-4 w-4" />
                            </Link>
                        </Button>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

export default RemanDashboardPage;
