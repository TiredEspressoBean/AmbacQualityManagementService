import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ThreeDModelViewer, type ModelBounds } from "@/components/three-d-model-viewer";
import { AnnotationPoint } from "@/components/annotation-point";
import { AnnotationsList } from "@/components/annotations-list";
import { useRetrieveHeatMapAnnotations } from "@/hooks/useRetrieveHeatMapAnnotations";
import { useUpdateHeatMapAnnotation } from "@/hooks/useUpdateHeatMapAnnotation";
import { useHeatMapFacets } from "@/hooks/useHeatMapFacets";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import {
    Loader2,
    AlertTriangle,
    Maximize,
    Minimize,
    Box,
    Layers,
    ArrowLeft,
    FileWarning,
    ChevronRight,
    Check,
    ChevronsUpDown,
    Search,
    Pencil,
    Save,
    X,
} from "lucide-react";
import * as THREE from "three";
import { api } from "@/lib/api/generated";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { useGLTF } from "@react-three/drei";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command";
import { cn } from "@/lib/utils";

// Helper to normalize media URLs to relative paths (for Vite proxy to work)
function normalizeMediaUrl(url: string | undefined | null): string | undefined {
    if (!url) return undefined;
    try {
        const parsed = new URL(url, window.location.origin);
        // If it's a media URL, return just the path (relative)
        if (parsed.pathname.startsWith('/media/')) {
            return parsed.pathname;
        }
        // If it's already relative or different, return as-is
        return url;
    } catch {
        // If URL parsing fails, return as-is
        return url;
    }
}

interface HeatMapViewerProps {
    // Primary context - optional, shows selection UI if not provided
    partTypeId?: string;
    partId?: string;

    // Step context - determines which model to use
    stepId?: string;

    // Filters
    errorTypes?: string[];
    severities?: string[];
    dateRange?: { start: string; end: string };
    workOrderIds?: string[];

    // UI options
    showStatistics?: boolean;
    allowFiltering?: boolean;
    className?: string;
    showHeader?: boolean;
}

// Part type card with prefetching
function PartTypeCard({
    partType,
    onSelect,
    onHover,
}: {
    partType: { id: string; name: string; modelCount: number };
    onSelect: () => void;
    onHover: () => void;
}) {
    return (
        <Card
            className="cursor-pointer hover:bg-accent transition-colors"
            onClick={onSelect}
            onMouseEnter={onHover}
        >
            <CardContent className="p-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h3 className="font-medium">{partType.name}</h3>
                        <p className="text-sm text-muted-foreground">
                            {partType.modelCount} model{partType.modelCount !== 1 ? 's' : ''}
                        </p>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </div>
            </CardContent>
        </Card>
    );
}

