import React from "react";
import {
    Tabs,
    TabsList,
    TabsTrigger,
    TabsContent,
} from "@/components/ui/tabs";
import {
    Card,
    CardHeader,
    CardTitle,
    CardContent,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import DocumentRenderer from "./DocumentRenderer";
// import HeatmapRenderer from "./HeatmapRenderer";

type Props = {
    modelType: string;
    modelData: any;
    documents?: any[];
    loading?: boolean;
};

export const CompositeRenderer: React.FC<Props> = ({
                                                       modelType,
                                                       modelData,
                                                       documents,
                                                       loading = false,
                                                   }) => {
    // Determine what content is available
    const isDocument = modelType === "documents";
    // Check if modelData has file property (indicating it's a selected document)
    const isSelectedDocument = Boolean(modelData?.file);
    const documentToRender = isDocument || isSelectedDocument ? modelData : documents?.[0];

    const hasFile = Boolean(documentToRender?.file);
    const hasHeatmap = Boolean(modelData?.annotations?.length);
    const hasDocuments = Boolean(documents?.length);

    // Show loading state
    if (loading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Loading...</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        <Skeleton className="h-8 w-full" />
                        <Skeleton className="h-64 w-full" />
                    </div>
                </CardContent>
            </Card>
        );
    }

    // Don't render if no content available
    if (!hasFile && !hasHeatmap && !hasDocuments) {
        return null;
    }

    // Determine default tab
    const getDefaultTab = () => {
        if (hasFile) return "document";
        if (hasHeatmap) return "heatmap";
        if (hasDocuments) return "documents";
        return "document";
    };

    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="text-lg">
                    {isDocument || isSelectedDocument ? "Document Viewer" : "Content Viewer"}
                    {isSelectedDocument && (
                        <span className="text-sm font-normal text-muted-foreground ml-2">
                            - {documentToRender?.file_name}
                        </span>
                    )}
                </CardTitle>
            </CardHeader>
            <CardContent>
                <Tabs defaultValue={getDefaultTab()} className="w-full">
                    <TabsList className="grid w-full grid-cols-3">
                        {hasFile && <TabsTrigger value="document">Document</TabsTrigger>}
                        {hasHeatmap && <TabsTrigger value="heatmap">Heatmap</TabsTrigger>}
                    </TabsList>

                    {hasFile && (
                        <TabsContent value="document" className="pt-4">
                            <DocumentRenderer modelData={documentToRender} loading={loading} />
                        </TabsContent>
                    )}

                    {hasHeatmap && (
                        <TabsContent value="heatmap" className="pt-4">
                            <div className="border rounded-lg p-4 min-h-[400px] bg-muted/20">
                                <div className="space-y-2">
                                    <p className="text-sm font-medium">
                                        Annotations: {modelData?.annotations?.length || 0}
                                    </p>
                                    <div className="text-xs text-muted-foreground italic">
                                        HeatmapRenderer component not yet implemented.
                                    </div>
                                </div>
                                {/* <HeatmapRenderer modelData={modelData} /> */}
                            </div>
                        </TabsContent>
                    )}
                </Tabs>
            </CardContent>
        </Card>
    );
};

export default CompositeRenderer;