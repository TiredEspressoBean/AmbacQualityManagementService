import { Link } from "@tanstack/react-router";
import { AlertTriangle, Clock, X } from "lucide-react";
import { useState } from "react";
import { useTenantContext } from "./tenant-provider";
import { Button } from "./ui/button";

/**
 * Calculate days remaining until a date
 */
function getDaysRemaining(dateString: string): number {
    const endDate = new Date(dateString);
    const now = new Date();
    const diffMs = endDate.getTime() - now.getTime();
    return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

/**
 * Banner that shows when tenant is in trial status.
 * Shows different states:
 * - Trial expired (status = 'trial' but trial_ends_at is past)
 * - Trial expiring soon (< 7 days)
 * - Trial active (> 7 days, dismissible)
 */
export function TrialBanner() {
    const { tenant, isSaas } = useTenantContext();
    const [dismissed, setDismissed] = useState(false);

    // Only show for SaaS deployments in trial status
    if (!isSaas || !tenant || tenant.status !== "trial" || dismissed) {
        return null;
    }

    const trialEndsAt = tenant.trial_ends_at;
    if (!trialEndsAt) {
        return null;
    }

    const daysRemaining = getDaysRemaining(trialEndsAt);
    const isExpired = daysRemaining <= 0;
    const isUrgent = daysRemaining <= 3;
    const isWarning = daysRemaining <= 7;

    // Expired - can't dismiss, must upgrade
    if (isExpired) {
        return (
            <div className="bg-destructive text-destructive-foreground px-4 py-3">
                <div className="container mx-auto flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <AlertTriangle className="h-5 w-5 flex-shrink-0" />
                        <p className="text-sm font-medium">
                            Your trial has expired. Upgrade now to continue using all features.
                        </p>
                    </div>
                    <Button
                        asChild
                        size="sm"
                        variant="secondary"
                        className="flex-shrink-0"
                    >
                        <Link to="/settings/billing">Upgrade Now</Link>
                    </Button>
                </div>
            </div>
        );
    }

    // Urgent (1-3 days) - can't dismiss
    if (isUrgent) {
        return (
            <div className="bg-destructive text-destructive-foreground px-4 py-2.5">
                <div className="container mx-auto flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <AlertTriangle className="h-5 w-5 flex-shrink-0" />
                        <p className="text-sm font-medium">
                            Your trial expires in {daysRemaining} day{daysRemaining !== 1 ? "s" : ""}.
                            Upgrade to keep your data and access.
                        </p>
                    </div>
                    <Button
                        asChild
                        size="sm"
                        variant="secondary"
                        className="flex-shrink-0"
                    >
                        <Link to="/settings/billing">Upgrade Now</Link>
                    </Button>
                </div>
            </div>
        );
    }

    // Warning (4-7 days) - dismissible
    if (isWarning) {
        return (
            <div className="bg-amber-500 text-white px-4 py-2.5">
                <div className="container mx-auto flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <Clock className="h-5 w-5 flex-shrink-0" />
                        <p className="text-sm font-medium">
                            Your trial expires in {daysRemaining} days. Upgrade to unlock all features.
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            asChild
                            size="sm"
                            variant="secondary"
                            className="flex-shrink-0"
                        >
                            <Link to="/settings/billing">View Plans</Link>
                        </Button>
                        <Button
                            size="sm"
                            variant="ghost"
                            className="flex-shrink-0 hover:bg-amber-600"
                            onClick={() => setDismissed(true)}
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </div>
        );
    }

    // Normal trial (> 7 days) - subtle, dismissible
    return (
        <div className="bg-primary/10 text-foreground px-4 py-2">
            <div className="container mx-auto flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                    <Clock className="h-4 w-4 flex-shrink-0 text-primary" />
                    <p className="text-sm">
                        <span className="font-medium">Free trial</span>
                        <span className="text-muted-foreground"> · {daysRemaining} days remaining</span>
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        asChild
                        size="sm"
                        variant="outline"
                        className="flex-shrink-0 h-7 text-xs"
                    >
                        <Link to="/settings/billing">View Plans</Link>
                    </Button>
                    <Button
                        size="sm"
                        variant="ghost"
                        className="flex-shrink-0 h-7 w-7 p-0"
                        onClick={() => setDismissed(true)}
                    >
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            </div>
        </div>
    );
}
