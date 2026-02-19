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
