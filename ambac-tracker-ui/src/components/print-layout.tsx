/**
 * PrintLayout - Wrapper for all Playwright-rendered print pages (documents).
 *
 * HOW TO CREATE A NEW PRINT PAGE:
 * ================================
 * 1. Create a new component (e.g., CocPrintPage.tsx)
 * 2. Wrap content in <PrintLayout title="..." subtitle="...">
 * 3. Content automatically gets the data-print-ready attribute (Playwright waits for this)
 * 4. Fetch all data via existing API hooks - page must be self-contained
 * 5. Add route in router.tsx
 * 6. Add matching config in pdf_generator.py REPORT_CONFIG
 *
 * AVAILABLE CSS CLASSES:
 * - .page-break-before  — force page break before element
 * - .page-break-after   — force page break after element
 * - .no-break           — prevent page break inside element
 * - Cards and grid children automatically avoid page breaks
 *
 * FOR LABELS (do NOT use PrintLayout):
 * - Use a bare div with data-print-ready attribute
 * - Set page size via @page CSS in the component, or use config page override
 * - For sheet layout (e.g., 30-up Avery 5160), use CSS grid on Letter @page
 * - For individual labels (thermal printers), set exact page dimensions in config
 *
 * FOR DOCUMENTS (use PrintLayout):
 * - Always use PrintLayout for consistent header/timestamp
 * - Use .no-break on table rows and card components
 * - For chart-heavy pages, set needs_scroll: true and a chart-specific
 *   wait_selector in REPORT_CONFIG (e.g., ".recharts-surface")
 *
 * DARK MODE:
 * - PrintLayout auto-forces light mode - no action needed
 * - All CSS variables are overridden for print readability
 */
import { useEffect, type ReactNode } from "react";

interface PrintLayoutProps {
    children: ReactNode;
    title?: string;
    subtitle?: string;
}

export function PrintLayout({ children, title, subtitle }: PrintLayoutProps) {
    // Force light mode for print pages
    useEffect(() => {
        document.documentElement.classList.remove("dark");
        document.documentElement.classList.add("light");
        document.documentElement.style.colorScheme = "light";
    }, []);

    return (
        <div className="print-layout light bg-white text-black p-8">
            {title && (
                <header className="mb-6 border-b border-gray-300 pb-4">
                    <h1 className="text-2xl font-bold text-black">{title}</h1>
                    {subtitle && (
                        <p className="text-lg text-gray-600 mt-1">{subtitle}</p>
                    )}
                    <p className="text-sm text-gray-500 mt-2">
                        Generated: {new Date().toLocaleString()}
                    </p>
                </header>
            )}
            <main data-print-ready>{children}</main>
            <style>{`
                /* Force document to flow naturally for PDF generation */
                html, body, #root {
                    height: auto !important;
                    min-height: auto !important;
                    max-height: none !important;
                    overflow: visible !important;
                }
                @media print {
                    .print-layout { padding: 0; }
                    @page {
                        margin: 0.5in;
                        size: letter;
                    }
                }
                /* Force light mode colors */
                .print-layout, .print-layout * {
                    --background: 0 0% 100%;
                    --foreground: 222.2 84% 4.9%;
                    --card: 0 0% 100%;
                    --card-foreground: 222.2 84% 4.9%;
                    --muted: 210 40% 96%;
                    --muted-foreground: 215.4 16.3% 46.9%;
                    --border: 214.3 31.8% 91.4%;
                }
                /* Auto-pagination: prevent cards from splitting across pages */
                .print-layout [data-slot="card"],
                .print-layout .card,
                .print-layout [class*="Card"] {
                    page-break-inside: avoid;
                    break-inside: avoid;
                }
                /* Page break utilities for manual control */
                .page-break-before { page-break-before: always; break-before: page; }
                .page-break-after { page-break-after: always; break-after: page; }
                .no-break { page-break-inside: avoid; break-inside: avoid; }
                /* Keep grid rows together */
                .print-layout .grid > * {
                    page-break-inside: avoid;
                    break-inside: avoid;
                }
            `}</style>
        </div>
    );
}
