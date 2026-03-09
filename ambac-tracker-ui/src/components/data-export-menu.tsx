"use client";

import * as React from "react";
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
import { useExport } from "@/hooks/useExport";
import { useImportTemplate } from "@/hooks/useImportTemplate";

type ExportFormat = "xlsx" | "csv";

interface DataExportMenuProps {
    /** Model/endpoint name for export (e.g., "Parts", "Orders") */
    modelName: string;
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
    queryParams,
    fields,
    filename,
    showTemplateOption = true,
    trigger,
    variant = "outline",
    size = "sm",
    className,
}: DataExportMenuProps) {
    const { mutate: exportData, isPending: isExporting } = useExport(modelName);
    const { mutate: downloadTemplate } = useImportTemplate(modelName);

    const handleExport = (format: ExportFormat) => {
        exportData({
            format,
            fields: fields?.join(","),
            filename,
            queries: queryParams,
        });
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
                        <DropdownMenuItem onClick={() => downloadTemplate("xlsx")}>
                            <FileDown className="mr-2 h-4 w-4 text-green-600" />
                            Excel Template
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => downloadTemplate("csv")}>
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
    queryParams,
    filename,
    variant = "outline",
    size = "sm",
    className,
    children,
}: QuickExportButtonProps) {
    const { mutate: exportData, isPending: isExporting } = useExport(modelName);

    const handleExport = () => {
        exportData({
            format,
            filename,
            queries: queryParams,
        });
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
