import { useParams } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import ModelDetailPage from './ModelDetailPage';
import { getFieldsConfigForModel } from './fieldsConfigMap';
import { CompositeRenderer } from "@/pages/detail pages/RendererSidebarComponent";

const getDetailComponentsForModel = (modelType: string) => {
    switch (modelType.toLowerCase()) {
        case 'parts':
            return {
                RendererSidebarComponent: CompositeRenderer,
            };
        case 'documents':
            return {
                RendererSidebarComponent: CompositeRenderer,
            };
        default:
            return {};
    }
};

const ModelDetailPageWrapper = () => {
    const { model, id } = useParams({ from: '/details/$model/$id' });
    const modelType = model;

    const fieldsConfig = getFieldsConfigForModel(modelType);
    const componentOverrides = getDetailComponentsForModel(modelType);

    const {
        data: modelData,
        isLoading,
        error,
    } = useQuery({
        queryKey: [modelType, id],
        queryFn: () => fieldsConfig.fetcher(id),
        enabled: !!model && !!id,
    });

    if (isLoading) return <div className="p-6">Loading...</div>;
    if (error || !modelData) return <div className="p-6 text-red-600">Failed to load data.</div>;

    return (
        <ModelDetailPage
            modelData={modelData}
            modelType={modelType}
            fieldsConfig={fieldsConfig}
            {...componentOverrides}
        />
    );
};

export default ModelDetailPageWrapper;