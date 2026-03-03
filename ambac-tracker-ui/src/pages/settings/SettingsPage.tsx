import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useTenantContext } from "@/components/tenant-provider";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
    Building2,
    Palette,
    Users,
    Shield,
    Bell,
    Link2,
    CreditCard,
    Settings2,
    ChevronRight,
    RefreshCw,
    Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

type SettingsCard = {
    title: string;
    description: string;
    icon: React.ElementType;
    href: string;
    badge?: string;
    disabled?: boolean;
    requiresAdmin?: boolean;
    saasOnly?: boolean;
};

const settingsCards: SettingsCard[] = [
    {
        title: "Organization",
        description: "Company name, contact info, and general settings",
        icon: Building2,
        href: "/settings/organization",
        requiresAdmin: true,
    },
    {
        title: "Branding",
        description: "Logo, colors, and visual identity",
        icon: Palette,
        href: "/settings/branding",
        requiresAdmin: true,
    },
    {
        title: "Billing & Plans",
        description: "Subscription, invoices, and payment methods",
        icon: CreditCard,
        href: "/settings/billing",
        requiresAdmin: true,
        saasOnly: true,
    },
    {
        title: "Users & Groups",
        description: "Manage team members and permissions",
        icon: Users,
        href: "/editor/users",
    },
    {
        title: "Roles & Permissions",
        description: "Configure access control and roles",
        icon: Shield,
        href: "/editor/groups",
        requiresAdmin: true,
    },
    {
        title: "Notifications",
        description: "Email and in-app notification preferences",
        icon: Bell,
        href: "/profile",
    },
    {
        title: "Integrations",
        description: "Connect external services and APIs",
        icon: Link2,
        href: "/settings/integrations",
        badge: "Coming Soon",
        disabled: true,
    },
];

function SettingsCardSkeleton() {
    return (
        <Card className="h-full">
            <CardHeader className="pb-3">
                <div className="flex items-start gap-3">
                    <Skeleton className="h-10 w-10 rounded-lg" />
                    <div className="flex-1 space-y-2">
                        <Skeleton className="h-5 w-32" />
                        <Skeleton className="h-4 w-48" />
                    </div>
                </div>
            </CardHeader>
        </Card>
    );
}

function DemoResetCard() {
    const [isResetting, setIsResetting] = useState(false);
    const [dialogOpen, setDialogOpen] = useState(false);
    const handleReset = async () => {
        setIsResetting(true);
        try {
            const response = await fetch("/api/tenant/demo-reset/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "include",
                body: JSON.stringify({ scale: "small" }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "Reset failed");
            }

            const data = await response.json();
            toast.success(data.message || "Data has been reset successfully.");
            setDialogOpen(false);
            // Reload the page to reflect new data
            window.location.reload();
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "An error occurred");
        } finally {
            setIsResetting(false);
        }
    };

    return (
        <Card className="border-amber-200 bg-amber-50/50 dark:border-amber-900 dark:bg-amber-950/20">
            <CardHeader className="pb-3">
                <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-900/50">
                        <RefreshCw className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <CardTitle className="text-base">Reset Demo Data</CardTitle>
                            <Badge variant="outline" className="text-xs border-amber-300 text-amber-700 dark:border-amber-700 dark:text-amber-400">
                                Demo Only
                            </Badge>
                        </div>
                        <CardDescription className="text-sm mt-1">
                            Reset all data to a fresh demo state for training
                        </CardDescription>
                    </div>
                    <AlertDialog open={dialogOpen} onOpenChange={setDialogOpen}>
                        <AlertDialogTrigger asChild>
                            <Button
                                variant="outline"
                                size="sm"
                                className="border-amber-300 hover:bg-amber-100 dark:border-amber-700 dark:hover:bg-amber-900/50"
                                disabled={isResetting}
                            >
                                {isResetting ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    "Reset"
                                )}
                            </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                            <AlertDialogHeader>
                                <AlertDialogTitle>Reset Demo Data?</AlertDialogTitle>
                                <AlertDialogDescription>
                                    This will delete all current data and replace it with fresh demo data.
                                    This action cannot be undone.
                                </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                                <AlertDialogCancel disabled={isResetting}>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                    onClick={handleReset}
                                    disabled={isResetting}
                                    className="bg-amber-600 hover:bg-amber-700"
                                >
                                    {isResetting ? (
                                        <>
                                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                            Resetting...
                                        </>
                                    ) : (
                                        "Reset Data"
                                    )}
                                </AlertDialogAction>
                            </AlertDialogFooter>
                        </AlertDialogContent>
                    </AlertDialog>
                </div>
            </CardHeader>
        </Card>
    );
}

