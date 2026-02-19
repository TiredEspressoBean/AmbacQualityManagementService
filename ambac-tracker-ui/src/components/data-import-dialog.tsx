"use client";

import * as React from "react";
import { toast } from "sonner";
import { FileSpreadsheet, Upload, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    FileUploader,
    FileInput,
    FileUploaderContent,
    FileUploaderItem,
} from "@/components/ui/file-upload";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

type ImportMode = "create" | "update" | "upsert";

interface ImportResult {
    row: number;
    status: "created" | "updated" | "error";
    id?: string;
    errors?: string | Record<string, string> | string[];
    warnings?: string[];
}

interface ImportResponse {
    summary: {
        total: number;
        created: number;
        updated: number;
        errors: number;
    };
    results: ImportResult[];
}

interface QueuedResponse {
    task_id: string;
    status: "queued";
    total_rows: number;
    message: string;
}

interface TaskStatusResponse {
    task_id: string;
    status: "PENDING" | "PROGRESS" | "SUCCESS" | "FAILURE";
    progress?: {
        current: number;
        total: number;
        created?: number;
        updated?: number;
        errors?: number;
    };
    result?: ImportResponse;
    error?: string;
}

interface ColumnMapping {
    original: string;
    mapped_to: string | null;
    confidence: "high" | "medium" | "none";
}

interface ModelField {
    name: string;
    display: string;
    required: boolean;
    type: string;
}

interface PreviewResponse {
    total_rows: number;
    columns: ColumnMapping[];
    sample_data: Record<string, unknown>[];
    model_fields: ModelField[];
}

interface DataImportDialogProps {
    /** Model/endpoint name for import (e.g., "parts", "orders") */
    modelName: string;
    /** Display name for the dialog title */
    displayName?: string;
    /** API base URL */
    apiBaseUrl?: string;
    /** Callback after successful import */
    onImportComplete?: (results: ImportResponse) => void;
    /** Custom trigger button */
    trigger?: React.ReactNode;
    /** Additional class name */
    className?: string;
}