// Selection interface component
function HeatMapSelection({
    onSelectPartType,
    onSelectPart,
}: {
    onSelectPartType: (id: string) => void;
    onSelectPart: (id: string) => void;
}) {
    const queryClient = useQueryClient();
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedPartTypeForPart, setSelectedPartTypeForPart] = useState<string | null>(null);
    const [selectedPartId, setSelectedPartId] = useState<string | null>(null);
    const [rawPartTypeSearch, setRawPartTypeSearch] = useState("");
    const [partTypeSearch, setPartTypeSearch] = useState("");
    const [rawPartSearch, setRawPartSearch] = useState("");
    const [partSearch, setPartSearch] = useState("");
    const [partTypeOpen, setPartTypeOpen] = useState(false);
    const [partOpen, setPartOpen] = useState(false);

    // Debounce part type search
    useEffect(() => {
        const timer = setTimeout(() => {
            setPartTypeSearch(rawPartTypeSearch);
        }, 300);
        return () => clearTimeout(timer);
    }, [rawPartTypeSearch]);

    // Debounce part search
    useEffect(() => {
        const timer = setTimeout(() => {
            setPartSearch(rawPartSearch);
        }, 300);
        return () => clearTimeout(timer);
    }, [rawPartSearch]);

    // Fetch all 3D models to find part types with models
    const { data: modelsData, isLoading: isLoadingModels } = useQuery({
        queryKey: ["three-d-models-all"],
        queryFn: () => api.api_ThreeDModels_list({ queries: { limit: 1000 } }),
    });

    // Fetch all annotations for stats (background)
    const { data: annotationsData } = useQuery({
        queryKey: ["heatmap-annotations-all"],
        queryFn: () => api.api_HeatMapAnnotation_list({ queries: { limit: 10000 } }),
    });

    // Fetch part types with search for combobox (using lightweight select endpoint)
    const { data: partTypesSearchData } = useQuery({
        queryKey: ["part-types-select", partTypeSearch],
        queryFn: () => api.api_PartTypes_select_list({ queries: { search: partTypeSearch } }),
        enabled: partTypeOpen,
    });

    // Fetch parts with search for combobox (using lightweight select endpoint)
    const { data: partsData, isLoading: isLoadingParts } = useQuery({
        queryKey: ["parts-select", selectedPartTypeForPart, partSearch],
        queryFn: () => api.api_Parts_select_list({
            queries: {
                part_type: selectedPartTypeForPart!,
                search: partSearch,
            }
        }),
        enabled: !!selectedPartTypeForPart && partOpen,
    });

    // Group models by part type and calculate stats
    const partTypesWithModels = useMemo(() => {
        const map = new Map<string, { id: string; name: string; modelCount: number; firstModelId?: string; firstModelUrl?: string }>();
        modelsData?.results?.forEach((model) => {
            if (model.part_type) {
                const existing = map.get(model.part_type);
                if (existing) {
                    existing.modelCount++;
                } else {
                    map.set(model.part_type, {
                        id: model.part_type,
                        name: model.part_type_display || `Part Type ${model.part_type}`,
                        modelCount: 1,
                        firstModelId: model.id,
                        firstModelUrl: normalizeMediaUrl(model.file), // Normalize to relative URL for Vite proxy
                    });
                }
            }
        });
        return map;
    }, [modelsData]);

    const partTypesList = Array.from(partTypesWithModels.values());

    // Calculate overall stats
    const totalModels = modelsData?.results?.length || 0;
    const totalAnnotations = annotationsData?.results?.length || 0;
    const totalPartTypes = partTypesList.length;

    // Filter part types by search
    const filteredPartTypes = partTypesList.filter((pt) =>
        pt.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    // Prefetch data when hovering over a part type
    const prefetchPartTypeData = useCallback((partTypeId: string) => {
        const partType = partTypesWithModels.get(partTypeId);
        if (!partType) return;

        // Prefetch the actual 3D model file (this is the heavy asset!)
        if (partType.firstModelUrl) {
            useGLTF.preload(partType.firstModelUrl);
        }

        // Prefetch models metadata for this part type
        queryClient.prefetchQuery({
            queryKey: ["models", partTypeId],
            queryFn: () => api.api_ThreeDModels_list({ queries: { part_type: partTypeId } }),
        });

        // Prefetch error types
        queryClient.prefetchQuery({
            queryKey: ["error-types", { queries: { part_type: partTypeId } }],
            queryFn: () => api.api_Error_types_list({ queries: { part_type: partTypeId } }),
        });

        // Prefetch annotations if we have a model ID
        if (partType.firstModelId) {
            queryClient.prefetchQuery({
                queryKey: ["heatmap-annotations", { model: partType.firstModelId }],
                queryFn: () => api.api_HeatMapAnnotation_list({ queries: { model: partType.firstModelId } }),
            });
        }
    }, [queryClient, partTypesWithModels]);

    const handleViewPartHeatmap = () => {
        if (selectedPartId) {
            onSelectPart(selectedPartId);
        }
    };

    // Get display names for comboboxes
    const selectedPartTypeName = partTypesList.find(pt => pt.id === selectedPartTypeForPart)?.name
        || partTypesSearchData?.results?.find(pt => pt.id === selectedPartTypeForPart)?.name;
    const selectedPart = partsData?.results?.find(p => p.id === selectedPartId);
    const selectedPartName = selectedPart
        ? (selectedPart.ERP_id || `Part #${selectedPart.id}`)
        : null;

    return (
        <div className="h-full overflow-hidden flex flex-col">
            {/* Header */}
            <div className="shrink-0 border-b px-6 py-4">
                <div className="flex items-center justify-between max-w-6xl mx-auto">
                    <div>
                        <h1 className="text-xl font-semibold">Defect Heat Map</h1>
                        <p className="text-sm text-muted-foreground">
                            Select a part type or specific part to visualize defects
                        </p>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span>{totalPartTypes} part types</span>
                        <span>{totalModels} models</span>
                        <span>{totalAnnotations} defects</span>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-auto px-6 py-4">
                <div className="max-w-4xl mx-auto">
                    {/* Tabs for selection method */}
                    <Tabs defaultValue="by-part-type" className="space-y-4">
                        <TabsList className="grid w-full max-w-sm grid-cols-2">
                            <TabsTrigger value="by-part-type" className="gap-2">
                                <Layers className="h-4 w-4" />
                                By Part Type
                            </TabsTrigger>
                            <TabsTrigger value="by-part" className="gap-2">
                                <Box className="h-4 w-4" />
                                By Specific Part
                            </TabsTrigger>
                        </TabsList>

                        {/* By Part Type Tab */}
                        <TabsContent value="by-part-type" className="space-y-4 mt-0">
                            {/* Search */}
                            <div className="relative max-w-sm">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    placeholder="Search part types..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="pl-10"
                                />
                            </div>

                            {/* Part Types Grid */}
                            {isLoadingModels ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                                    {[1, 2, 3, 4].map((i) => (
                                        <Skeleton key={i} className="h-20 rounded-lg" />
                                    ))}
                                </div>
                            ) : filteredPartTypes.length === 0 ? (
                                <Card className="border-dashed">
                                    <CardContent className="py-12 text-center">
                                        <FileWarning className="h-10 w-10 mx-auto mb-3 text-muted-foreground/30" />
                                        <p className="text-muted-foreground font-medium">
                                            {searchTerm
                                                ? "No part types match your search"
                                                : "No part types with 3D models found"}
                                        </p>
                                        {!searchTerm && (
                                            <p className="text-sm text-muted-foreground/70 mt-1">
                                                Upload 3D models in the editor to enable heatmap visualization
                                            </p>
                                        )}
                                    </CardContent>
                                </Card>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                                    {filteredPartTypes.map((partType) => (
                                        <PartTypeCard
                                            key={partType.id}
                                            partType={partType}
                                            onSelect={() => onSelectPartType(partType.id)}
                                            onHover={() => prefetchPartTypeData(partType.id)}
                                        />
                                    ))}
                                </div>
                            )}
                        </TabsContent>

                        {/* By Specific Part Tab */}
                        <TabsContent value="by-part" className="mt-0">
                            <Card>
                                <CardContent className="p-4">
                                    <div className="flex flex-wrap items-end gap-4">
                                        {/* Part Type Combobox */}
                                        <div className="space-y-1.5 min-w-[200px]">
                                            <Label className="text-sm">Part Type</Label>
                                            <Popover open={partTypeOpen} onOpenChange={setPartTypeOpen}>
                                                <PopoverTrigger asChild>
                                                    <Button
                                                        variant="outline"
                                                        role="combobox"
                                                        aria-expanded={partTypeOpen}
                                                        className="w-full justify-between font-normal"
                                                    >
                                                        {selectedPartTypeName || "Select part type..."}
                                                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                    </Button>
                                                </PopoverTrigger>
                                                <PopoverContent className="w-[200px] p-0">
                                                    <Command shouldFilter={false}>
                                                        <CommandInput
                                                            placeholder="Search part types..."
                                                            value={rawPartTypeSearch}
                                                            onValueChange={setRawPartTypeSearch}
                                                        />
                                                        <CommandList>
                                                            <CommandEmpty>No part type found.</CommandEmpty>
                                                            <CommandGroup>
                                                                {(partTypesSearchData?.results || []).map((pt) => (
                                                                    <CommandItem
                                                                        key={pt.id}
                                                                        value={pt.name}
                                                                        onSelect={() => {
                                                                            setSelectedPartTypeForPart(pt.id);
                                                                            setSelectedPartId(null);
                                                                            setRawPartTypeSearch("");
                                                                            setPartTypeOpen(false);
                                                                        }}
                                                                    >
                                                                        <Check
                                                                            className={cn(
                                                                                "mr-2 h-4 w-4",
                                                                                selectedPartTypeForPart === pt.id ? "opacity-100" : "opacity-0"
                                                                            )}
                                                                        />
                                                                        {pt.name}
                                                                    </CommandItem>
                                                                ))}
                                                            </CommandGroup>
                                                        </CommandList>
                                                    </Command>
                                                </PopoverContent>
                                            </Popover>
                                        </div>

                                        {/* Part Combobox */}
                                        <div className="space-y-1.5 min-w-[200px]">
                                            <Label className="text-sm">Part</Label>
                                            {isLoadingParts ? (
                                                <Skeleton className="h-10 w-full" />
                                            ) : (
                                                <Popover open={partOpen} onOpenChange={setPartOpen}>
                                                    <PopoverTrigger asChild>
                                                        <Button
                                                            variant="outline"
                                                            role="combobox"
                                                            aria-expanded={partOpen}
                                                            disabled={!selectedPartTypeForPart}
                                                            className="w-full justify-between font-normal"
                                                        >
                                                            {selectedPartName || (selectedPartTypeForPart ? "Select part..." : "Select part type first")}
                                                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                        </Button>
                                                    </PopoverTrigger>
                                                    <PopoverContent className="w-[200px] p-0">
                                                        <Command shouldFilter={false}>
                                                            <CommandInput
                                                                placeholder="Search parts..."
                                                                value={rawPartSearch}
                                                                onValueChange={setRawPartSearch}
                                                            />
                                                            <CommandList>
                                                                <CommandEmpty>No parts found.</CommandEmpty>
                                                                <CommandGroup>
                                                                    {(partsData?.results || []).map((part) => {
                                                                        const partName = part.ERP_id || `Part #${part.id}`;
                                                                        return (
                                                                            <CommandItem
                                                                                key={part.id}
                                                                                value={partName}
                                                                                onSelect={() => {
                                                                                    setSelectedPartId(part.id);
                                                                                    setRawPartSearch("");
                                                                                    setPartOpen(false);
                                                                                }}
                                                                            >
                                                                                <Check
                                                                                    className={cn(
                                                                                        "mr-2 h-4 w-4",
                                                                                        selectedPartId === part.id ? "opacity-100" : "opacity-0"
                                                                                    )}
                                                                                />
                                                                                {partName}
                                                                            </CommandItem>
                                                                        );
                                                                    })}
                                                                </CommandGroup>
                                                            </CommandList>
                                                        </Command>
                                                    </PopoverContent>
                                                </Popover>
                                            )}
                                        </div>

                                        {/* View Button */}
                                        <Button
                                            onClick={handleViewPartHeatmap}
                                            disabled={!selectedPartId}
                                        >
                                            View Heatmap
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </div>
            </div>
        </div>
    );
}

