import React from "react";

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
        return <p className="text-muted-foreground text-sm italic">No document file available.</p>;
    }

    const getFileExtension = (filename: string) => {
        return filename.split('.').pop()?.toLowerCase() || '';
    };

    const fileExtension = getFileExtension(modelData.file_name || fileUrl);

    const renderFileContent = () => {
        // Image files
        if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(fileExtension)) {
            return (
                <img 
                    src={fileUrl} 
                    alt={modelData.file_name || "Document"}
                    className="max-w-full h-auto rounded border"
                    style={{ maxHeight: '600px' }}
                />
            );
        }
        
        // Text files - fetch and display content
        if (['txt', 'csv', 'log', 'md'].includes(fileExtension)) {
            return <TextFileViewer url={fileUrl} fileName={modelData.file_name} />;
        }
        
        // PDF and other iframe-compatible files
        if (['pdf', 'html', 'htm'].includes(fileExtension)) {
            return (
                <iframe
                    src={`${fileUrl}#toolbar=0`}
                    title={modelData.file_name || "Document Viewer"}
                    className="w-full h-[600px] rounded border"
                />
            );
        }
        
        // Fallback for unsupported file types
        return (
            <div className="flex flex-col items-center justify-center h-[400px] text-center space-y-4">
                <div className="text-4xl">📄</div>
                <div className="space-y-2">
                    <p className="text-sm font-medium">Preview not available for .{fileExtension} files</p>
                    <p className="text-xs text-muted-foreground">
                        Click the download link above to view this file
                    </p>
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
                {modelData.upload_date && (
                    <p>Uploaded: {new Date(modelData.upload_date).toLocaleDateString()}</p>
                )}
            </div>

            <div className="border rounded bg-muted/10 p-3 min-h-[400px] overflow-auto">
                {renderFileContent()}
            </div>

        </div>
    );
};

// Component to handle text file viewing
const TextFileViewer: React.FC<{ url: string; fileName?: string }> = ({ url, fileName }) => {
    const [content, setContent] = React.useState<string>('');
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState<string | null>(null);

    React.useEffect(() => {
        const fetchTextContent = async () => {
            try {
                setLoading(true);
                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`Failed to fetch file: ${response.statusText}`);
                }
                const text = await response.text();
                setContent(text);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load file');
            } finally {
                setLoading(false);
            }
        };

        fetchTextContent();
    }, [url]);

    if (loading) {
        return <div className="flex items-center justify-center h-[400px]">Loading content...</div>;
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-[400px] text-center space-y-2">
                <p className="text-sm text-red-600">Error loading file: {error}</p>
                <p className="text-xs text-muted-foreground">Try opening the file directly using the link above</p>
            </div>
        );
    }

    return (
        <div className="w-full h-[600px] overflow-auto">
            <pre className="whitespace-pre-wrap font-mono text-sm p-4 bg-background rounded border">
                {content}
            </pre>
        </div>
    );
};

export default DocumentRenderer;