export function DataImportDialog({
    modelName,
    displayName,
    apiBaseUrl = "/api",
    onImportComplete,
    trigger,
    className,
}: DataImportDialogProps) {
    const [open, setOpen] = React.useState(false);
    const [files, setFiles] = React.useState<File[] | null>(null);
    const [mode, setMode] = React.useState<ImportMode>("upsert");
    const [isImporting, setIsImporting] = React.useState(false);
    const [isLoadingPreview, setIsLoadingPreview] = React.useState(false);
    const [results, setResults] = React.useState<ImportResponse | null>(null);
    const [step, setStep] = React.useState<"upload" | "mapping" | "processing" | "results">("upload");
    const [taskId, setTaskId] = React.useState<string | null>(null);
    const [progress, setProgress] = React.useState<{ current: number; total: number } | null>(null);
    const pollIntervalRef = React.useRef<NodeJS.Timeout | null>(null);

    // Column mapping state
    const [previewData, setPreviewData] = React.useState<PreviewResponse | null>(null);
    const [columnMappings, setColumnMappings] = React.useState<Record<string, string>>({});

    const title = displayName || modelName.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

    const handleFilesChange = async (newFiles: File[] | null) => {
        setFiles(newFiles);
        setResults(null);
        setPreviewData(null);
        setColumnMappings({});

        if (newFiles && newFiles.length > 0) {
            // Load preview to get column mappings
            setIsLoadingPreview(true);
            try {
                const formData = new FormData();
                formData.append("file", newFiles[0]);

                const response = await fetch(`${apiBaseUrl}/${modelName}/import-preview/`, {
                    method: "POST",
                    body: formData,
                    credentials: "include",
                });

                if (!response.ok) {
                    throw new Error("Failed to preview file");
                }

                const data: PreviewResponse = await response.json();
                setPreviewData(data);

                // Initialize column mappings from auto-detected values
                const initialMappings: Record<string, string> = {};
                data.columns.forEach((col) => {
                    if (col.mapped_to) {
                        initialMappings[col.original] = col.mapped_to;
                    }
                });
                setColumnMappings(initialMappings);

                setStep("mapping");
            } catch (error) {
                console.error("Preview error:", error);
                toast.error("Failed to preview file. Please check the format.");
                setStep("upload");
            } finally {
                setIsLoadingPreview(false);
            }
        } else {
            setStep("upload");
        }
    };

    const pollTaskStatus = React.useCallback(async (id: string) => {
        try {
            const response = await fetch(
                `${apiBaseUrl}/${modelName}/import-status/${id}/`,
                { credentials: "include" }
            );
            const data: TaskStatusResponse = await response.json();

            if (data.status === "PROGRESS" && data.progress) {
                setProgress({ current: data.progress.current, total: data.progress.total });
            } else if (data.status === "SUCCESS" && data.result) {
                // Task completed
                if (pollIntervalRef.current) {
                    clearInterval(pollIntervalRef.current);
                    pollIntervalRef.current = null;
                }
                setResults(data.result);
                setStep("results");
                setIsImporting(false);
                setTaskId(null);

                if (data.result.summary.errors === 0) {
                    toast.success(
                        `Import complete: ${data.result.summary.created} created, ${data.result.summary.updated} updated`
                    );
                } else {
                    toast.warning(
                        `Import completed with errors: ${data.result.summary.created} created, ${data.result.summary.updated} updated, ${data.result.summary.errors} errors`
                    );
                }

                onImportComplete?.(data.result);
            } else if (data.status === "FAILURE") {
                // Task failed
                if (pollIntervalRef.current) {
                    clearInterval(pollIntervalRef.current);
                    pollIntervalRef.current = null;
                }
                setIsImporting(false);
                setTaskId(null);
                toast.error(data.error || "Import failed");
            }
        } catch (error) {
            console.error("Error polling task status:", error);
        }
    }, [apiBaseUrl, modelName, onImportComplete]);

    // Cleanup polling on unmount
    React.useEffect(() => {
        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
            }
        };
    }, []);

    const handleImport = async () => {
        if (!files || files.length === 0) {
            toast.error("Please select a file to import");
            return;
        }

        setIsImporting(true);
        setResults(null);
        setProgress(null);

        try {
            const formData = new FormData();
            formData.append("file", files[0]);
            formData.append("mode", mode);

            // Send custom column mappings if any were modified
            if (Object.keys(columnMappings).length > 0) {
                formData.append("column_mapping", JSON.stringify(columnMappings));
            }

            const response = await fetch(`${apiBaseUrl}/${modelName}/import/`, {
                method: "POST",
                body: formData,
                credentials: "include",
            });

            // Check if it's a queued response (202) or immediate (207)
            if (response.status === 202) {
                // Large import - queued for background processing
                const data: QueuedResponse = await response.json();
                setTaskId(data.task_id);
                setProgress({ current: 0, total: data.total_rows });
                setStep("processing");
                toast.info(`Processing ${data.total_rows} rows in background...`);

                // Start polling for status
                pollIntervalRef.current = setInterval(() => {
                    pollTaskStatus(data.task_id);
                }, 2000); // Poll every 2 seconds
            } else {
                // Small import - immediate results
                const data: ImportResponse = await response.json();
                setResults(data);
                setStep("results");
                setIsImporting(false);

                if (data.summary.errors === 0) {
                    toast.success(
                        `Import complete: ${data.summary.created} created, ${data.summary.updated} updated`
                    );
                } else {
                    toast.warning(
                        `Import completed with errors: ${data.summary.created} created, ${data.summary.updated} updated, ${data.summary.errors} errors`
                    );
                }

                onImportComplete?.(data);
            }
        } catch (error) {
            toast.error("Import failed. Please check the file format and try again.");
            console.error("Import error:", error);
            setIsImporting(false);
        }
    };

    const handleDownloadTemplate = async (format: "csv" | "xlsx") => {
        try {
            const response = await fetch(
                `${apiBaseUrl}/${modelName}/import-template/?format=${format}`,
                { credentials: "include" }
            );

            if (!response.ok) {
                throw new Error("Failed to download template");
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${modelName}_import_template.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (error) {
            toast.error("Failed to download template");
            console.error("Template download error:", error);
        }
    };

    const handleReset = () => {
        if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
        }
        setFiles(null);
        setResults(null);
        setStep("upload");
        setTaskId(null);
        setProgress(null);
        setIsImporting(false);
        setPreviewData(null);
        setColumnMappings({});
    };

    const handleMappingChange = (originalColumn: string, targetField: string) => {
        setColumnMappings((prev) => ({
            ...prev,
            [originalColumn]: targetField,
        }));
    };

    const getConfidenceIcon = (confidence: string) => {
        switch (confidence) {
            case "high":
                return <CheckCircle2 className="h-4 w-4 text-green-500" />;
            case "medium":
                return <AlertCircle className="h-4 w-4 text-yellow-500" />;
            default:
                return <XCircle className="h-4 w-4 text-red-500" />;
        }
    };

    const handleClose = () => {
        setOpen(false);
        // Reset state after dialog closes
        setTimeout(() => {
            handleReset();
        }, 200);
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                {trigger || (
                    <Button variant="outline" size="sm" className={className}>
                        <Upload className="mr-2 h-4 w-4" />
                        Import
                    </Button>
                )}
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>Import {title}</DialogTitle>
                    <DialogDescription>
                        Upload a CSV or Excel file to import data.
                    </DialogDescription>
                </DialogHeader>

                {step === "upload" && (
                    <div className="space-y-4">
                        {/* Template download buttons */}
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <span>Download template:</span>
                            <Button
                                variant="link"
                                size="sm"
                                className="h-auto p-0"
                                onClick={() => handleDownloadTemplate("xlsx")}
                            >
                                Excel (.xlsx)
                            </Button>
                            <span>|</span>
                            <Button
                                variant="link"
                                size="sm"
                                className="h-auto p-0"
                                onClick={() => handleDownloadTemplate("csv")}
                            >
                                CSV
                            </Button>
                        </div>

                        {/* File upload dropzone */}
                        <FileUploader
                            value={files}
                            onValueChange={handleFilesChange}
                            dropzoneOptions={{
                                accept: {
                                    "text/csv": [".csv"],
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                                    "application/vnd.ms-excel": [".xls"],
                                },
                                maxFiles: 1,
                                maxSize: 10 * 1024 * 1024, // 10MB
                            }}
                            className="relative bg-background rounded-lg p-2"
                        >
                            <FileInput className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg">
                                <div className="flex flex-col items-center justify-center p-8 text-center">
                                    <FileSpreadsheet className="h-10 w-10 text-muted-foreground mb-4" />
                                    <p className="text-sm font-medium">
                                        Drag & drop your file here
                                    </p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        or click to browse (.csv, .xlsx, .xls)
                                    </p>
                                </div>
                            </FileInput>
                            <FileUploaderContent>
                                {files?.map((file, index) => (
                                    <FileUploaderItem key={index} index={index}>
                                        <FileSpreadsheet className="h-4 w-4" />
                                        <span className="truncate">{file.name}</span>
                                        <span className="text-xs text-muted-foreground">
                                            ({(file.size / 1024).toFixed(1)} KB)
                                        </span>
                                    </FileUploaderItem>
                                ))}
                            </FileUploaderContent>
                        </FileUploader>
                    </div>
                )}

                {isLoadingPreview && (
                    <div className="flex flex-col items-center justify-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4" />
                        <p className="text-sm text-muted-foreground">Analyzing file...</p>
                    </div>
                )}

                {step === "mapping" && previewData && files && files.length > 0 && (
                    <div className="space-y-4">
                        {/* Selected file info */}
                        <div className="flex items-center gap-3 p-3 bg-muted rounded-lg">
                            <FileSpreadsheet className="h-8 w-8 text-primary" />
                            <div className="flex-1 min-w-0">
                                <p className="font-medium truncate">{files[0].name}</p>
                                <p className="text-sm text-muted-foreground">
                                    {previewData.total_rows} rows detected
                                </p>
                            </div>
                            <Button variant="ghost" size="sm" onClick={handleReset}>
                                Change
                            </Button>
                        </div>

                        {/* Column mapping */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Column Mapping</label>
                            <div className="border rounded-lg divide-y max-h-[200px] overflow-y-auto">
                                {previewData.columns.map((col) => (
                                    <div key={col.original} className="flex items-center gap-2 p-2 text-sm">
                                        <div className="flex items-center gap-1 w-1/3 min-w-0">
                                            {getConfidenceIcon(col.confidence)}
                                            <span className="truncate" title={col.original}>
                                                {col.original}
                                            </span>
                                        </div>
                                        <span className="text-muted-foreground">→</span>
                                        <Select
                                            value={columnMappings[col.original] || "_skip_"}
                                            onValueChange={(v) => handleMappingChange(col.original, v)}
                                        >
                                            <SelectTrigger className="flex-1 h-8">
                                                <SelectValue placeholder="Skip column" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="_skip_">
                                                    <span className="text-muted-foreground italic">Skip column</span>
                                                </SelectItem>
                                                {previewData.model_fields.map((field) => (
                                                    <SelectItem key={field.name} value={field.name}>
                                                        {field.display}
                                                        {field.required && <span className="text-red-500 ml-1">*</span>}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                ))}
                            </div>
                            <p className="text-xs text-muted-foreground">
                                <CheckCircle2 className="h-3 w-3 text-green-500 inline mr-1" />
                                Auto-mapped
                                <AlertCircle className="h-3 w-3 text-yellow-500 inline mx-1 ml-3" />
                                Possible match
                                <XCircle className="h-3 w-3 text-red-500 inline mx-1 ml-3" />
                                Not mapped
                            </p>
                        </div>

                        {/* Import mode selection */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Import Mode</label>
                            <Select value={mode} onValueChange={(v) => setMode(v as ImportMode)}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="upsert">
                                        <div>
                                            <div className="font-medium">Create or Update (Recommended)</div>
                                            <div className="text-xs text-muted-foreground">
                                                Creates new records, updates existing ones
                                            </div>
                                        </div>
                                    </SelectItem>
                                    <SelectItem value="create">
                                        <div>
                                            <div className="font-medium">Create Only</div>
                                            <div className="text-xs text-muted-foreground">
                                                Only create new records, error if exists
                                            </div>
                                        </div>
                                    </SelectItem>
                                    <SelectItem value="update">
                                        <div>
                                            <div className="font-medium">Update Only</div>
                                            <div className="text-xs text-muted-foreground">
                                                Only update existing records, error if not found
                                            </div>
                                        </div>
                                    </SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                )}

                {step === "processing" && (
                    <div className="space-y-4">
                        <div className="flex flex-col items-center justify-center py-8">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4" />
                            <p className="text-lg font-medium">Processing Import...</p>
                            {progress && (
                                <>
                                    <p className="text-sm text-muted-foreground mt-2">
                                        {progress.current} of {progress.total} rows
                                    </p>
                                    <div className="w-full max-w-xs mt-4">
                                        <Progress
                                            value={progress.total > 0 ? (progress.current / progress.total) * 100 : 0}
                                        />
                                    </div>
                                </>
                            )}
                            {taskId && (
                                <p className="text-xs text-muted-foreground mt-4">
                                    Task ID: {taskId}
                                </p>
                            )}
                        </div>
                    </div>
                )}

                {step === "results" && results && (
                    <div className="space-y-4">
                        {/* Summary */}
                        <div className="grid grid-cols-4 gap-2">
                            <SummaryCard
                                label="Total"
                                value={results.summary.total}
                                variant="default"
                            />
                            <SummaryCard
                                label="Created"
                                value={results.summary.created}
                                variant="success"
                            />
                            <SummaryCard
                                label="Updated"
                                value={results.summary.updated}
                                variant="info"
                            />
                            <SummaryCard
                                label="Errors"
                                value={results.summary.errors}
                                variant="error"
                            />
                        </div>

                        {/* Progress bar */}
                        <div className="space-y-1">
                            <div className="flex justify-between text-xs text-muted-foreground">
                                <span>Import Progress</span>
                                <span>
                                    {results.summary.created + results.summary.updated} /{" "}
                                    {results.summary.total} successful
                                </span>
                            </div>
                            <Progress
                                value={
                                    ((results.summary.created + results.summary.updated) /
                                        results.summary.total) *
                                    100
                                }
                            />
                        </div>

                        {/* Results list (show errors first) */}
                        {results.summary.errors > 0 && (
                            <div className="space-y-2">
                                <p className="text-sm font-medium">Errors</p>
                                <div className="max-h-48 overflow-y-auto space-y-1">
                                    {results.results
                                        .filter((r) => r.status === "error")
                                        .slice(0, 20)
                                        .map((result) => (
                                            <ResultRow key={result.row} result={result} />
                                        ))}
                                    {results.results.filter((r) => r.status === "error").length >
                                        20 && (
                                        <p className="text-xs text-muted-foreground">
                                            ... and{" "}
                                            {results.results.filter((r) => r.status === "error")
                                                .length - 20}{" "}
                                            more errors
                                        </p>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                <DialogFooter>
                    {step === "upload" && (
                        <Button variant="outline" onClick={handleClose}>
                            Cancel
                        </Button>
                    )}
                    {step === "mapping" && (
                        <>
                            <Button variant="outline" onClick={handleReset}>
                                Back
                            </Button>
                            <Button onClick={handleImport} disabled={isImporting}>
                                {isImporting ? "Importing..." : `Import ${previewData?.total_rows || 0} Rows`}
                            </Button>
                        </>
                    )}
                    {step === "processing" && (
                        <p className="text-sm text-muted-foreground">
                            Processing in background. You can close this dialog.
                        </p>
                    )}
                    {step === "results" && (
                        <>
                            <Button variant="outline" onClick={handleReset}>
                                Import Another
                            </Button>
                            <Button onClick={handleClose}>Done</Button>
                        </>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function SummaryCard({
    label,
    value,
    variant,
}: {
    label: string;
    value: number;
    variant: "default" | "success" | "info" | "error";
}) {
    const variantStyles = {
        default: "bg-muted",
        success: "bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300",
        info: "bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300",
        error: "bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300",
    };

    return (
        <div className={cn("rounded-lg p-2 text-center", variantStyles[variant])}>
            <div className="text-xl font-bold">{value}</div>
            <div className="text-xs">{label}</div>
        </div>
    );
}

function ResultRow({ result }: { result: ImportResult }) {
    const getIcon = () => {
        switch (result.status) {
            case "created":
                return <CheckCircle2 className="h-4 w-4 text-green-500" />;
            case "updated":
                return <AlertCircle className="h-4 w-4 text-blue-500" />;
            case "error":
                return <XCircle className="h-4 w-4 text-red-500" />;
        }
    };

    const getErrorMessage = () => {
        if (!result.errors) return null;
        if (typeof result.errors === "string") return result.errors;
        if (Array.isArray(result.errors)) return result.errors.join(", ");
        return Object.entries(result.errors)
            .map(([field, msg]) => `${field}: ${msg}`)
            .join(", ");
    };

    return (
        <div className="flex items-start gap-2 p-2 bg-muted/50 rounded text-sm">
            {getIcon()}
            <div className="flex-1 min-w-0">
                <span className="font-medium">Row {result.row}</span>
                {result.status === "error" && (
                    <p className="text-xs text-red-600 dark:text-red-400 truncate">
                        {getErrorMessage()}
                    </p>
                )}
                {result.warnings && result.warnings.length > 0 && (
                    <p className="text-xs text-amber-600 dark:text-amber-400 truncate">
                        Warnings: {result.warnings.join(", ")}
                    </p>
                )}
            </div>
        </div>
    );
}
