import React from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

/**
 * PDF.js worker
 * Using CDN since bundled path has issues with Vite resolution
 */
pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;

// Bundled approach (commented out due to path resolution issues):
// pdfjs.GlobalWorkerOptions.workerSrc = new URL(
//     "pdfjs-dist/build/pdf.worker.min.mjs",
//     import.meta.url
// ).toString();

// NOTE: Do NOT set pdfjs.GlobalWorkerOptions.verbosity — it doesn't exist.
// Keep verbosity in <Document options> if desired.

type Props = {
    modelData: {
        file: string;
        file_name?: string;
        upload_date?: string;
    };
    loading?: boolean;
};

const DocumentRenderer: React.FC<Props> = ({ modelData, loading = false }) => {
    const fileUrl = modelData?.file;

    if (loading) {
        return <p className="text-muted-foreground text-sm">Loading document...</p>;
    }

    if (!fileUrl) {
        return (
            <p className="text-muted-foreground text-sm italic">No document file available.</p>
        );
    }

    const getFileExtension = (filename: string) => {
        return filename.split(".").pop()?.toLowerCase() || "";
    };

    // Use URL pathname for extension detection to ignore query strings
    let pathname = "";
    try {
        const u = new URL(modelData.file, window.location.origin);
        pathname = u.pathname;
    } catch {
        pathname = modelData.file;
    }
    const fileExtension = getFileExtension(modelData.file_name ?? pathname);

    const renderFileContent = () => {
        // Images
        if (["jpg", "jpeg", "png", "gif", "bmp", "webp", "svg"].includes(fileExtension)) {
            return <ImageViewer url={fileUrl} fileName={modelData.file_name} />;
        }

        // Text-like
        if (["txt", "csv", "log", "md"].includes(fileExtension)) {
            return <TextFileViewer url={fileUrl} fileName={modelData.file_name} />;
        }

        // PDFs
        if (["pdf"].includes(fileExtension)) {
            return <PDFViewer url={fileUrl} fileName={modelData.file_name} />;
        }

        // HTML
        if (["html", "htm"].includes(fileExtension)) {
            return (
                <iframe
                    src={`${fileUrl}#toolbar=0`}
                    title={modelData.file_name || "Document Viewer"}
                    className="w-full h-[600px] rounded border"
                />
            );
        }

        // Fallback
        return (
            <div className="flex flex-col items-center justify-center h-[400px] text-center space-y-4">
                <div className="text-4xl">📄</div>
                <div className="space-y-2">
                    <p className="text-sm font-medium">Preview not available for .{fileExtension} files</p>
                    <p className="text-xs text-muted-foreground">Click the download link above to view this file</p>
                </div>
            </div>
        );
    };

    return (
        <div className="space-y-4">
            <div className="text-sm text-muted-foreground">
                <p>
                    <span className="font-medium">File:</span>{" "}
                    <a href={fileUrl} target="_blank" rel="noopener noreferrer" className="text-primary underline">
                        {modelData.file_name || fileUrl}
                    </a>
                </p>
                {modelData.upload_date && <p>Uploaded: {new Date(modelData.upload_date).toLocaleDateString()}</p>}
            </div>

            <div className="border rounded bg-muted/10 p-3 min-h-[400px] overflow-auto">{renderFileContent()}</div>
        </div>
    );
};

// Text viewer
const TextFileViewer: React.FC<{ url: string; fileName?: string }> = ({ url }) => {
    const [content, setContent] = React.useState<string>("");
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState<string | null>(null);

    React.useEffect(() => {
        let aborted = false;
        (async () => {
            try {
                setLoading(true);
                const response = await fetch(url);
                if (!response.ok) throw new Error(`Failed to fetch file: ${response.status} ${response.statusText}`);
                const text = await response.text();
                if (!aborted) setContent(text);
            } catch (err) {
                if (!aborted) setError(err instanceof Error ? err.message : "Failed to load file");
            } finally {
                if (!aborted) setLoading(false);
            }
        })();
        return () => {
            aborted = true;
        };
    }, [url]);

    if (loading) return <div className="flex items-center justify-center h-[400px]">Loading content...</div>;
    if (error)
        return (
            <div className="flex flex-col items-center justify-center h-[400px] text-center space-y-2">
                <p className="text-sm text-red-600">Error loading file: {error}</p>
                <p className="text-xs text-muted-foreground">Try opening the file directly using the link above</p>
            </div>
        );

    return (
        <div className="w-full h-[600px] overflow-auto">
            <pre className="whitespace-pre-wrap font-mono text-sm p-4 bg-background rounded border">{content}</pre>
        </div>
    );
};

