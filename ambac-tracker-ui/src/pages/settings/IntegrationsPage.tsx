import { Link } from "@tanstack/react-router";
import { ArrowLeft, Link2, CheckCircle, AlertCircle, Circle, Loader2, ChevronRight } from "lucide-react";
import { useIntegrationsCatalog } from "@/hooks/useIntegrationsCatalog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDistanceToNow } from "date-fns";

type CatalogItem = {
    provider: string;
    name: string;
    description: string;
    icon: string;
    auth_type: string;
    capabilities: string[];
    status: string;
    config_id: string | null;
    is_enabled: boolean;
    display_name: string;
    sync_status: string | null;
    last_synced_at: string | null;
    last_sync_error: string | null;
    last_sync_stats: Record<string, number> | null;
};

function StatusBadge({ status }: { status: string }) {
    switch (status) {
        case "connected":
            return (
                <Badge variant="default" className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 border-green-200 dark:border-green-800">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    Connected
                </Badge>
            );
        case "error":
            return (
                <Badge variant="destructive">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    Error
                </Badge>
            );
        case "syncing":
            return (
                <Badge variant="secondary">
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    Syncing
                </Badge>
            );
        case "disabled":
            return (
                <Badge variant="outline">
                    <Circle className="h-3 w-3 mr-1" />
                    Disabled
                </Badge>
            );
        case "not_configured":
        default:
            return null;
    }
}

function IntegrationCard({ item }: { item: CatalogItem }) {
    const isConfigured = item.status !== "not_configured";
    const href = isConfigured
        ? `/settings/integrations/${item.config_id}`
        : `/settings/integrations/new?provider=${item.provider}`;

    return (
        <Link to={href} className="block">
            <Card className="h-full transition-all hover:border-primary/50 hover:shadow-sm cursor-pointer">
                <CardHeader className="pb-2">
                    <div className="flex items-start gap-3">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                            <Link2 className="h-5 w-5 text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                                <CardTitle className="text-base">{item.name}</CardTitle>
                                <StatusBadge status={item.status} />
                            </div>
                            <CardDescription className="text-sm mt-0.5">
                                {item.description}
                            </CardDescription>
                        </div>
                        <ChevronRight className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                    </div>
                </CardHeader>
                {isConfigured && item.last_synced_at && (
                    <CardContent className="pt-0 pb-3">
                        <p className="text-xs text-muted-foreground pl-[52px]">
                            Synced {formatDistanceToNow(new Date(item.last_synced_at), { addSuffix: true })}
                        </p>
                    </CardContent>
                )}
            </Card>
        </Link>
    );
}

export function IntegrationsPage() {
    const { data: catalog, isLoading, isError } = useIntegrationsCatalog();

    const configured = catalog?.filter(i => i.status !== "not_configured") ?? [];
    const available = catalog?.filter(i => i.status === "not_configured") ?? [];
    const hasErrors = configured.some(i => i.status === "error");
    const isEmpty = !isLoading && catalog?.length === 0;
    const noneConfigured = !isLoading && configured.length === 0 && available.length > 0;

    if (isError) {
        return (
            <div className="container mx-auto p-6 max-w-4xl">
                <div className="text-center py-12">
                    <p className="text-destructive">Failed to load integrations</p>
                    <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>
                        Retry
                    </Button>
                </div>
            </div>
        );
    }

    return (
        <div className="container mx-auto p-6 max-w-4xl">
            {/* Header */}
            <div className="mb-6">
                <Link to="/settings" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4">
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Back to Settings
                </Link>
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <Link2 className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold">Integrations</h1>
                    </div>
                </div>
            </div>

            {isLoading ? (
                <div className="grid gap-4 sm:grid-cols-2">
                    <Skeleton className="h-24" />
                    <Skeleton className="h-24" />
                </div>
            ) : isEmpty ? (
                /* Empty state — no integrations available at all */
                <div className="text-center py-16">
                    <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted mx-auto mb-4">
                        <Link2 className="h-7 w-7 text-muted-foreground" />
                    </div>
                    <h2 className="text-lg font-medium mb-1">No integrations available</h2>
                    <p className="text-sm text-muted-foreground">
                        Integrations will appear here when they are configured for your deployment.
                    </p>
                </div>
            ) : (
                <>
                    {/* Needs attention */}
                    {hasErrors && (
                        <Card className="mb-6 border-destructive/50 bg-destructive/5">
                            <CardContent className="py-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <AlertCircle className="h-4 w-4 text-destructive" />
                                    <span className="text-sm font-medium text-destructive">Needs attention</span>
                                </div>
                                {configured.filter(i => i.status === "error").map(item => (
                                    <div key={item.provider} className="flex items-center justify-between py-1">
                                        <span className="text-sm">{item.name}: {item.last_sync_error || "Sync failed"}</span>
                                        <Link to={`/settings/integrations/${item.config_id}`}>
                                            <Button variant="outline" size="sm" className="h-7 text-xs">
                                                View
                                            </Button>
                                        </Link>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    )}

                    {/* First-time guidance — only when nothing is configured yet */}
                    {noneConfigured && (
                        <div className="mb-6 p-4 rounded-lg bg-muted/50 text-sm text-muted-foreground">
                            Connect an integration to automatically sync orders, contacts, and pipeline data from your external systems.
                        </div>
                    )}

                    {/* Connected */}
                    {configured.length > 0 && (
                        <div className="mb-6">
                            <h2 className="text-sm font-medium text-muted-foreground mb-3">
                                Connected
                            </h2>
                            <div className="grid gap-3 sm:grid-cols-2">
                                {configured.map(item => (
                                    <IntegrationCard key={item.provider} item={item} />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Available */}
                    {available.length > 0 && (
                        <div>
                            <h2 className="text-sm font-medium text-muted-foreground mb-3">
                                Available
                            </h2>
                            <div className="grid gap-3 sm:grid-cols-2">
                                {available.map(item => (
                                    <IntegrationCard key={item.provider} item={item} />
                                ))}
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}