// Number input that only commits on blur or Enter (for better keyboard typing)
function CommitNumberInput({
    value,
    onChange,
    min,
    max,
    step,
    className,
}: {
    value: number;
    onChange: (value: number) => void;
    min: number;
    max: number;
    step: number;
    className?: string;
}) {
    const [localValue, setLocalValue] = useState(value.toFixed(2));
    const [isFocused, setIsFocused] = useState(false);

    // Sync local value when external value changes (but not while focused)
    useEffect(() => {
        if (!isFocused) {
            setLocalValue(value.toFixed(2));
        }
    }, [value, isFocused]);

    const commit = () => {
        const parsed = parseFloat(localValue);
        if (!isNaN(parsed)) {
            const clamped = Math.max(min, Math.min(max, parsed));
            onChange(clamped);
            setLocalValue(clamped.toFixed(2));
        } else {
            // Reset to current value if invalid
            setLocalValue(value.toFixed(2));
        }
    };

    return (
        <Input
            type="number"
            value={localValue}
            onChange={(e) => setLocalValue(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => {
                setIsFocused(false);
                commit();
            }}
            onKeyDown={(e) => {
                if (e.key === 'Enter') {
                    commit();
                    (e.target as HTMLInputElement).blur();
                }
            }}
            className={className}
            step={step}
            min={min}
            max={max}
        />
    );
}

// Main viewer component
function HeatMapViewerContent({
    partTypeId,
    partId,
    stepId: initialStepId,
    errorTypes: initialErrorTypes = [],
    severities: initialSeverities = [],
    showStatistics = true,
    className = "",
    showHeader = true,
    onBack,
}: HeatMapViewerProps & { onBack?: () => void }) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [annotationsExpanded, setAnnotationsExpanded] = useState(true);

    // Editing state
    const [isEditing, setIsEditing] = useState(false);
    const [editSeverity, setEditSeverity] = useState("");
    const [editDefectType, setEditDefectType] = useState("");
    const [editNotes, setEditNotes] = useState("");

    // Update mutation
    const updateAnnotation = useUpdateHeatMapAnnotation();
    const queryClient = useQueryClient();
    const [heatmapEnabled, setHeatmapEnabled] = useState(true);
    const [heatmapAutoAdjust, setHeatmapAutoAdjust] = useState(true);
    const [modelBounds, setModelBounds] = useState<ModelBounds | null>(null);
    // Manual values (used when auto-adjust is off)
    const [manualRadius, setManualRadius] = useState(0.5);
    const [manualIntensity, setManualIntensity] = useState(1.0);
    // Multipliers (used when auto-adjust is on)
    const [radiusMultiplier, setRadiusMultiplier] = useState(1.0);
    const [intensityMultiplier, setIntensityMultiplier] = useState(1.0);
    const [isFullscreen, setIsFullscreen] = useState(false);

    // User-controlled filters
    const [selectedStepId, setSelectedStepId] = useState<string | null>(initialStepId || null);
    const [selectedErrorTypes, setSelectedErrorTypes] = useState<string[]>(initialErrorTypes);
    const [selectedSeverities, setSelectedSeverities] = useState<string[]>(initialSeverities);
    const [dateRangePreset, setDateRangePreset] = useState<string>("all");
    const [customDateRange, setCustomDateRange] = useState<{ start: string; end: string }>({
        start: "",
        end: "",
    });
    const [selectedWorkOrderId, setSelectedWorkOrderId] = useState<string | null>(null);

    // Step 1: If viewing by partId, fetch the part to get its part_type
    const { data: partData, isLoading: isLoadingPart } = useQuery({
        queryKey: ["part", partId],
        queryFn: () => api.api_Parts_retrieve({ params: { id: partId! } }),
        enabled: !!partId,
    });

    const resolvedPartTypeId = partTypeId || partData?.part_type;

    // Step 3: Fetch available models for this part type to build step selector
    const { data: modelsData, isLoading: isLoadingModels } = useQuery({
        queryKey: ["models", resolvedPartTypeId],
        queryFn: () => api.api_ThreeDModels_list({
            queries: { part_type: resolvedPartTypeId }
        }),
        enabled: !!resolvedPartTypeId,
    });

    const availableModels = modelsData?.results || [];

    // Step 3b: Fetch work orders for the filter (based on part type)
    const { data: workOrdersData } = useQuery({
        queryKey: ["workorders-for-heatmap", resolvedPartTypeId],
        queryFn: () => api.api_WorkOrder_list({
            queries: { part_type: resolvedPartTypeId, limit: 100 }
        }),
        enabled: !!resolvedPartTypeId,
    });

    const availableWorkOrders = workOrdersData?.results || [];

    // Calculate date range from preset - returns full ISO datetime strings
    const getDateRangeFromPreset = useCallback((preset: string) => {
        const now = new Date();

        // Helper to get start of day in ISO format
        const startOfDay = (date: Date) => {
            const d = new Date(date);
            d.setHours(0, 0, 0, 0);
            return d.toISOString();
        };

        // Helper to get end of day in ISO format
        const endOfDay = (date: Date) => {
            const d = new Date(date);
            d.setHours(23, 59, 59, 999);
            return d.toISOString();
        };

        switch (preset) {
            case "7days": {
                const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                return { start: startOfDay(weekAgo), end: endOfDay(now) };
            }
            case "30days": {
                const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                return { start: startOfDay(monthAgo), end: endOfDay(now) };
            }
            case "90days": {
                const quarterAgo = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
                return { start: startOfDay(quarterAgo), end: endOfDay(now) };
            }
            case "custom":
                // Convert custom date strings to ISO if provided
                if (customDateRange.start || customDateRange.end) {
                    return {
                        start: customDateRange.start ? new Date(customDateRange.start + "T00:00:00").toISOString() : "",
                        end: customDateRange.end ? new Date(customDateRange.end + "T23:59:59").toISOString() : "",
                    };
                }
                return customDateRange;
            default:
                return { start: "", end: "" };
        }
    }, [customDateRange]);

    // Step 4: Determine which model to use
    const targetModel = useMemo(() => {
        if (!availableModels.length) return null;

        if (selectedStepId !== null) {
            return availableModels.find(m => m.step === selectedStepId) || null;
        } else {
            return availableModels.find(m => m.step === null) || availableModels[0];
        }
    }, [availableModels, selectedStepId]);

    // Step 5: Build base filters (used for both facets and annotations)
    const baseFilters = useMemo(() => {
        const filters: Record<string, string | number> = {};

        if (partId) {
            filters.part = partId;
        }

        if (targetModel) {
            filters.model = targetModel.id;
        }

        // Date range filter (dates are already in ISO format with time)
        const dateRange = getDateRangeFromPreset(dateRangePreset);
        if (dateRange.start) {
            filters.created_at__gte = dateRange.start;
        }
        if (dateRange.end) {
            filters.created_at__lte = dateRange.end;
        }

        // Work order filter
        if (selectedWorkOrderId) {
            filters.part__work_order = selectedWorkOrderId;
        }

        return filters;
    }, [partId, targetModel, dateRangePreset, getDateRangeFromPreset, selectedWorkOrderId]);

    // Step 5a: Fetch facets (aggregated counts) - lightweight query for filter dropdowns
    const { data: facetsData } = useHeatMapFacets(
        baseFilters,
        { enabled: !!targetModel }
    );

    // Step 5b: Fetch annotations with all filters (including defect_type and severity)
    const annotationFilters = useMemo(() => {
        const filters = { ...baseFilters };

        // Add defect type filter (server-side)
        if (selectedErrorTypes.length > 0) {
            filters.defect_type = selectedErrorTypes[0];
        }

        // Add severity filter (server-side)
        if (selectedSeverities.length > 0) {
            filters.severity = selectedSeverities[0];
        }

        return filters;
    }, [baseFilters, selectedErrorTypes, selectedSeverities]);

    const { data: annotationsData, isLoading: isFetchingAnnotations } = useRetrieveHeatMapAnnotations({
        queries: annotationFilters,
    });

    // Annotations are already filtered server-side
    const filteredAnnotations = annotationsData?.results || [];

    // Get facet data for dropdowns
    const availableDefectTypes = facetsData?.defect_types || [];
    const availableSeverities = facetsData?.severities || [];

    // Convert annotation positions to Vector3 array
    const heatmapPositions = useMemo(() => {
        return filteredAnnotations.map(
            (a) => new THREE.Vector3(a.position_x, a.position_y, a.position_z)
        );
    }, [filteredAnnotations]);

    // Compute per-annotation intensity weights based on severity
    // critical=2.0, high=1.5, medium=1.0, low=0.5
    const heatmapIntensities = useMemo(() => {
        const severityWeights: Record<string, number> = {
            critical: 2.0,
            high: 1.5,
            medium: 1.0,
            low: 0.5,
        };
        return filteredAnnotations.map(
            (a) => severityWeights[a.severity || "medium"] ?? 1.0
        );
    }, [filteredAnnotations]);

    // Calculate auto-adjusted heatmap values based on model size and annotation count
    const autoHeatmapValues = useMemo(() => {
        // Default values if we don't have model bounds yet
        const defaultRadius = 0.15; // ~5% of 3 unit model
        const defaultIntensity = 1.0;

        if (!modelBounds) {
            return { radius: defaultRadius, intensity: defaultIntensity };
        }

        // Radius: 5% of the model's max dimension
        // Model is scaled to ~3 units, so this gives radius around 0.15
        const baseRadius = modelBounds.maxDimension * 0.05;

        // Intensity: normalize based on annotation count
        // With few annotations, we want higher intensity; with many, lower
        // Using inverse square root to dampen the effect
        const annotationCount = filteredAnnotations.length;
        let baseIntensity = 1.0;
        if (annotationCount > 1) {
            // Scale down as annotation count increases
            // 1 annotation = 1.0, 10 annotations = ~0.5, 100 annotations = ~0.25
            baseIntensity = 1.5 / Math.sqrt(annotationCount);
            // Clamp to reasonable range
            baseIntensity = Math.max(0.1, Math.min(2.0, baseIntensity));
        }

        return { radius: baseRadius, intensity: baseIntensity };
    }, [modelBounds, filteredAnnotations.length]);

    // Final computed heatmap values
    const heatmapRadius = useMemo(() => {
        if (heatmapAutoAdjust) {
            return autoHeatmapValues.radius * radiusMultiplier;
        }
        return manualRadius;
    }, [heatmapAutoAdjust, autoHeatmapValues.radius, radiusMultiplier, manualRadius]);

    const heatmapIntensity = useMemo(() => {
        if (heatmapAutoAdjust) {
            return autoHeatmapValues.intensity * intensityMultiplier;
        }
        return manualIntensity;
    }, [heatmapAutoAdjust, autoHeatmapValues.intensity, intensityMultiplier, manualIntensity]);

    // Callback for when model bounds are calculated
    const handleModelBoundsCalculated = useCallback((bounds: ModelBounds) => {
        setModelBounds(bounds);
    }, []);

    const clearAllFilters = () => {
        setSelectedErrorTypes([]);
        setSelectedSeverities([]);
        setDateRangePreset("all");
        setCustomDateRange({ start: "", end: "" });
        setSelectedWorkOrderId(null);
    };

    const hasActiveFilters = selectedErrorTypes.length > 0 ||
        selectedSeverities.length > 0 ||
        dateRangePreset !== "all" ||
        selectedWorkOrderId !== null;

    // Fullscreen functionality
    const toggleFullscreen = () => {
        if (!containerRef.current) return;

        if (!document.fullscreenElement) {
            containerRef.current.requestFullscreen().then(() => {
                setIsFullscreen(true);
            }).catch((err) => {
                console.error('Error attempting to enable fullscreen:', err);
            });
        } else {
            document.exitFullscreen().then(() => {
                setIsFullscreen(false);
            });
        }
    };

    // Handle fullscreen change events
    useEffect(() => {
        const handleFullscreenChange = () => {
            setIsFullscreen(!!document.fullscreenElement);
        };

        document.addEventListener('fullscreenchange', handleFullscreenChange);
        return () => {
            document.removeEventListener('fullscreenchange', handleFullscreenChange);
        };
    }, []);

    // Keyboard shortcut for fullscreen (G key)
    useEffect(() => {
        const handleKeyPress = (e: KeyboardEvent) => {
            if (e.key === 'g' && !e.ctrlKey && !e.altKey && !e.metaKey) {
                if (e.target instanceof HTMLElement &&
                    (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) {
                    return;
                }
                e.preventDefault();
                toggleFullscreen();
            }
        };

        window.addEventListener('keydown', handleKeyPress);
        return () => {
            window.removeEventListener('keydown', handleKeyPress);
        };
    }, []);

    // Start editing the selected annotation
    const startEditing = () => {
        if (selectedIdx === null || !filteredAnnotations[selectedIdx]) return;
        const ann = filteredAnnotations[selectedIdx];
        setEditSeverity(ann.severity || "low");
        setEditDefectType(ann.defect_type || "");
        setEditNotes(ann.notes || "");
        setIsEditing(true);
    };

    // Cancel editing
    const cancelEditing = () => {
        setIsEditing(false);
        setEditSeverity("");
        setEditDefectType("");
        setEditNotes("");
    };

    // Save annotation changes
    const saveAnnotation = async () => {
        if (selectedIdx === null || !filteredAnnotations[selectedIdx]) return;
        const ann = filteredAnnotations[selectedIdx];
        if (!ann.id) {
            toast.error("Cannot update annotation without ID");
            return;
        }

        try {
            await updateAnnotation.mutateAsync({
                id: ann.id,
                data: {
                    severity: editSeverity,
                    defect_type: editDefectType,
                    notes: editNotes,
                },
            });
            // Invalidate all annotation queries to refresh the data
            queryClient.invalidateQueries({ queryKey: ["heatMapAnnotation"] });
            queryClient.invalidateQueries({ queryKey: ["heatmap-annotations"] });
            queryClient.invalidateQueries({ queryKey: ["heatmap-annotations-all"] });
            queryClient.invalidateQueries({ queryKey: ["heatmap-facets"] });
            toast.success("Annotation updated");
            setIsEditing(false);
        } catch (error) {
            console.error("Failed to update annotation:", error);
            toast.error("Failed to update annotation");
        }
    };

    // Reset editing state when selection changes
    useEffect(() => {
        setIsEditing(false);
    }, [selectedIdx]);

    // Loading state
    const isLoadingData = isLoadingPart || isLoadingModels || isFetchingAnnotations;

    if (isLoadingData) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <p className="text-muted-foreground">Loading heatmap data...</p>
                </div>
            </div>
        );
    }

    // Error state - no model found
    if (!targetModel) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="text-center p-8 max-w-md">
                    <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-destructive" />
                    <h3 className="text-lg font-semibold mb-2">No 3D Model Found</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                        No 3D model is available for this part type
                        {selectedStepId && " and step"}.
                    </p>
                    {partTypeId && <p className="text-xs text-muted-foreground font-mono mb-4">
                        Part Type ID: {resolvedPartTypeId}
                        {selectedStepId && `, Step ID: ${selectedStepId}`}
                    </p>}
                    {onBack && (
                        <Button variant="outline" onClick={onBack}>
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Back to Selection
                        </Button>
                    )}
                </div>
            </div>
        );
    }

    const modelUrl = normalizeMediaUrl(targetModel.file);

    return (
        <div
            ref={containerRef}
            className={`relative flex ${isFullscreen ? 'h-screen' : 'h-full'} w-full bg-background overflow-hidden ${className}`}
        >
            {/* Left Sidebar - Filters */}
            {showHeader && (
                <div className="w-64 border-r bg-card shrink-0 flex flex-col">
                    {/* Sidebar Header with Back Button */}
                    <div className="p-4 border-b">
                        {onBack && (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={onBack}
                                className="mb-2 -ml-2 text-muted-foreground hover:text-foreground"
                            >
                                <ArrowLeft className="h-4 w-4 mr-1" />
                                Change Selection
                            </Button>
                        )}
                        <h2 className="font-semibold text-sm">Filters & Controls</h2>
                    </div>

                    {/* Scrollable Filter Content */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-6">
                        {/* Step Selector */}
                        {availableModels.length > 1 && (
                            <div className="space-y-2">
                                <Label className="text-xs font-medium text-muted-foreground uppercase">Manufacturing Step</Label>
                                <Select
                                    value={selectedStepId?.toString() || "all"}
                                    onValueChange={(value) => setSelectedStepId(value === "all" ? null : value)}
                                >
                                    <SelectTrigger className="w-full">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent container={containerRef.current}>
                                        <SelectItem value="all">All Steps</SelectItem>
                                        {availableModels.map((model) => (
                                            <SelectItem key={model.id} value={model.id.toString()}>
                                                {model.step_display || "Default"}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}

                        {/* Defect Type Filter */}
                        <div className="space-y-3">
                            <Label className="text-xs font-medium text-muted-foreground uppercase">Defect Type</Label>
                            <Select
                                value={selectedErrorTypes[0] || "all"}
                                onValueChange={(value) => setSelectedErrorTypes(value === "all" ? [] : [value])}
                            >
                                <SelectTrigger className="w-full">
                                    <SelectValue placeholder="All Defect Types" />
                                </SelectTrigger>
                                <SelectContent container={containerRef.current}>
                                    <SelectItem value="all">All Defect Types</SelectItem>
                                    {availableDefectTypes.map((defectType) => (
                                        <SelectItem key={defectType.value} value={defectType.value}>
                                            {defectType.value} ({defectType.count})
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {availableDefectTypes.length === 0 && (
                                <p className="text-xs text-muted-foreground">
                                    No defect types found in current filters
                                </p>
                            )}
                        </div>

                        {/* Severity Filter */}
                        <div className="space-y-3">
                            <Label className="text-xs font-medium text-muted-foreground uppercase">Severity</Label>
                            <Select
                                value={selectedSeverities[0] || "all"}
                                onValueChange={(value) => setSelectedSeverities(value === "all" ? [] : [value])}
                            >
                                <SelectTrigger className="w-full">
                                    <SelectValue placeholder="All Severities" />
                                </SelectTrigger>
                                <SelectContent container={containerRef.current}>
                                    <SelectItem value="all">All Severities</SelectItem>
                                    {availableSeverities.map((severity) => (
                                        <SelectItem key={severity.value} value={severity.value}>
                                            {severity.value.charAt(0).toUpperCase() + severity.value.slice(1)} ({severity.count})
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Date Range Filter */}
                        <div className="space-y-3">
                            <Label className="text-xs font-medium text-muted-foreground uppercase">Date Range</Label>
                            <Select
                                value={dateRangePreset}
                                onValueChange={setDateRangePreset}
                            >
                                <SelectTrigger className="w-full">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent container={containerRef.current}>
                                    <SelectItem value="all">All Time</SelectItem>
                                    <SelectItem value="7days">Last 7 Days</SelectItem>
                                    <SelectItem value="30days">Last 30 Days</SelectItem>
                                    <SelectItem value="90days">Last 90 Days</SelectItem>
                                    <SelectItem value="custom">Custom Range</SelectItem>
                                </SelectContent>
                            </Select>
                            {dateRangePreset === "custom" && (
                                <div className="space-y-2 pt-2">
                                    <div className="space-y-1">
                                        <Label className="text-xs">Start Date</Label>
                                        <Input
                                            type="date"
                                            value={customDateRange.start}
                                            onChange={(e) => setCustomDateRange(prev => ({ ...prev, start: e.target.value }))}
                                        />
                                    </div>
                                    <div className="space-y-1">
                                        <Label className="text-xs">End Date</Label>
                                        <Input
                                            type="date"
                                            value={customDateRange.end}
                                            onChange={(e) => setCustomDateRange(prev => ({ ...prev, end: e.target.value }))}
                                        />
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Work Order Filter */}
                        {availableWorkOrders.length > 0 && (
                            <div className="space-y-3">
                                <Label className="text-xs font-medium text-muted-foreground uppercase">Work Order</Label>
                                <Select
                                    value={selectedWorkOrderId?.toString() || "all"}
                                    onValueChange={(value) => setSelectedWorkOrderId(value === "all" ? null : value)}
                                >
                                    <SelectTrigger className="w-full">
                                        <SelectValue placeholder="All Work Orders" />
                                    </SelectTrigger>
                                    <SelectContent container={containerRef.current}>
                                        <SelectItem value="all">All Work Orders</SelectItem>
                                        {availableWorkOrders.map((wo) => (
                                            <SelectItem key={wo.id} value={wo.id.toString()}>
                                                {wo.ERP_id || `WO-${wo.id}`}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}

                        {/* Clear All Filters */}
                        {hasActiveFilters && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={clearAllFilters}
                                className="w-full"
                            >
                                Clear All Filters
                            </Button>
                        )}

                        {/* Heatmap Controls */}
                        <div className="space-y-3 pt-4 border-t">
                            <Label className="text-xs font-medium text-muted-foreground uppercase">Heatmap Settings</Label>

                            <div className="flex items-center justify-between">
                                <Label htmlFor="heatmap" className="text-sm cursor-pointer">
                                    Enable Heatmap
                                </Label>
                                <Switch
                                    id="heatmap"
                                    checked={heatmapEnabled}
                                    onCheckedChange={setHeatmapEnabled}
                                />
                            </div>

                            {heatmapEnabled && (
                                <div className="space-y-4 pt-2">
                                    {/* Auto-adjust toggle */}
                                    <div className="flex items-center justify-between">
                                        <Label htmlFor="auto-adjust" className="text-sm cursor-pointer">
                                            Auto-adjust
                                        </Label>
                                        <Switch
                                            id="auto-adjust"
                                            checked={heatmapAutoAdjust}
                                            onCheckedChange={setHeatmapAutoAdjust}
                                        />
                                    </div>

                                    {/* Radius control */}
                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between">
                                            <Label className="text-xs">
                                                Radius {heatmapAutoAdjust && <span className="text-muted-foreground">(multiplier)</span>}
                                            </Label>
                                            <CommitNumberInput
                                                value={heatmapAutoAdjust ? radiusMultiplier : manualRadius}
                                                onChange={(val) => {
                                                    if (heatmapAutoAdjust) {
                                                        setRadiusMultiplier(val);
                                                    } else {
                                                        setManualRadius(val);
                                                    }
                                                }}
                                                className="w-20 h-7 text-xs text-right font-mono"
                                                step={0.05}
                                                min={heatmapAutoAdjust ? 0.1 : 0.01}
                                                max={heatmapAutoAdjust ? 3 : 5}
                                            />
                                        </div>
                                        <Slider
                                            value={[heatmapAutoAdjust ? radiusMultiplier : manualRadius]}
                                            onValueChange={([value]) => {
                                                if (heatmapAutoAdjust) {
                                                    setRadiusMultiplier(value);
                                                } else {
                                                    setManualRadius(value);
                                                }
                                            }}
                                            min={heatmapAutoAdjust ? 0.25 : 0.05}
                                            max={heatmapAutoAdjust ? 2.5 : 2}
                                            step={0.05}
                                            className="w-full"
                                        />
                                        {heatmapAutoAdjust && (
                                            <p className="text-xs text-muted-foreground">
                                                Final: {heatmapRadius.toFixed(3)} ({modelBounds ? ((heatmapRadius / modelBounds.maxDimension) * 100).toFixed(0) : 5}% of part)
                                            </p>
                                        )}
                                    </div>

                                    {/* Intensity control */}
                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between">
                                            <Label className="text-xs">
                                                Intensity {heatmapAutoAdjust && <span className="text-muted-foreground">(multiplier)</span>}
                                            </Label>
                                            <CommitNumberInput
                                                value={heatmapAutoAdjust ? intensityMultiplier : manualIntensity}
                                                onChange={(val) => {
                                                    if (heatmapAutoAdjust) {
                                                        setIntensityMultiplier(val);
                                                    } else {
                                                        setManualIntensity(val);
                                                    }
                                                }}
                                                className="w-20 h-7 text-xs text-right font-mono"
                                                step={0.1}
                                                min={0.1}
                                                max={5}
                                            />
                                        </div>
                                        <Slider
                                            value={[heatmapAutoAdjust ? intensityMultiplier : manualIntensity]}
                                            onValueChange={([value]) => {
                                                if (heatmapAutoAdjust) {
                                                    setIntensityMultiplier(value);
                                                } else {
                                                    setManualIntensity(value);
                                                }
                                            }}
                                            min={0.1}
                                            max={heatmapAutoAdjust ? 3 : 5}
                                            step={0.1}
                                            className="w-full"
                                        />
                                        {heatmapAutoAdjust && (
                                            <p className="text-xs text-muted-foreground">
                                                Final: {heatmapIntensity.toFixed(2)} (for {filteredAnnotations.length} defect{filteredAnnotations.length !== 1 ? 's' : ''})
                                            </p>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Top Header Bar */}
                {showHeader && (
                    <div className="p-4 border-b bg-card shrink-0">
                        <div className="flex items-center justify-between">
                            <div>
                                <h1 className="text-xl font-semibold">Defect Heat Map</h1>
                                <p className="text-sm text-muted-foreground">
                                    Showing {filteredAnnotations.length} of {facetsData?.total_count ?? filteredAnnotations.length} defect{(facetsData?.total_count ?? filteredAnnotations.length) !== 1 ? 's' : ''}
                                    {partId ? " on this part" : " across all parts"}
                                </p>
                            </div>

                            <div className="flex items-center gap-3">
                                {/* Statistics */}
                                {showStatistics && availableSeverities.length > 0 && (
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-muted-foreground mr-2">Severity:</span>
                                        {availableSeverities.map((severity) => {
                                            const variant =
                                                severity.value === "critical" ? "destructive" :
                                                severity.value === "high" ? "destructive" :
                                                severity.value === "medium" ? "secondary" :
                                                "outline";
                                            return (
                                                <Badge key={severity.value} variant={variant} className="text-xs">
                                                    {severity.value}: {severity.count}
                                                </Badge>
                                            );
                                        })}
                                    </div>
                                )}

                                {/* Fullscreen Toggle Button */}
                                <Button
                                    variant="outline"
                                    size="icon"
                                    onClick={toggleFullscreen}
                                    title={isFullscreen ? "Exit Fullscreen (G)" : "Enter Fullscreen (G)"}
                                >
                                    {isFullscreen ? (
                                        <Minimize className="h-4 w-4" />
                                    ) : (
                                        <Maximize className="h-4 w-4" />
                                    )}
                                </Button>
                            </div>
                        </div>
                    </div>
                )}

                {/* 3D Viewport */}
                <div className="flex-1 relative min-h-0">
                    {/* Navigation Instructions - Bottom Left */}
                    <div className="absolute bottom-4 left-4 z-10">
                        <div className="bg-background/90 backdrop-blur-sm rounded-lg p-3 shadow-lg border max-w-xs">
                            <p className="text-xs text-muted-foreground">
                                <span className="font-medium">Mouse:</span> Rotate, zoom, and pan
                                <br />
                                <span className="font-medium">Keyboard:</span> WASD to move • Space/Ctrl for up/down
                                <br />
                                QE yaw • RF pitch • ZC roll • G fullscreen
                            </p>
                        </div>
                    </div>

                    <ThreeDModelViewer
                        modelUrl={modelUrl}
                        mode="navigate"
                        isLoading={isLoading}
                        onLoadingComplete={() => setIsLoading(false)}
                        onModelBoundsCalculated={handleModelBoundsCalculated}
                        neutralColor="#94a3b8"
                        heatmapEnabled={heatmapEnabled}
                        heatmapPositions={heatmapPositions}
                        heatmapIntensities={heatmapIntensities}
                        heatmapRadius={heatmapRadius}
                        heatmapIntensity={heatmapIntensity}
                    >
                        {filteredAnnotations.map((annotation, idx) => (
                            <AnnotationPoint
                                key={annotation.id || idx}
                                position={[annotation.position_x, annotation.position_y, annotation.position_z]}
                                selected={idx === selectedIdx}
                                severity={annotation.severity || undefined}
                                onClick={() => setSelectedIdx(idx)}
                            />
                        ))}
                    </ThreeDModelViewer>

                    {/* Annotations List */}
                    <AnnotationsList
                        annotations={filteredAnnotations}
                        selectedIdx={selectedIdx}
                        expanded={annotationsExpanded}
                        onToggleExpanded={() => setAnnotationsExpanded(!annotationsExpanded)}
                        onAnnotationClick={(idx) => {
                            setSelectedIdx(idx);
                            setAnnotationsExpanded(false);
                        }}
                    />

                    {/* Selected Annotation Details */}
                    {selectedIdx !== null && filteredAnnotations[selectedIdx] && (
                        <div className="absolute top-4 right-4 w-80">
                            <Card>
                                <CardHeader className="pb-3">
                                    <div className="flex items-start justify-between gap-2">
                                        {isEditing ? (
                                            <CardTitle className="text-base">Edit Annotation</CardTitle>
                                        ) : (
                                            <>
                                                <CardTitle className="text-base">
                                                    {filteredAnnotations[selectedIdx].defect_type || "Unknown Defect"}
                                                </CardTitle>
                                                <div className="flex items-center gap-2">
                                                    <Badge variant={
                                                        filteredAnnotations[selectedIdx].severity === "critical" ? "destructive" :
                                                        filteredAnnotations[selectedIdx].severity === "high" ? "destructive" :
                                                        filteredAnnotations[selectedIdx].severity === "medium" ? "secondary" :
                                                        "outline"
                                                    }>
                                                        {filteredAnnotations[selectedIdx].severity || "N/A"}
                                                    </Badge>
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        className="h-6 w-6"
                                                        onClick={startEditing}
                                                        title="Edit annotation"
                                                    >
                                                        <Pencil className="h-3 w-3" />
                                                    </Button>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    {isEditing ? (
                                        /* Edit Mode */
                                        <>
                                            {/* Severity */}
                                            <div className="space-y-1">
                                                <Label className="text-xs text-muted-foreground">Severity</Label>
                                                <Select value={editSeverity} onValueChange={setEditSeverity}>
                                                    <SelectTrigger>
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="low">Low</SelectItem>
                                                        <SelectItem value="medium">Medium</SelectItem>
                                                        <SelectItem value="high">High</SelectItem>
                                                        <SelectItem value="critical">Critical</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                            </div>

                                            {/* Defect Type */}
                                            <div className="space-y-1">
                                                <Label className="text-xs text-muted-foreground">Defect Type</Label>
                                                <Select value={editDefectType} onValueChange={setEditDefectType}>
                                                    <SelectTrigger>
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {availableDefectTypes.map((dt) => (
                                                            <SelectItem key={dt.value} value={dt.value}>
                                                                {dt.value}
                                                            </SelectItem>
                                                        ))}
                                                        {/* Also allow the current value if not in list */}
                                                        {editDefectType && !availableDefectTypes.find(dt => dt.value === editDefectType) && (
                                                            <SelectItem value={editDefectType}>
                                                                {editDefectType}
                                                            </SelectItem>
                                                        )}
                                                    </SelectContent>
                                                </Select>
                                            </div>

                                            {/* Notes */}
                                            <div className="space-y-1">
                                                <Label className="text-xs text-muted-foreground">Notes</Label>
                                                <Textarea
                                                    value={editNotes}
                                                    onChange={(e) => setEditNotes(e.target.value)}
                                                    placeholder="Add notes about this defect..."
                                                    className="min-h-[80px]"
                                                />
                                            </div>

                                            {/* Action Buttons */}
                                            <div className="flex gap-2 pt-2">
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    className="flex-1"
                                                    onClick={cancelEditing}
                                                >
                                                    <X className="h-3 w-3 mr-1" />
                                                    Cancel
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    className="flex-1"
                                                    onClick={saveAnnotation}
                                                    disabled={updateAnnotation.isPending}
                                                >
                                                    <Save className="h-3 w-3 mr-1" />
                                                    {updateAnnotation.isPending ? "Saving..." : "Save"}
                                                </Button>
                                            </div>
                                        </>
                                    ) : (
                                        /* View Mode */
                                        <>
                                            {/* Position Coordinates */}
                                            <div className="space-y-1">
                                                <Label className="text-xs text-muted-foreground">Position (x, y, z)</Label>
                                                <p className="text-sm font-mono bg-muted px-2 py-1 rounded">
                                                    {filteredAnnotations[selectedIdx].position_x.toFixed(3)}, {' '}
                                                    {filteredAnnotations[selectedIdx].position_y.toFixed(3)}, {' '}
                                                    {filteredAnnotations[selectedIdx].position_z.toFixed(3)}
                                                </p>
                                            </div>

                                            {/* Notes */}
                                            {filteredAnnotations[selectedIdx].notes && (
                                                <div className="space-y-1">
                                                    <Label className="text-xs text-muted-foreground">Notes</Label>
                                                    <p className="text-sm">
                                                        {filteredAnnotations[selectedIdx].notes}
                                                    </p>
                                                </div>
                                            )}

                                            {/* Created By */}
                                            {filteredAnnotations[selectedIdx].created_by_display && (
                                                <div className="space-y-1">
                                                    <Label className="text-xs text-muted-foreground">Reported By</Label>
                                                    <p className="text-sm">
                                                        {filteredAnnotations[selectedIdx].created_by_display}
                                                    </p>
                                                </div>
                                            )}

                                            {/* Created At */}
                                            {filteredAnnotations[selectedIdx].created_at && (
                                                <div className="space-y-1">
                                                    <Label className="text-xs text-muted-foreground">Date Found</Label>
                                                    <p className="text-sm">
                                                        {new Date(filteredAnnotations[selectedIdx].created_at).toLocaleString()}
                                                    </p>
                                                </div>
                                            )}

                                            {/* Part Info */}
                                            {filteredAnnotations[selectedIdx].part_display && (
                                                <div className="space-y-1">
                                                    <Label className="text-xs text-muted-foreground">Part</Label>
                                                    <p className="text-sm">
                                                        {filteredAnnotations[selectedIdx].part_display}
                                                    </p>
                                                </div>
                                            )}
                                        </>
                                    )}
                                </CardContent>
                            </Card>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// Main exported component that handles both selection and viewing
export function HeatMapViewer(props: HeatMapViewerProps) {
    // Get route params (if navigated via route) and merge with props
    const routeParams = useParams({ strict: false }) as { partTypeId?: string; partId?: string };
    const mergedProps = {
        ...props,
        partTypeId: props.partTypeId ?? routeParams.partTypeId,
        partId: props.partId ?? routeParams.partId,
    };

    // Internal state for selection when no props provided
    const [internalPartTypeId, setInternalPartTypeId] = useState<string | null>(null);
    const [internalPartId, setInternalPartId] = useState<string | null>(null);

    // Determine if we should show selection or viewer
    const hasPropsSelection = mergedProps.partTypeId !== undefined || mergedProps.partId !== undefined;
    const hasInternalSelection = internalPartTypeId !== null || internalPartId !== null;

    // If props are provided, use them directly (viewer mode)
    if (hasPropsSelection) {
        return <HeatMapViewerContent {...mergedProps} />;
    }

    // If internal selection exists, show viewer with back button
    if (hasInternalSelection) {
        return (
            <HeatMapViewerContent
                {...mergedProps}
                partTypeId={internalPartTypeId ?? undefined}
                partId={internalPartId ?? undefined}
                onBack={() => {
                    setInternalPartTypeId(null);
                    setInternalPartId(null);
                }}
            />
        );
    }

    // Show selection interface
    return (
        <HeatMapSelection
            onSelectPartType={(id) => setInternalPartTypeId(id)}
            onSelectPart={(id) => setInternalPartId(id)}
        />
    );
}