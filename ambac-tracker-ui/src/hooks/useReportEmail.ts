import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

/**
 * Report type — registry key validated server-side against the
 * Tracker.reports adapter registry. Use useReportTypes() to enumerate
 * available reports.
 */
export type ReportType = string;

/**
 * Parameters for generating a report.
 */
export interface ReportParams {
    [key: string]: unknown;
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
            const data = await api.api_reports_generate_create(
                { report_type: reportType, params },
                { headers: { "X-CSRFToken": getCookie("csrftoken") || "" } }
            );

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
            // eslint-disable-next-line no-restricted-syntax -- Binary blob download requires raw fetch for Content-Disposition header access and blob handling
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
 * // reportTypes = [{ name: "spc", title: "SPC Report", template: "spc.typ" }, ...]
 * ```
 */
export function useReportTypes() {
    return useQuery({
        queryKey: ["reportTypes"],
        queryFn: () => api.api_reports_types_retrieve(),
        staleTime: 60 * 60 * 1000, // Cache for 1 hour - report types rarely change
    });
}
