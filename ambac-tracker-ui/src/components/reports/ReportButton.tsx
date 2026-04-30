import * as React from "react";
import { Download, FileText, Loader2, Mail } from "lucide-react";

import { Button, type buttonVariants } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useReportEmail, type ReportParams, type ReportType } from "@/hooks/useReportEmail";
import { cn } from "@/lib/utils";
import type { VariantProps } from "class-variance-authority";

type ButtonVariantProps = VariantProps<typeof buttonVariants>;

export type ReportButtonProps = {
    /** Registry key of the report (validated server-side against the adapter registry). */
    reportType: ReportType;
    /** Adapter-specific parameters. The button is disabled when this is null. */
    params: ReportParams | null;
    /** Visible label. Defaults to "Report". */
    label?: string;
    /** Override the icon shown next to the label. */
    icon?: React.ReactNode;
    /** Hide the "Email me" entry — use for reports that should not be emailed. */
    allowEmail?: boolean;
    /** Hide the "Download" entry — rare; included for symmetry. */
    allowDownload?: boolean;
    /** Forwarded to the trigger Button. */
    variant?: ButtonVariantProps["variant"];
    size?: ButtonVariantProps["size"];
    className?: string;
    /** Forwarded to the trigger Button. The button is also disabled when params is null or a request is in flight. */
    disabled?: boolean;
};

/**
 * ReportButton — reusable PDF report trigger for any registered backend adapter.
 *
 * Wraps the shadcn `Button` + `DropdownMenu` primitives and the
 * `useReportEmail` hook. Surfaces two actions:
 *   1. "Download" — synchronous PDF stream via /api/reports/download/
 *   2. "Email me" — async generation + email via /api/reports/generate/
 *
 * Drop into any page that has the params for a given report type.
 *
 * @example
 *   <ReportButton
 *     reportType="spc"
 *     label="SPC Report"
 *     params={selectedMeasurementId ? { measurement_id: selectedMeasurementId, days: 90, mode: "xbar-r" } : null}
 *   />
 */
export function ReportButton({
    reportType,
    params,
    label = "Report",
    icon,
    allowEmail = true,
    allowDownload = true,
    variant = "outline",
    size = "sm",
    className,
    disabled = false,
}: ReportButtonProps) {
    const { requestReport, downloadReport, isRequesting } = useReportEmail();

    const isDisabled = disabled || isRequesting || params === null;

    const handleDownload = () => {
        if (params) void downloadReport(reportType, params);
    };
    const handleEmail = () => {
        if (params) void requestReport(reportType, params);
    };

    const triggerIcon = icon ?? (
        isRequesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />
    );

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button
                    variant={variant}
                    size={size}
                    disabled={isDisabled}
                    className={cn(className)}
                >
                    {triggerIcon}
                    {label}
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel>Get report</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {allowDownload && (
                    <DropdownMenuItem onSelect={handleDownload} disabled={isDisabled}>
                        <Download className="h-4 w-4" />
                        Download PDF
                    </DropdownMenuItem>
                )}
                {allowEmail && (
                    <DropdownMenuItem onSelect={handleEmail} disabled={isDisabled}>
                        <Mail className="h-4 w-4" />
                        Email me
                    </DropdownMenuItem>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}