function SettingsCardItem({ card }: { card: SettingsCard }) {
    const Icon = card.icon;

    const content = (
        <Card className={cn(
            "h-full transition-all",
            card.disabled
                ? "opacity-60 cursor-not-allowed"
                : "hover:border-primary/50 hover:shadow-sm cursor-pointer"
        )}>
            <CardHeader className="pb-3">
                <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                        <Icon className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <CardTitle className="text-base">{card.title}</CardTitle>
                            {card.badge && (
                                <Badge variant="secondary" className="text-xs">
                                    {card.badge}
                                </Badge>
                            )}
                        </div>
                        <CardDescription className="text-sm mt-1">
                            {card.description}
                        </CardDescription>
                    </div>
                    {!card.disabled && (
                        <ChevronRight className="h-5 w-5 text-muted-foreground shrink-0" />
                    )}
                </div>
            </CardHeader>
        </Card>
    );

    if (card.disabled) {
        return content;
    }

    return (
        <Link to={card.href} className="block">
            {content}
        </Link>
    );
}

export function SettingsPage() {
    const { tenant, isLoading, isDemo, isSaas } = useTenantContext();

    // Filter cards based on deployment mode
    const visibleCards = settingsCards.filter((card) => {
        if (card.saasOnly && !isSaas) return false;
        return true;
    });

    return (
        <div className="container mx-auto p-6 max-w-4xl">
            {/* Header */}
            <div className="mb-8">
                <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                        <Settings2 className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold">Settings</h1>
                        <p className="text-muted-foreground">
                            {isLoading ? (
                                <Skeleton className="h-4 w-48 mt-1" />
                            ) : (
                                <>Manage settings for {tenant?.name || "your organization"}</>
                            )}
                        </p>
                    </div>
                    {isDemo && (
                        <Badge variant="outline" className="ml-auto">
                            Demo Mode
                        </Badge>
                    )}
                </div>
            </div>

            {/* Tenant Info Card */}
            {!isLoading && tenant && (
                <Card className="mb-6 bg-muted/30">
                    <CardContent className="pt-6">
                        <div className="flex items-center gap-4">
                            {tenant.logo_url ? (
                                <img
                                    src={tenant.logo_url}
                                    alt={tenant.name}
                                    className="h-12 w-12 rounded-lg object-contain"
                                />
                            ) : (
                                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-lg">
                                    {tenant.name.charAt(0).toUpperCase()}
                                </div>
                            )}
                            <div className="flex-1">
                                <p className="font-medium">{tenant.name}</p>
                                <p className="text-sm text-muted-foreground">
                                    {tenant.slug}.yourapp.com
                                </p>
                            </div>
                            <div className="flex gap-2">
                                <Badge variant="outline">{tenant.tier}</Badge>
                                <Badge
                                    variant={tenant.status === "active" ? "default" : "secondary"}
                                >
                                    {tenant.status}
                                </Badge>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Settings Cards Grid */}
            <div className="grid gap-4 sm:grid-cols-2">
                {isLoading ? (
                    <>
                        <SettingsCardSkeleton />
                        <SettingsCardSkeleton />
                        <SettingsCardSkeleton />
                        <SettingsCardSkeleton />
                    </>
                ) : (
                    visibleCards.map((card) => (
                        <SettingsCardItem key={card.title} card={card} />
                    ))
                )}
            </div>

            {/* Demo Reset - only visible in demo mode */}
            {!isLoading && isDemo && (
                <div className="mt-8">
                    <h2 className="text-lg font-semibold mb-4">Demo Tools</h2>
                    <DemoResetCard />
                </div>
            )}
        </div>
    );
}
