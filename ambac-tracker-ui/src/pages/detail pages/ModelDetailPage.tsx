import React from 'react';
import {
    Card, CardHeader, CardTitle, CardContent, CardFooter,
} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {useNavigate} from '@tanstack/react-router';
import {useRetrieveDocuments} from '@/hooks/useRetrieveDocuments';
import {useRetrieveContentTypes} from '@/hooks/useRetrieveContentTypes';
import type {schemas} from '@/lib/api/generated';
import {z} from 'zod';

type Document = z.infer<typeof schemas.Document>;

export type FieldsConfig = {
    fields: Record<string, { label: string }>;
    customRenderers?: Record<string, (value: any) => React.ReactNode>;
    fetcher: (id: string) => Promise<any>;
};

type ModelData = {
    id: number; name?: string; documents?: Document[]; // preload optional
    [key: string]: any;
};

type ModelDetailPageProps = {
    modelData: ModelData; modelType: string; fieldsConfig: FieldsConfig;
};

const DocumentsSection: React.FC<{
    documents: Document[]; isLoading?: boolean; error?: unknown;
}> = ({documents, isLoading, error}) => {
    const navigate = useNavigate();

    if (isLoading) {
        return <p className="text-sm text-muted-foreground">Loading documents…</p>;
    }

    if (error) {
        console.log(error)
        return <p className="text-sm text-destructive">Failed to load documents.</p>;
    }

    if (!documents.length) return null;

    return (<div className="mt-6">
            <h3 className="text-xl font-semibold mb-2">Associated Documents</h3>
            <ul className="space-y-1">
                {documents.map((doc) => (<li key={doc.id}>
                        <Button
                            variant="link"
                            size="sm"
                            className="p-0 text-blue-600 hover:text-blue-800"
                            onClick={() => navigate({to: `/documents/${doc.id}`})}
                        >
                            {doc.file_name}
                        </Button>
                    </li>))}
            </ul>
        </div>);
};

const ModelDetailPage: React.FC<ModelDetailPageProps> = ({
                                                             modelData, modelType, fieldsConfig,
                                                         }) => {
    const {
        data: contentTypes, isLoading: isLoadingContentTypes, error: contentTypeError,
    } = useRetrieveContentTypes({});

    const contentTypeId = contentTypes?.results?.find((ct) => ct.model?.toLowerCase() === modelType.toLowerCase())?.id;

    const {
        data: documents,
        isLoading: isLoadingDocs,
        error: documentError,
    } = useRetrieveDocuments({
        queries: {
            object_id: modelData.id,
            content_type: contentTypeId,
        },
        enabled: !!contentTypeId && !!modelData.id,
    });


    const renderField = (field: string, value: any) => {
        const customRenderer = fieldsConfig.customRenderers?.[field];
        return customRenderer ? customRenderer(value) : value;
    };

    return (<div className="p-6 max-w-4xl mx-auto">
            <Card className="shadow-sm mb-6">
                <CardHeader>
                    <CardTitle className="text-2xl font-semibold">
                        {modelData.name || `${modelType} Detail`}
                    </CardTitle>
                </CardHeader>

                <CardContent className="space-y-4">
                    {Object.entries(fieldsConfig.fields).map(([key, config]) => key in modelData ? (
                        <div key={key} className="mb-4">
                            <strong className="text-lg text-gray-700">{config.label}:</strong>
                            <div className="text-gray-500">
                                {renderField(key, modelData[key])}
                            </div>
                        </div>) : null)}
                </CardContent>

                <CardFooter className="flex flex-col items-start">
                    <DocumentsSection
                        documents={documents?.results ?? []}
                        isLoading={isLoadingDocs || isLoadingContentTypes}
                        error={documentError || contentTypeError}
                    />
                </CardFooter>
            </Card>

            <div className="mt-4 flex justify-between">
                <Button
                    className="bg-gray-800 text-white hover:bg-gray-700"
                    onClick={() => alert('Edit functionality here!')}
                >
                    Edit
                </Button>
                <Button
                    className="bg-gray-800 text-white hover:bg-gray-700"
                    onClick={() => alert('Create functionality here!')}
                >
                    Create New
                </Button>
            </div>
        </div>);
};

export default ModelDetailPage;
