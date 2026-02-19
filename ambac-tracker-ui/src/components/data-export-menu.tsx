"use client";

import * as React from "react";
import { toast } from "sonner";
import { Download, FileSpreadsheet, FileText, FileDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type ExportFormat = "xlsx" | "csv";

interface DataExportMenuProps {
    /** Model/endpoint name for export (e.g., "parts", "orders") */
    modelName: string;
    /** API base URL */
    apiBaseUrl?: string;
    /** Current filter/search query params to include in export */
    queryParams?: Record<string, string | number | boolean | undefined>;
    /** Specific fields to export (comma-separated) */
    fields?: string[];
    /** Custom filename (without extension) */
    filename?: string;
    /** Whether template download is available */
    showTemplateOption?: boolean;
    /** Custom trigger button */
    trigger?: React.ReactNode;
    /** Button variant */
    variant?: "default" | "outline" | "ghost" | "secondary";
    /** Button size */
    size?: "default" | "sm" | "lg" | "icon";
    /** Additional class name */
    className?: string;
}

export function DataExportMenu({
    modelName,
    apiBaseUrl = "/api",
    queryParams,
    fields,
    filename,
    showTemplateOption = true,
    trigger,
    variant = "outline",
    size = "sm",
    className,
}: DataExportMenuProps) {
    const [isExporting, setIsExporting] = React.useState(false);

    const buildUrl = (
        endpoint: "export" | "import-template",
        format: ExportFormat
    ): string => {
        const url = new URL(`${apiBaseUrl}/${modelName}/${endpoint}/`, window.location.origin);
        url.searchParams.set("format", format);

        if (fields && fields.length > 0) {
            url.searchParams.set("fields", fields.join(","));
        }

        if (filename) {
            url.searchParams.set("filename", filename);
        }

        // Add any active filters/search to export
        if (queryParams) {
            Object.entries(queryParams).forEach(([key, value]) => {
                if (value !== undefined && value !== null && value !== "") {
                    url.searchParams.set(key, String(value));
                }
            });
        }

        return url.toString();
    };

    const handleExport = async (format: ExportFormat) => {
        setIsExporting(true);

        try {
            const url = buildUrl("export", format);
            const response = await fetch(url, { credentials: "include" });

            if (!response.ok) {
                throw new Error(`Export failed: ${response.statusText}`);
            }

            // Get filename from Content-Disposition header if available
            const contentDisposition = response.headers.get("Content-Disposition");
            let downloadFilename = `${modelName}_export.${format}`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                if (filenameMatch) {
                    downloadFilename = filenameMatch[1];
                }
            }

            const blob = await response.blob();
            downloadBlob(blob, downloadFilename);

            toast.success(`Exported to ${format.toUpperCase()}`);
        } catch (error) {
            console.error("Export error:", error);
            toast.error("Export failed. Please try again.");
        } finally {
            setIsExporting(false);
        }
    };

    const handleDownloadTemplate = async (format: ExportFormat) => {
        try {
            const url = buildUrl("import-template", format);
            const response = await fetch(url, { credentials: "include" });

            if (!response.ok) {
                throw new Error(`Template download failed: ${response.statusText}`);
            }

            const blob = await response.blob();
            downloadBlob(blob, `${modelName}_import_template.${format}`);

            toast.success("Template downloaded");
        } catch (error) {
            console.error("Template download error:", error);
            toast.error("Failed to download template");
        }
    };

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                {trigger || (
                    <Button
                        variant={variant}
                        size={size}
                        className={className}
                        disabled={isExporting}
                    >
                        <Download className="mr-2 h-4 w-4" />
                        {isExporting ? "Exporting..." : "Export"}
                    </Button>
                )}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel>Export Data</DropdownMenuLabel>
                <DropdownMenuItem onClick={() => handleExport("xlsx")}>
                    <FileSpreadsheet className="mr-2 h-4 w-4 text-green-600" />
                    Export as Excel
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport("csv")}>
                    <FileText className="mr-2 h-4 w-4 text-blue-600" />
                    Export as CSV
                </DropdownMenuItem>

                {showTemplateOption && (
                    <>
                        <DropdownMenuSeparator />
                        <DropdownMenuLabel>Import Template</DropdownMenuLabel>
                        <DropdownMenuItem onClick={() => handleDownloadTemplate("xlsx")}>
                            <FileDown className="mr-2 h-4 w-4 text-green-600" />
                            Excel Template
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleDownloadTemplate("csv")}>
                            <FileDown className="mr-2 h-4 w-4 text-blue-600" />
                            CSV Template
                        </DropdownMenuItem>
                    </>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}

/**
 * Simplified export button for quick exports without menu
 */
interface QuickExportButtonProps {
    /** Model/endpoint name for export */
    modelName: string;
    /** Export format */
    format?: ExportFormat;
    /** API base URL */
    apiBaseUrl?: string;
    /** Current filter/search query params */
    queryParams?: Record<string, string | number | boolean | undefined>;
    /** Custom filename */
    filename?: string;
    /** Button variant */
    variant?: "default" | "outline" | "ghost" | "secondary";
    /** Button size */
    size?: "default" | "sm" | "lg" | "icon";
    /** Additional class name */
    className?: string;
    /** Children (button text) */
    children?: React.ReactNode;
}

export function QuickExportButton({
    modelName,
    format = "xlsx",
    apiBaseUrl = "/api",
    queryParams,
    filename,
    variant = "outline",
    size = "sm",
    className,
    children,
}: QuickExportButtonProps) {
    const [isExporting, setIsExporting] = React.useState(false);

    const handleExport = async () => {
        setIsExporting(true);

        try {
            const url = new URL(`${apiBaseUrl}/${modelName}/export/`, window.location.origin);
            url.searchParams.set("format", format);

            if (filename) {
                url.searchParams.set("filename", filename);
            }

            if (queryParams) {
                Object.entries(queryParams).forEach(([key, value]) => {
                    if (value !== undefined && value !== null && value !== "") {
                        url.searchParams.set(key, String(value));
                    }
                });
            }

            const response = await fetch(url.toString(), { credentials: "include" });

            if (!response.ok) {
                throw new Error(`Export failed: ${response.statusText}`);
            }

            const blob = await response.blob();
            downloadBlob(blob, `${filename || modelName}_export.${format}`);

            toast.success("Export complete");
        } catch (error) {
            console.error("Export error:", error);
            toast.error("Export failed");
        } finally {
            setIsExporting(false);
        }
    };

    return (
        <Button
            variant={variant}
            size={size}
            className={className}
            onClick={handleExport}
            disabled={isExporting}
        >
            {isExporting ? (
                "Exporting..."
            ) : (
                children || (
                    <>
                        <Download className="mr-2 h-4 w-4" />
                        Export
                    </>
                )
            )}
        </Button>
    );
}

// Utility function to trigger file download
function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