// Image viewer
const ImageViewer: React.FC<{ url: string; fileName?: string }> = ({ url, fileName }) => {
    const [isLightboxOpen, setIsLightboxOpen] = React.useState(false);
    const [imageLoaded, setImageLoaded] = React.useState(false);
    const [error, setError] = React.useState<string | null>(null);
    const [imageSrc, setImageSrc] = React.useState<string | null>(null);
    const [loading, setLoading] = React.useState(true);

    const openLightbox = () => setIsLightboxOpen(true);
    const closeLightbox = () => setIsLightboxOpen(false);

    // Fetch image and create object URL to bypass ORB (Opaque Response Blocking)
    React.useEffect(() => {
        let aborted = false;
        let objectUrl: string | null = null;

        (async () => {
            try {
                setLoading(true);
                setError(null);

                const response = await fetch(url);
                if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

                const blob = await response.blob();
                if (aborted) return;

                objectUrl = URL.createObjectURL(blob);
                setImageSrc(objectUrl);
                setLoading(false);
            } catch (e: any) {
                if (!aborted) {
                    setError(`Failed to load image: ${e.message}`);
                    setLoading(false);
                }
            }
        })();

        return () => {
            aborted = true;
            // Clean up the object URL to prevent memory leaks
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
            }
        };
    }, [url]);

    // Handle ESC key to close lightbox
    React.useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape' && isLightboxOpen) {
                closeLightbox();
            }
        };

        if (isLightboxOpen) {
            document.addEventListener('keydown', handleKeyDown);
            document.body.style.overflow = 'hidden';
        }

        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.body.style.overflow = 'unset';
        };
    }, [isLightboxOpen]);

    const handleImageLoad = () => setImageLoaded(true);
    const handleImageError = () => setError('Failed to display image');

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[400px]">
                <div className="text-center space-y-2">
                    <div className="text-4xl">🖼️</div>
                    <p className="text-sm">Loading image...</p>
                </div>
            </div>
        );
    }

    if (error || !imageSrc) {
        return (
            <div className="flex flex-col items-center justify-center h-[400px] text-center space-y-2">
                <div className="text-4xl">🖼️</div>
                <p className="text-sm text-red-600">{error || 'Failed to load image'}</p>
                <p className="text-xs text-muted-foreground">Try opening the file directly using the link above</p>
            </div>
        );
    }

    return (
        <>
            <div className="relative">
                <img
                    src={imageSrc}
                    alt={fileName || "Document"}
                    className="max-w-full h-auto rounded border cursor-pointer hover:opacity-90 transition-opacity"
                    style={{ maxHeight: "600px" }}
                    onClick={openLightbox}
                    onLoad={handleImageLoad}
                    onError={handleImageError}
                />

                <button
                    onClick={openLightbox}
                    className="absolute top-2 right-2 px-2 py-1 bg-black/70 text-white rounded text-xs hover:bg-black/80 transition-colors"
                    title="Click to expand"
                >
                    🔍 Expand
                </button>
            </div>

            {/* Lightbox */}
            {isLightboxOpen && (
                <div
                    className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
                    onClick={closeLightbox}
                >
                    <div
                        className="relative max-w-[95vw] max-h-[95vh] flex flex-col"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Lightbox Controls */}
                        <div className="bg-gray-900 text-white shadow-lg px-4 py-2 flex items-center justify-between rounded-t-lg">
                            <div className="flex items-center space-x-2">
                                <span className="text-sm font-medium text-gray-200 truncate max-w-[300px]">
                                    {fileName || 'Image'}
                                </span>
                            </div>

                            <div className="flex items-center space-x-2">
                                <a
                                    href={url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm"
                                    title="Open in new tab"
                                >
                                    Open in New Tab
                                </a>
                                <button
                                    onClick={closeLightbox}
                                    className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-sm"
                                    title="Close lightbox (ESC)"
                                >
                                    ✕ Close
                                </button>
                            </div>
                        </div>

                        {/* Lightbox Image Content */}
                        <div className="bg-gray-100 rounded-b-lg p-4 flex items-center justify-center min-h-[400px] overflow-auto">
                            <img
                                src={imageSrc}
                                alt={fileName || "Document"}
                                className="max-w-full max-h-full object-contain shadow-xl rounded"
                                style={{ maxHeight: "85vh" }}
                            />
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};

// PDF viewer
const PDFViewer: React.FC<{ url: string; fileName?: string }> = ({ url }) => {
    const [numPages, setNumPages] = React.useState<number | null>(null);
    const [pageNumber, setPageNumber] = React.useState(1);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState<string | null>(null);
    const [pdfSrc, setPdfSrc] = React.useState<string | null>(null);
    const [scale, setScale] = React.useState(1.0);

    React.useEffect(() => {
        let aborted = false;
        let objectUrl: string | null = null;

        (async () => {
            try {
                setLoading(true);
                setError(null);

                const response = await fetch(url);
                if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

                const blob = await response.blob();
                if (aborted) return;

                objectUrl = URL.createObjectURL(blob);
                setPdfSrc(objectUrl);
                setLoading(false);
            } catch (e: any) {
                if (!aborted) {
                    setError(`Failed to fetch PDF: ${e.message}`);
                    setLoading(false);
                }
            }
        })();

        return () => {
            aborted = true;
            // Clean up the object URL to prevent memory leaks
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
            }
        };
    }, [url]);

    // Memoize options to prevent "options changed but equal" warning
    const pdfOptions = React.useMemo(() => ({
        cMapUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
        cMapPacked: true,
        standardFontDataUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/standard_fonts/`,
        verbosity: pdfjs.VerbosityLevel.INFOS,
        enableXfa: false,
        disableAutoFetch: false,
        disableStream: false,
        disableFontFace: false,
    }), []);

    const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
        setNumPages(numPages);
    };

    const onDocumentLoadError = (err: Error) => {
        console.error('PDF load error:', err);
        setError(`Failed to load PDF: ${err.message}`);
    };

    const goToPreviousPage = () => setPageNumber((prev) => Math.max(prev - 1, 1));
    const goToNextPage = () => setPageNumber((prev) => Math.min(prev + 1, numPages || 1));

    const zoomIn = () => setScale((prev) => Math.min(prev + 0.25, 3.0));
    const zoomOut = () => setScale((prev) => Math.max(prev - 0.25, 0.5));
    const resetZoom = () => setScale(1.0);

    const [isLightboxOpen, setIsLightboxOpen] = React.useState(false);
    const openLightbox = () => setIsLightboxOpen(true);
    const closeLightbox = () => setIsLightboxOpen(false);

    // Handle ESC key to close lightbox
    React.useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape' && isLightboxOpen) {
                closeLightbox();
            }
        };

        if (isLightboxOpen) {
            document.addEventListener('keydown', handleKeyDown);
            // Prevent body scroll when lightbox is open
            document.body.style.overflow = 'hidden';
        }

        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.body.style.overflow = 'unset';
        };
    }, [isLightboxOpen]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[600px]">
                <div className="text-center space-y-2">
                    <div className="text-4xl">📄</div>
                    <p className="text-sm">Loading PDF...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-[600px] text-center space-y-4">
                <div className="text-4xl">📄</div>
                <div className="space-y-2">
                    <p className="text-sm text-red-600">Failed to load PDF</p>
                    <p className="text-xs text-muted-foreground">{error}</p>
                    <div className="space-y-2 pt-2">
                        <a
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-block px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 text-sm"
                        >
                            Open PDF in New Tab
                        </a>
                        <p className="text-xs text-muted-foreground">Click above to view the PDF directly</p>
                    </div>
                </div>
            </div>
        );
    }

    if (!pdfSrc) {
        return (
            <div className="flex items-center justify-center h-[600px]">
                <div className="text-center space-y-2">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                    <p className="text-sm">Preparing PDF...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Controls */}
            <div className="flex items-center justify-between bg-muted/50 p-3 rounded">
                <div className="flex items-center space-x-4">
                    <button
                        onClick={goToPreviousPage}
                        disabled={pageNumber <= 1}
                        className="px-3 py-1 bg-primary text-primary-foreground rounded disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    >
                        Previous
                    </button>
                    <span className="text-sm">
                        Page {pageNumber} of {numPages || '?'}
                    </span>
                    <button
                        onClick={goToNextPage}
                        disabled={pageNumber >= (numPages || 1)}
                        className="px-3 py-1 bg-primary text-primary-foreground rounded disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    >
                        Next
                    </button>
                </div>

                <div className="flex items-center space-x-2">
                    <div className="flex items-center space-x-1">
                        <button
                            onClick={zoomOut}
                            disabled={scale <= 0.5}
                            className="px-2 py-1 bg-secondary text-secondary-foreground rounded disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                            title="Zoom out"
                        >
                            −
                        </button>
                        <span className="text-xs px-2 py-1 bg-background rounded border min-w-[3rem] text-center">
                            {Math.round(scale * 100)}%
                        </span>
                        <button
                            onClick={zoomIn}
                            disabled={scale >= 3.0}
                            className="px-2 py-1 bg-secondary text-secondary-foreground rounded disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                            title="Zoom in"
                        >
                            +
                        </button>
                        <button
                            onClick={resetZoom}
                            className="px-2 py-1 bg-secondary text-secondary-foreground rounded hover:bg-secondary/80 text-xs"
                            title="Reset zoom"
                        >
                            Reset
                        </button>
                    </div>

                    <button
                        onClick={openLightbox}
                        className="px-3 py-1 bg-secondary text-secondary-foreground rounded hover:bg-secondary/80 text-sm"
                        title="View in lightbox"
                    >
                        🔍 Expand
                    </button>

                    <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1 bg-secondary text-secondary-foreground rounded hover:bg-secondary/80 text-sm"
                    >
                        Open in New Tab
                    </a>
                </div>
            </div>

            {/* PDF */}
            <div className="flex justify-center bg-muted/10 p-4 rounded min-h-[600px] overflow-auto">
                <Document
                    file={pdfSrc}
                    onLoadSuccess={onDocumentLoadSuccess}
                    onLoadError={onDocumentLoadError}
                    options={pdfOptions}
                    loading={
                        <div className="flex items-center justify-center h-[500px]">
                            <div className="text-center space-y-2">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                                <p className="text-sm">Rendering PDF...</p>
                            </div>
                        </div>
                    }
                >
                    <Page
                        pageNumber={pageNumber}
                        renderTextLayer
                        renderAnnotationLayer
                        className="shadow-lg cursor-pointer"
                        scale={scale}
                        onClick={openLightbox}
                    />
                </Document>
            </div>

            {/* Lightbox */}
            {isLightboxOpen && (
                <div
                    className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
                    onClick={closeLightbox}
                >
                    <div
                        className="relative bg-white rounded-lg max-w-[95vw] max-h-[95vh] overflow-auto"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Lightbox Controls */}
                        <div className="sticky top-0 z-10 bg-gray-900 text-white shadow-lg p-3 flex items-center justify-between flex-wrap gap-2">
                            <div className="flex items-center space-x-4">
                                <button
                                    onClick={goToPreviousPage}
                                    disabled={pageNumber <= 1}
                                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                                >
                                    Previous
                                </button>
                                <span className="text-sm font-medium text-gray-200">
                                    Page {pageNumber} of {numPages || '?'}
                                </span>
                                <button
                                    onClick={goToNextPage}
                                    disabled={pageNumber >= (numPages || 1)}
                                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                                >
                                    Next
                                </button>
                            </div>

                            <div className="flex items-center space-x-2">
                                <div className="flex items-center space-x-1">
                                    <button
                                        onClick={zoomOut}
                                        disabled={scale <= 0.5}
                                        className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                                        title="Zoom out"
                                    >
                                        −
                                    </button>
                                    <span className="text-xs px-2 py-1 bg-gray-800 text-gray-200 rounded border border-gray-600 min-w-[3rem] text-center">
                                        {Math.round(scale * 100)}%
                                    </span>
                                    <button
                                        onClick={zoomIn}
                                        disabled={scale >= 3.0}
                                        className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                                        title="Zoom in"
                                    >
                                        +
                                    </button>
                                    <button
                                        onClick={resetZoom}
                                        className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded text-xs"
                                        title="Reset zoom"
                                    >
                                        Reset
                                    </button>
                                </div>

                                <button
                                    onClick={closeLightbox}
                                    className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-sm"
                                    title="Close lightbox (ESC)"
                                >
                                    ✕ Close
                                </button>
                            </div>
                        </div>

                        {/* Lightbox PDF Content */}
                        <div className="p-6 flex justify-center bg-gray-50 min-h-[600px]">
                            {pdfSrc && (
                                <Document
                                    file={pdfSrc}
                                    onLoadSuccess={onDocumentLoadSuccess}
                                    onLoadError={onDocumentLoadError}
                                    options={pdfOptions}
                                    loading={
                                        <div className="flex items-center justify-center h-[500px]">
                                            <div className="text-center space-y-2">
                                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-600 mx-auto"></div>
                                                <p className="text-sm text-gray-600">Loading PDF...</p>
                                            </div>
                                        </div>
                                    }
                                >
                                    <Page
                                        pageNumber={pageNumber}
                                        renderTextLayer
                                        renderAnnotationLayer
                                        className="shadow-xl border border-gray-300"
                                        scale={Math.max(scale, 1.2)} // Minimum 120% in lightbox
                                    />
                                </Document>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DocumentRenderer;

