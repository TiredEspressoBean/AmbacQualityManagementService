import { useState } from "react";
import { toast } from "sonner";
import { getCookie } from "@/lib/utils";

/**
 * Report types supported by the PDF generation system.
 */
export type ReportType = "spc" | "capa" | "quality_report";

/**
 * Parameters for generating a report.
 */
export interface ReportParams {
    [key: string]: unknown;
}

/**
 * Response from the report generation endpoint.
 */
interface GenerateReportResponse {
    message: string;
    task_id: string;
}

/**
 * Hook for requesting PDF report generation and email delivery.
 *
 * This hook provides a simple interface for requesting any type of report.
 * Reports are generated server-side using Playwright and emailed to the user.
 *
 * @example
 * ```tsx
 * const { requestReport, downloadReport, isRequesting } = useReportEmail();
 *
 * // Email an SPC report
 * const handleEmailReport = () => {
 *     requestReport("spc", {
 *         processId: 1,
 *         stepId: 101,
 *         measurementId: 1001,
 *         mode: "xbar-r"
 *     });
 * };
 *
 * // Download an SPC report directly
 * const handleDownloadReport = () => {
 *     downloadReport("spc", {
 *         processId: 1,
 *         stepId: 101,
 *         measurementId: 1001,
 *         mode: "xbar-r"
 *     });
 * };
 * ```
 */
export function useReportEmail() {
    const [isRequesting, setIsRequesting] = useState(false);

    /**
     * Request a report to be generated and emailed.
     *
     * @param reportType - Type of report (spc, capa, quality_report)
     * @param params - Parameters specific to the report type
     * @returns Promise that resolves when the request is accepted
     */
    const requestReport = async (
        reportType: ReportType,
        params: ReportParams
    ): Promise<void> => {
        setIsRequesting(true);
        try {
            const response = await fetch("/api/reports/generate/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken") || "",
                },
                body: JSON.stringify({
                    report_type: reportType,
                    params,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || "Failed to request report");
            }

            const data: GenerateReportResponse = await response.json();

            toast.success(
                data.message || "Report is being generated. Check your email shortly!"
            );
        } catch (error) {
            const message =
                error instanceof Error ? error.message : "Failed to request report";
            toast.error(message);
            throw error;
        } finally {
            setIsRequesting(false);
        }
    };

    /**
     * Download a report directly to device (synchronous).
     *
     * @param reportType - Type of report (spc, capa, quality_report)
     * @param params - Parameters specific to the report type
     * @returns Promise that resolves when download starts
     */
    const downloadReport = async (
        reportType: ReportType,
        params: ReportParams
    ): Promise<void> => {
        setIsRequesting(true);
        try {
            const response = await fetch("/api/reports/download/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken") || "",
                },
                body: JSON.stringify({
                    report_type: reportType,
                    params,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || "Failed to generate report");
            }

            // Get filename from Content-Disposition header
            const contentDisposition = response.headers.get("Content-Disposition");
            let filename = `${reportType}_report.pdf`;
            if (contentDisposition) {
                const match = contentDisposition.match(/filename="(.+)"/);
                if (match) filename = match[1];
            }

            // Download the PDF
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            toast.success("Report downloaded!");
        } catch (error) {
            const message =
                error instanceof Error ? error.message : "Failed to download report";
            toast.error(message);
            throw error;
        } finally {
            setIsRequesting(false);
        }
    };

    return { requestReport, downloadReport, isRequesting };
}

/**
 * Get available report types and their configurations.
 *
 * @example
 * ```tsx
 * const { data: reportTypes, isLoading } = useReportTypes();
 * // reportTypes = { spc: { title: "SPC Report", route: "/spc/print" }, ... }
 * ```
 */
export function useReportTypes() {
    const [isLoading, setIsLoading] = useState(false);
    const [data, setData] = useState<Record<string, { title: string; route: string }> | null>(null);
    const [error, setError] = useState<Error | null>(null);

    const fetchTypes = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch("/api/reports/types/", {
                headers: {
                    "X-CSRFToken": getCookie("csrftoken") || "",
                },
            });

            if (!response.ok) {
                throw new Error("Failed to fetch report types");
            }

            const types = await response.json();
            setData(types);
        } catch (err) {
            setError(err instanceof Error ? err : new Error("Unknown error"));
        } finally {
            setIsLoading(false);
        }
    };

    return { data, isLoading, error, fetchTypes };
}
