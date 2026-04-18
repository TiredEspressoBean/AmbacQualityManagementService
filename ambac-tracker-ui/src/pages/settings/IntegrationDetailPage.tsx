import { useState, useEffect, useRef } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { useIntegrationsCatalog } from "@/hooks/useIntegrationsCatalog";
import { useCreateIntegration } from "@/hooks/useCreateIntegration";
import { useUpdateIntegration } from "@/hooks/useUpdateIntegration";
import { useDeleteIntegration } from "@/hooks/useDeleteIntegration";
import { useTestIntegrationConnection } from "@/hooks/useTestIntegrationConnection";
import { useTriggerIntegrationSync } from "@/hooks/useTriggerIntegrationSync";
import { useIntegrationSyncLogs } from "@/hooks/useIntegrationSyncLogs";
import {
    ArrowLeft, Link2, CheckCircle, AlertCircle, Circle, Loader2,
    Zap, RefreshCw, Trash2, Power, PowerOff, ArrowDownToLine,
    ArrowUpFromLine, ExternalLink, Info, Shield, Settings
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
    AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";

type CatalogItem = {
    provider: string;
    name: string;
    category: string;
    description: string;
    long_description: string;
    icon: string;
    capabilities: string[];
    auth_type: string;
    auth_label: string;
    auth_instructions: string;
    auth_docs_url: string;
    data_flows: Array<{ direction: string; label: string; description: string }>;
    sync_details: Record<string, string>;
    requirements: string[];
    creates: string[];
    limitations: string[];
    status: string;
    config_id: string | null;
    is_enabled: boolean;
    display_name: string;
    sync_status: string | null;
    last_synced_at: string | null;
    last_sync_error: string | null;
    last_sync_stats: Record<string, number> | null;
    config: Record<string, any>;
};

function DirectionIcon({ direction }: { direction: string }) {
    if (direction === "inbound") return <ArrowDownToLine className="h-3.5 w-3.5 text-blue-500" />;
    if (direction === "outbound") return <ArrowUpFromLine className="h-3.5 w-3.5 text-green-500" />;
    return <RefreshCw className="h-3.5 w-3.5 text-muted-foreground" />;
}

export function IntegrationDetailPage() {
    const params = useParams({ strict: false });
    const rawId = params.id as string;

    const [apiKeyInput, setApiKeyInput] = useState("");
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const [isSyncPolling, setIsSyncPolling] = useState(false);
    const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Load catalog to get manifest data + config status
    const { data: catalog, isLoading: catalogLoading, refetch: refetchCatalog } = useIntegrationsCatalog();

    // Find the integration by config_id or provider
    const searchParams = new URLSearchParams(window.location.search);
    const providerParam = searchParams.get("provider");

    const item = (catalog as CatalogItem[] | undefined)?.find((i: CatalogItem) =>
        (rawId !== "new" && i.config_id === rawId) ||
        (rawId === "new" && i.provider === providerParam)
    );

    // If the URL says "new" but the catalog shows it's already configured, treat as edit
    const isConfigured = item ? (item.status !== "not_configured" && !!item.config_id) : false;
    const integrationId = item?.config_id ?? null;

    // Fetch sync logs (only for configured)
    const { data: syncLogs, refetch: refetchSyncLogs } = useIntegrationSyncLogs(
        { params: { id: integrationId! } },
        { enabled: !!integrationId }
    );

    // Poll for sync completion
    useEffect(() => {
        if (isSyncPolling) {
            pollIntervalRef.current = setInterval(async () => {
                const result = await refetchCatalog();
                const updated = (result.data as CatalogItem[] | undefined)?.find(
                    (i: CatalogItem) => i.config_id === integrationId
                );
                if (updated && updated.sync_status !== "SYNCING") {
                    setIsSyncPolling(false);
                    refetchSyncLogs();
                    if (updated.last_sync_error) {
                        toast.error(`Sync failed: ${updated.last_sync_error}`);
                    } else {
                        const stats = updated.last_sync_stats;
                        const msg = stats
                            ? `Sync complete: ${stats.created ?? 0} created, ${stats.updated ?? 0} updated`
                            : "Sync complete";
                        toast.success(msg);
                    }
                }
            }, 3000);
        }
        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
            }
        };
    }, [isSyncPolling, integrationId, refetchCatalog, refetchSyncLogs]);

    // Mutations
    const createIntegration = useCreateIntegration();
    const updateIntegration = useUpdateIntegration();
    const testConnection = useTestIntegrationConnection();
    const triggerSync = useTriggerIntegrationSync();
    const deleteIntegration = useDeleteIntegration();

    const handleSetup = async () => {
        if (!apiKeyInput.trim() || !item) return;
        try {
            if (isConfigured && integrationId) {
                // Already exists — update the key instead
                await updateIntegration.mutateAsync({ id: integrationId, data: { api_key: apiKeyInput } as any });
                toast.success("API key updated");
            } else {
                await createIntegration.mutateAsync({
                    provider: item.provider,
                    display_name: item.name,
                    api_key: apiKeyInput,
                    is_enabled: true,
                    config: {},
                } as any);
                toast.success("Integration connected");
            }
            setApiKeyInput("");
            // Refresh catalog so the page transitions to the configured view
            await refetchCatalog();
        } catch {
            toast.error("Failed to set up integration");
        }
    };

    const handleUpdateApiKey = async () => {
        if (!apiKeyInput.trim() || !integrationId) return;
        try {
            await updateIntegration.mutateAsync({ id: integrationId, data: { api_key: apiKeyInput } as any });
            toast.success("API key updated");
            setApiKeyInput("");
        } catch {
            toast.error("Failed to update API key");
        }
    };

    const handleToggleEnabled = async () => {
        if (!item || !integrationId) return;
        try {
            await updateIntegration.mutateAsync({ id: integrationId, data: { is_enabled: !item.is_enabled } as any });
            toast.success(item.is_enabled ? "Integration disabled" : "Integration enabled");
        } catch {
            toast.error("Failed to update integration");
        }
    };

    if (catalogLoading) {
        return (
            <div className="container mx-auto p-6 max-w-3xl">
                <Skeleton className="h-8 w-48 mb-6" />
                <Skeleton className="h-48 w-full mb-6" />
                <Skeleton className="h-32 w-full" />
            </div>
        );
    }

    if (!item) {
        return (
            <div className="container mx-auto p-6 max-w-3xl">
                <div className="text-center py-12">
                    <p className="text-muted-foreground">Integration not found</p>
                    <Link to="/settings/integrations">
                        <Button variant="outline" className="mt-4">Back to Integrations</Button>
                    </Link>
                </div>
            </div>
        );
    }

    const syncLogsArray = Array.isArray(syncLogs) ? syncLogs : [];

    return (
        <div className="container mx-auto p-6 max-w-3xl">
            {/* Header */}
            <div className="mb-6">
                <Link to="/settings/integrations" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4">
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Back to Integrations
                </Link>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                            <Link2 className="h-6 w-6 text-primary" />
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <h1 className="text-2xl font-bold">{item.name}</h1>
                                {item.category && (
                                    <Badge variant="outline" className="text-xs">{item.category}</Badge>
                                )}
                            </div>
                            <p className="text-sm text-muted-foreground">{item.description}</p>
                        </div>
                    </div>
                    {isConfigured && (
                        <Button variant="outline" size="sm" onClick={handleToggleEnabled}
                            disabled={updateIntegration.isPending}>
                            {item.is_enabled
                                ? <><PowerOff className="h-4 w-4 mr-1" /> Disable</>
                                : <><Power className="h-4 w-4 mr-1" /> Enable</>
                            }
                        </Button>
                    )}
                </div>
            </div>

            {/* About — always visible */}
            {item.long_description && (
                <p className="text-sm text-muted-foreground mb-6">{item.long_description}</p>
            )}

            {/* Data flows */}
            {item.data_flows.length > 0 && (
                <Card className="mb-6">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-lg">What syncs</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {item.data_flows.map((flow, idx) => (
                                <div key={idx} className="flex items-start gap-2.5">
                                    <DirectionIcon direction={flow.direction} />
                                    <div>
                                        <span className="text-sm font-medium">{flow.label}</span>
                                        <p className="text-xs text-muted-foreground">{flow.description}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Setup / Connection */}
            <Card className="mb-6">
                <CardHeader>
                    <CardTitle className="text-lg">
                        {isConfigured ? "Connection" : "Set up"}
                    </CardTitle>
                    {!isConfigured && item.auth_instructions && (
                        <CardDescription>{item.auth_instructions}</CardDescription>
                    )}
                </CardHeader>
                <CardContent className="space-y-4">
                    <div>
                        <label className="text-sm font-medium mb-1.5 block">{item.auth_label}</label>
                        <div className="flex gap-2">
                            <Input
                                type="password"
                                placeholder={isConfigured ? "Enter new key to update" : `Enter ${item.auth_label.toLowerCase()}`}
                                value={apiKeyInput}
                                onChange={(e) => setApiKeyInput(e.target.value)}
                                className="max-w-md"
                            />
                            <Button
                                variant={isConfigured ? "outline" : "default"}
                                onClick={isConfigured ? handleUpdateApiKey : handleSetup}
                                disabled={!apiKeyInput.trim() || createIntegration.isPending || updateIntegration.isPending}
                            >
                                {(createIntegration.isPending || updateIntegration.isPending)
                                    ? <Loader2 className="h-4 w-4 animate-spin" />
                                    : isConfigured ? "Update" : "Connect"
                                }
                            </Button>
                        </div>
                        {isConfigured && (
                            <p className="text-xs text-muted-foreground mt-1">Encrypted at rest. Current key is never displayed.</p>
                        )}
                        {item.auth_docs_url && (
                            <a href={item.auth_docs_url} target="_blank" rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs text-primary hover:underline mt-1">
                                How to get credentials <ExternalLink className="h-3 w-3" />
                            </a>
                        )}
                    </div>

                    {isConfigured && (
                        <>
                            <Separator />
                            <div className="flex items-center gap-3">
                                <Button variant="outline" size="sm"
                                    onClick={() => testConnection.mutate({ id: integrationId! }, {
                                        onSuccess: (data: any) => {
                                            setTestResult(data);
                                            toast[data.success ? "success" : "error"](data.message || "Connection test complete");
                                        },
                                        onError: () => {
                                            setTestResult({ success: false, message: "Connection test failed" });
                                            toast.error("Connection test failed");
                                        },
                                    })}
                                    disabled={testConnection.isPending}>
                                    {testConnection.isPending
                                        ? <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                                        : <Zap className="h-4 w-4 mr-1" />
                                    }
                                    Test Connection
                                </Button>
                                {testResult && (
                                    <span className={`text-sm ${testResult.success ? "text-green-600" : "text-destructive"}`}>
                                        {testResult.message}
                                    </span>
                                )}
                            </div>
                        </>
                    )}
                </CardContent>
            </Card>

            {/* Requirements & limitations — show when not yet configured */}
            {!isConfigured && (item.requirements.length > 0 || item.limitations.length > 0) && (
                <Card className="mb-6">
                    <CardContent className="py-4 space-y-4">
                        {item.requirements.length > 0 && (
                            <div>
                                <h3 className="text-sm font-medium flex items-center gap-1.5 mb-2">
                                    <Shield className="h-4 w-4 text-muted-foreground" />
                                    Requirements
                                </h3>
                                <ul className="space-y-1">
                                    {item.requirements.map((req, idx) => (
                                        <li key={idx} className="text-sm text-muted-foreground pl-5">• {req}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        {item.limitations.length > 0 && (
                            <div>
                                <h3 className="text-sm font-medium flex items-center gap-1.5 mb-2">
                                    <Info className="h-4 w-4 text-muted-foreground" />
                                    Limitations
                                </h3>
                                <ul className="space-y-1">
                                    {item.limitations.map((lim, idx) => (
                                        <li key={idx} className="text-sm text-muted-foreground pl-5">• {lim}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Configuration — only for configured */}
            {isConfigured && (
                <Card className="mb-6">
                    <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                            <Settings className="h-4 w-4" />
                            Configuration
                        </CardTitle>
                        <CardDescription>Provider-specific settings for this integration</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <Label htmlFor="pipeline-tracking">Pipeline Tracking</Label>
                                <p className="text-xs text-muted-foreground">
                                    Show pipeline stages as a progress bar on orders
                                </p>
                            </div>
                            <Switch
                                id="pipeline-tracking"
                                checked={item.config?.pipeline_tracking_enabled ?? true}
                                onCheckedChange={async (checked) => {
                                    try {
                                        await updateIntegration.mutateAsync({
                                            id: integrationId!,
                                            data: { config: { ...(item.config ?? {}), pipeline_tracking_enabled: checked } } as any,
                                        });
                                        await refetchCatalog();
                                        toast.success(checked ? "Pipeline tracking enabled" : "Pipeline tracking disabled");
                                    } catch {
                                        toast.error("Failed to update configuration");
                                    }
                                }}
                            />
                        </div>

                        <Separator />

                        <div>
                            <Label htmlFor="active-stage-prefix">Active Stage Prefix</Label>
                            <p className="text-xs text-muted-foreground mb-2">
                                Pipeline stages starting with this prefix are considered active. The prefix is stripped from display names.
                            </p>
                            <div className="flex gap-2">
                                <Input
                                    id="active-stage-prefix"
                                    placeholder="e.g. Active -"
                                    defaultValue={item.config?.active_stage_prefix ?? ""}
                                    className="max-w-xs"
                                    onBlur={async (e) => {
                                        const value = e.target.value;
                                        const currentPrefix = item.config?.active_stage_prefix ?? "";
                                        if (value === currentPrefix) return;
                                        try {
                                            await updateIntegration.mutateAsync({
                                                id: integrationId!,
                                                data: { config: { ...(item.config ?? {}), active_stage_prefix: value } } as any,
                                            });
                                            await refetchCatalog();
                                            toast.success("Prefix updated");
                                        } catch {
                                            toast.error("Failed to update prefix");
                                        }
                                    }}
                                />
                            </div>
                        </div>

                        <Separator />

                        <div className="flex items-center justify-between">
                            <div>
                                <Label htmlFor="debug-mode">Debug Mode</Label>
                                <p className="text-xs text-muted-foreground">
                                    Log detailed sync information for troubleshooting
                                </p>
                            </div>
                            <Switch
                                id="debug-mode"
                                checked={item.config?.debug_mode ?? false}
                                onCheckedChange={async (checked) => {
                                    try {
                                        await updateIntegration.mutateAsync({
                                            id: integrationId!,
                                            data: { config: { ...(item.config ?? {}), debug_mode: checked } } as any,
                                        });
                                        await refetchCatalog();
                                        toast.success(checked ? "Debug mode enabled" : "Debug mode disabled");
                                    } catch {
                                        toast.error("Failed to update configuration");
                                    }
                                }}
                            />
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Sync activity — only for configured */}
            {isConfigured && (
                <Card className="mb-6">
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle className="text-lg">Sync Activity</CardTitle>
                                <CardDescription>
                                    {item.last_synced_at
                                        ? `Last synced ${formatDistanceToNow(new Date(item.last_synced_at), { addSuffix: true })}`
                                        : "Never synced"
                                    }
                                </CardDescription>
                            </div>
                            <Button variant="outline" size="sm"
                                onClick={() => triggerSync.mutate({ id: integrationId! }, {
                                    onSuccess: () => {
                                        setIsSyncPolling(true);
                                        toast.info("Sync started...");
                                    },
                                    onError: () => toast.error("Failed to start sync"),
                                })}
                                disabled={triggerSync.isPending || isSyncPolling || item.sync_status === "SYNCING"}>
                                {(triggerSync.isPending || isSyncPolling || item.sync_status === "SYNCING")
                                    ? <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                                    : <RefreshCw className="h-4 w-4 mr-1" />
                                }
                                {isSyncPolling ? "Syncing..." : "Sync Now"}
                            </Button>
                        </div>
                    </CardHeader>
                    <CardContent>
                        {item.last_sync_stats && Object.keys(item.last_sync_stats).length > 0 && (
                            <div className="flex gap-4 mb-4">
                                {Object.entries(item.last_sync_stats).map(([key, value]) => (
                                    <div key={key} className="text-center">
                                        <p className="text-2xl font-semibold">{value}</p>
                                        <p className="text-xs text-muted-foreground capitalize">{key}</p>
                                    </div>
                                ))}
                            </div>
                        )}

                        {item.last_sync_error && (
                            <div className="mb-4 p-3 rounded-lg bg-destructive/10 text-sm text-destructive">
                                {item.last_sync_error}
                            </div>
                        )}

                        {syncLogsArray.length > 0 ? (
                            <div className="space-y-1">
                                <h3 className="text-sm font-medium mb-2">Recent activity</h3>
                                {syncLogsArray.slice(0, 10).map((log: any) => (
                                    <div key={log.id} className="flex items-center justify-between py-1.5 text-sm border-b last:border-0">
                                        <div className="flex items-center gap-2">
                                            {log.status === "SUCCESS"
                                                ? <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                                                : log.status === "FAILED"
                                                    ? <AlertCircle className="h-3.5 w-3.5 text-destructive" />
                                                    : <Loader2 className="h-3.5 w-3.5 text-muted-foreground animate-spin" />
                                            }
                                            <span>{log.sync_type_display || log.sync_type}</span>
                                        </div>
                                        <div className="flex items-center gap-3 text-muted-foreground">
                                            {log.records_created > 0 && <span>+{log.records_created}</span>}
                                            {log.records_updated > 0 && <span>~{log.records_updated}</span>}
                                            <span>
                                                {log.started_at
                                                    ? formatDistanceToNow(new Date(log.started_at), { addSuffix: true })
                                                    : ""
                                                }
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-sm text-muted-foreground">No sync history yet</p>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Remove — only for configured, at the bottom */}
            {isConfigured && (
                <Card>
                    <CardContent className="py-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium">Remove integration</p>
                                <p className="text-xs text-muted-foreground">
                                    Disconnect and remove sync configuration. Synced data will be preserved.
                                </p>
                            </div>
                            <AlertDialog>
                                <AlertDialogTrigger asChild>
                                    <Button variant="outline" size="sm" className="text-destructive hover:text-destructive">
                                        <Trash2 className="h-4 w-4 mr-1" /> Remove
                                    </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                    <AlertDialogHeader>
                                        <AlertDialogTitle>Remove integration?</AlertDialogTitle>
                                        <AlertDialogDescription>
                                            This will disconnect {item.name} and remove all sync configuration.
                                            Orders and data that were previously synced will not be deleted.
                                        </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                                        <AlertDialogAction
                                            onClick={() => deleteIntegration.mutate({ id: integrationId! }, {
                                                onSuccess: () => { toast.success("Integration removed"); window.history.back(); },
                                                onError: () => toast.error("Failed to remove integration"),
                                            })}
                                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                        >
                                            Remove
                                        </AlertDialogAction>
                                    </AlertDialogFooter>
                                </AlertDialogContent>
                            </AlertDialog>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
