import { useMemo } from "react";
import { useSearch } from "@tanstack/react-router";
import {
    CartesianGrid,
    Line,
    LineChart,
    ReferenceLine,
    XAxis,
    YAxis,
    ComposedChart,
    Bar,
} from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle, TrendingUp, Activity } from "lucide-react";
import { PrintLayout } from "@/components/print-layout";

// ---------- Types ----------
type ChartMode = "xbar-r" | "i-mr";

type SubgroupPoint = {
    subgroup: number;
    xBar: number;
    range: number;
    values: number[];
    timestamp: Date;
    label: string;
};

type IndividualPoint = {
    index: number;
    value: number;
    movingRange: number;
    timestamp: Date;
    label: string;
};

type ControlLimits = {
    xBarUCL: number;
    xBarLCL: number;
    xBarCL: number;
    rangeUCL: number;
    rangeLCL: number;
    rangeCL: number;
};

type IMRControlLimits = {
    individualUCL: number;
    individualLCL: number;
    individualCL: number;
    mrUCL: number;
    mrCL: number;
};

type OutOfControlPoint = {
    subgroup: number;
    type: "xBar" | "range" | "individual" | "mr";
    rule: string;
    value: number;
};

type MeasurementDef = {
    id: string;
    name: string;
    nominal: number;
    tolerancePlus: number;
    toleranceMinus: number;
    unit: string;
};

type Step = {
    id: string;
    name: string;
    measurements: MeasurementDef[];
};

type Process = {
    id: string;
    name: string;
    steps: Step[];
};

// ---------- Mock process/step/measurement hierarchy ----------
const processData: Process[] = [
    {
        id: "1",
        name: "CNC Machining",
        steps: [
            {
                id: "101",
                name: "Rough Turning",
                measurements: [
                    { id: "1001", name: "Outer Diameter", nominal: 25.0, tolerancePlus: 0.1, toleranceMinus: 0.1, unit: "mm" },
                    { id: "1002", name: "Length", nominal: 75.0, tolerancePlus: 0.2, toleranceMinus: 0.2, unit: "mm" },
                    { id: "1003", name: "Surface Roughness Ra", nominal: 3.2, tolerancePlus: 0.8, toleranceMinus: 0.0, unit: "μm" },
                ],
            },
            {
                id: "102",
                name: "Finish Turning",
                measurements: [
                    { id: "1004", name: "Outer Diameter", nominal: 24.5, tolerancePlus: 0.025, toleranceMinus: 0.025, unit: "mm" },
                    { id: "1005", name: "Concentricity", nominal: 0.0, tolerancePlus: 0.015, toleranceMinus: 0.0, unit: "mm" },
                    { id: "1006", name: "Surface Roughness Ra", nominal: 1.6, tolerancePlus: 0.4, toleranceMinus: 0.0, unit: "μm" },
                ],
            },
            {
                id: "103",
                name: "Boring",
                measurements: [
                    { id: "1007", name: "Bore Diameter", nominal: 10.0, tolerancePlus: 0.018, toleranceMinus: 0.0, unit: "mm" },
                    { id: "1008", name: "Bore Depth", nominal: 35.0, tolerancePlus: 0.1, toleranceMinus: 0.1, unit: "mm" },
                    { id: "1009", name: "Bore Cylindricity", nominal: 0.0, tolerancePlus: 0.008, toleranceMinus: 0.0, unit: "mm" },
                    { id: "1010", name: "Surface Roughness Ra", nominal: 0.8, tolerancePlus: 0.2, toleranceMinus: 0.0, unit: "μm" },
                ],
            },
            {
                id: "104",
                name: "Threading",
                measurements: [
                    { id: "1011", name: "Thread Pitch Diameter", nominal: 8.376, tolerancePlus: 0.036, toleranceMinus: 0.0, unit: "mm" },
                    { id: "1012", name: "Thread Pitch", nominal: 1.25, tolerancePlus: 0.02, toleranceMinus: 0.02, unit: "mm" },
                    { id: "1013", name: "Thread Depth", nominal: 0.812, tolerancePlus: 0.05, toleranceMinus: 0.05, unit: "mm" },
                ],
            },
        ],
    },
    {
        id: "2",
        name: "Grinding",
        steps: [
            {
                id: "201",
                name: "Centerless Grinding",
                measurements: [
                    { id: "2001", name: "Diameter", nominal: 12.0, tolerancePlus: 0.005, toleranceMinus: 0.005, unit: "mm" },
                    { id: "2002", name: "Roundness", nominal: 0.0, tolerancePlus: 0.003, toleranceMinus: 0.0, unit: "mm" },
                    { id: "2003", name: "Surface Roughness Ra", nominal: 0.4, tolerancePlus: 0.1, toleranceMinus: 0.0, unit: "μm" },
                ],
            },
            {
                id: "202",
                name: "Surface Grinding",
                measurements: [
                    { id: "2004", name: "Flatness", nominal: 0.0, tolerancePlus: 0.01, toleranceMinus: 0.0, unit: "mm" },
                    { id: "2005", name: "Parallelism", nominal: 0.0, tolerancePlus: 0.015, toleranceMinus: 0.0, unit: "mm" },
                    { id: "2006", name: "Thickness", nominal: 5.0, tolerancePlus: 0.01, toleranceMinus: 0.01, unit: "mm" },
                    { id: "2007", name: "Surface Roughness Ra", nominal: 0.2, tolerancePlus: 0.05, toleranceMinus: 0.0, unit: "μm" },
                ],
            },
            {
                id: "203",
                name: "Internal Grinding",
                measurements: [
                    { id: "2008", name: "Bore Diameter", nominal: 15.0, tolerancePlus: 0.008, toleranceMinus: 0.0, unit: "mm" },
                    { id: "2009", name: "Cylindricity", nominal: 0.0, tolerancePlus: 0.005, toleranceMinus: 0.0, unit: "mm" },
                    { id: "2010", name: "Surface Roughness Ra", nominal: 0.4, tolerancePlus: 0.1, toleranceMinus: 0.0, unit: "μm" },
                ],
            },
        ],
    },
    {
        id: "3",
        name: "Heat Treatment",
        steps: [
            {
                id: "301",
                name: "Hardening",
                measurements: [
                    { id: "3001", name: "Surface Hardness", nominal: 60.0, tolerancePlus: 2.0, toleranceMinus: 2.0, unit: "HRC" },
                    { id: "3002", name: "Case Depth", nominal: 0.8, tolerancePlus: 0.2, toleranceMinus: 0.2, unit: "mm" },
                    { id: "3003", name: "Core Hardness", nominal: 35.0, tolerancePlus: 3.0, toleranceMinus: 3.0, unit: "HRC" },
                ],
            },
            {
                id: "302",
                name: "Tempering",
                measurements: [
                    { id: "3004", name: "Final Hardness", nominal: 58.0, tolerancePlus: 2.0, toleranceMinus: 2.0, unit: "HRC" },
                    { id: "3005", name: "Distortion (Runout)", nominal: 0.0, tolerancePlus: 0.05, toleranceMinus: 0.0, unit: "mm" },
                ],
            },
        ],
    },
    {
        id: "4",
        name: "Assembly",
        steps: [
            {
                id: "401",
                name: "Press Fit",
                measurements: [
                    { id: "4001", name: "Press Force", nominal: 15.0, tolerancePlus: 3.0, toleranceMinus: 3.0, unit: "kN" },
                    { id: "4002", name: "Seat Depth", nominal: 12.0, tolerancePlus: 0.1, toleranceMinus: 0.1, unit: "mm" },
                    { id: "4003", name: "Final Position", nominal: 0.0, tolerancePlus: 0.05, toleranceMinus: 0.05, unit: "mm" },
                ],
            },
            {
                id: "402",
                name: "Torque Assembly",
                measurements: [
                    { id: "4004", name: "Torque", nominal: 25.0, tolerancePlus: 2.5, toleranceMinus: 2.5, unit: "Nm" },
                    { id: "4005", name: "Angle", nominal: 90.0, tolerancePlus: 5.0, toleranceMinus: 5.0, unit: "°" },
                    { id: "4006", name: "Clamp Load", nominal: 45.0, tolerancePlus: 5.0, toleranceMinus: 5.0, unit: "kN" },
                ],
            },
            {
                id: 403,
                name: "Final Inspection",
                measurements: [
                    { id: 4007, name: "Total Runout", nominal: 0.0, tolerancePlus: 0.025, toleranceMinus: 0.0, unit: "mm" },
                    { id: 4008, name: "Overall Length", nominal: 150.0, tolerancePlus: 0.1, toleranceMinus: 0.1, unit: "mm" },
                    { id: 4009, name: "Weight", nominal: 850.0, tolerancePlus: 10.0, toleranceMinus: 10.0, unit: "g" },
                ],
            },
        ],
    },
    {
        id: 5,
        name: "Surface Treatment",
        steps: [
            {
                id: 501,
                name: "Anodizing",
                measurements: [
                    { id: 5001, name: "Coating Thickness", nominal: 25.0, tolerancePlus: 5.0, toleranceMinus: 5.0, unit: "μm" },
                    { id: 5002, name: "Hardness", nominal: 400.0, tolerancePlus: 50.0, toleranceMinus: 50.0, unit: "HV" },
                    { id: 5003, name: "Color Delta E", nominal: 0.0, tolerancePlus: 1.0, toleranceMinus: 0.0, unit: "ΔE" },
                ],
            },
            {
                id: 502,
                name: "Plating",
                measurements: [
                    { id: 5004, name: "Coating Thickness", nominal: 8.0, tolerancePlus: 2.0, toleranceMinus: 2.0, unit: "μm" },
                    { id: 5005, name: "Adhesion (Tape Test)", nominal: 5.0, tolerancePlus: 0.0, toleranceMinus: 1.0, unit: "Class" },
                    { id: 5006, name: "Salt Spray Hours", nominal: 96.0, tolerancePlus: 0.0, toleranceMinus: 0.0, unit: "hrs" },
                ],
            },
        ],
    },
];

// ---------- Control chart constants ----------
const A2 = 0.577;
const D3 = 0;
const D4 = 2.114;
const d2 = 2.326;
const d2_mr = 1.128;
const D4_mr = 3.267;
const E2 = 2.66;

// ---------- Data generation functions ----------
function generateSpcData(measurementDef: MeasurementDef, numSubgroups: number = 25): SubgroupPoint[] {
    const data: SubgroupPoint[] = [];
    const subgroupSize = 5;
    const baseDate = new Date();
    baseDate.setDate(baseDate.getDate() - numSubgroups);

    let processMean = measurementDef.nominal;
    const processStdDev = (measurementDef.tolerancePlus + Math.abs(measurementDef.toleranceMinus)) / 6;

    for (let i = 0; i < numSubgroups; i++) {
        const values: number[] = [];
        if (i > 15) processMean = measurementDef.nominal + processStdDev * 0.3;

        for (let j = 0; j < subgroupSize; j++) {
            const specialCause = Math.random() < 0.05 ? processStdDev * 2.5 : 0;
            const value = processMean + (Math.random() - 0.5) * 2 * processStdDev + specialCause;
            values.push(Math.round(value * 1000) / 1000);
        }

        const xBar = values.reduce((a, b) => a + b, 0) / values.length;
        const range = Math.max(...values) - Math.min(...values);
        const timestamp = new Date(baseDate);
        timestamp.setDate(baseDate.getDate() + i);

        data.push({
            subgroup: i + 1,
            xBar: Math.round(xBar * 1000) / 1000,
            range: Math.round(range * 1000) / 1000,
            values,
            timestamp,
            label: timestamp.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        });
    }
    return data;
}

function generateIMRData(measurementDef: MeasurementDef, numPoints: number = 50): IndividualPoint[] {
    const data: IndividualPoint[] = [];
    const baseDate = new Date();
    baseDate.setDate(baseDate.getDate() - numPoints);

    let processMean = measurementDef.nominal;
    const processStdDev = (measurementDef.tolerancePlus + Math.abs(measurementDef.toleranceMinus)) / 6;

    for (let i = 0; i < numPoints; i++) {
        if (i > 30) processMean = measurementDef.nominal + processStdDev * 0.4;
        const specialCause = Math.random() < 0.04 ? processStdDev * 2.5 : 0;
        const value = processMean + (Math.random() - 0.5) * 2 * processStdDev + specialCause;
        const timestamp = new Date(baseDate);
        timestamp.setDate(baseDate.getDate() + i);
        const prevValue = i > 0 ? data[i - 1].value : value;
        const movingRange = Math.abs(value - prevValue);

        data.push({
            index: i + 1,
            value: Math.round(value * 1000) / 1000,
            movingRange: i === 0 ? 0 : Math.round(movingRange * 1000) / 1000,
            timestamp,
            label: timestamp.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        });
    }
    return data;
}

function calculateControlLimits(data: SubgroupPoint[]): ControlLimits {
    const xBarBar = data.reduce((sum, d) => sum + d.xBar, 0) / data.length;
    const rBar = data.reduce((sum, d) => sum + d.range, 0) / data.length;

    return {
        xBarUCL: Math.round((xBarBar + A2 * rBar) * 1000) / 1000,
        xBarLCL: Math.round((xBarBar - A2 * rBar) * 1000) / 1000,
        xBarCL: Math.round(xBarBar * 1000) / 1000,
        rangeUCL: Math.round((D4 * rBar) * 1000) / 1000,
        rangeLCL: Math.round((D3 * rBar) * 1000) / 1000,
        rangeCL: Math.round(rBar * 1000) / 1000,
    };
}

function calculateIMRControlLimits(data: IndividualPoint[]): IMRControlLimits {
    const values = data.map(d => d.value);
    const xBar = values.reduce((sum, v) => sum + v, 0) / values.length;
    const movingRanges = data.slice(1).map(d => d.movingRange);
    const mrBar = movingRanges.reduce((sum, mr) => sum + mr, 0) / movingRanges.length;

    return {
        individualUCL: Math.round((xBar + E2 * mrBar) * 1000) / 1000,
        individualLCL: Math.round((xBar - E2 * mrBar) * 1000) / 1000,
        individualCL: Math.round(xBar * 1000) / 1000,
        mrUCL: Math.round((D4_mr * mrBar) * 1000) / 1000,
        mrCL: Math.round(mrBar * 1000) / 1000,
    };
}

function detectOutOfControl(data: SubgroupPoint[], limits: ControlLimits): OutOfControlPoint[] {
    const ooc: OutOfControlPoint[] = [];

    data.forEach((point) => {
        if (point.xBar > limits.xBarUCL || point.xBar < limits.xBarLCL) {
            ooc.push({ subgroup: point.subgroup, type: "xBar", rule: "Rule 1: Beyond 3σ", value: point.xBar });
        }
        if (point.range > limits.rangeUCL) {
            ooc.push({ subgroup: point.subgroup, type: "range", rule: "Rule 1: Beyond UCL", value: point.range });
        }
    });

    return ooc;
}

function detectIMROutOfControl(data: IndividualPoint[], limits: IMRControlLimits): OutOfControlPoint[] {
    const ooc: OutOfControlPoint[] = [];

    data.forEach((point) => {
        if (point.value > limits.individualUCL || point.value < limits.individualLCL) {
            ooc.push({ subgroup: point.index, type: "individual", rule: "Rule 1: Beyond 3σ", value: point.value });
        }
        if (point.index > 1 && point.movingRange > limits.mrUCL) {
            ooc.push({ subgroup: point.index, type: "mr", rule: "Rule 1: Beyond UCL", value: point.movingRange });
        }
    });

    return ooc;
}

function calculateCapability(
    data: SubgroupPoint[],
    limits: ControlLimits,
    measurementDef: MeasurementDef
): { cp: number; cpk: number; pp: number; ppk: number; sigma: number } {
    const sigma = limits.rangeCL / d2;
    const usl = measurementDef.nominal + measurementDef.tolerancePlus;
    const lsl = measurementDef.nominal - Math.abs(measurementDef.toleranceMinus);
    const tolerance = usl - lsl;

    const cp = tolerance / (6 * sigma);
    const cpupper = (usl - limits.xBarCL) / (3 * sigma);
    const cplower = (limits.xBarCL - lsl) / (3 * sigma);
    const cpk = Math.min(cpupper, cplower);

    const allValues = data.flatMap(d => d.values);
    const overallMean = allValues.reduce((a, b) => a + b, 0) / allValues.length;
    const overallStdDev = Math.sqrt(
        allValues.reduce((sum, v) => sum + Math.pow(v - overallMean, 2), 0) / (allValues.length - 1)
    );

    const pp = tolerance / (6 * overallStdDev);
    const ppupper = (usl - overallMean) / (3 * overallStdDev);
    const pplower = (overallMean - lsl) / (3 * overallStdDev);
    const ppk = Math.min(ppupper, pplower);

    return {
        cp: Math.round(cp * 100) / 100,
        cpk: Math.round(cpk * 100) / 100,
        pp: Math.round(pp * 100) / 100,
        ppk: Math.round(ppk * 100) / 100,
        sigma: Math.round(sigma * 10000) / 10000,
    };
}

function generateHistogramData(data: SubgroupPoint[], measurementDef: MeasurementDef) {
    const allValues = data.flatMap(d => d.values);
    const min = Math.min(...allValues);
    const max = Math.max(...allValues);
    const binCount = 10;
    const binWidth = (max - min) / binCount;

    const bins: { bin: string; count: number; midpoint: number }[] = [];
    for (let i = 0; i < binCount; i++) {
        const binStart = min + i * binWidth;
        const binEnd = binStart + binWidth;
        const count = allValues.filter(v => v >= binStart && v < binEnd).length;
        bins.push({
            bin: `${binStart.toFixed(3)}`,
            count,
            midpoint: binStart + binWidth / 2,
        });
    }

    return { bins, lsl: measurementDef.nominal - Math.abs(measurementDef.toleranceMinus), usl: measurementDef.nominal + measurementDef.tolerancePlus };
}

// Chart configs
const xBarChartConfig = {
    xBar: { label: "X-bar", color: "var(--chart-1)" },
} as const;

const rangeChartConfig = {
    range: { label: "Range", color: "var(--chart-2)" },
} as const;

const individualChartConfig = {
    value: { label: "Individual", color: "var(--chart-1)" },
} as const;

const mrChartConfig = {
    movingRange: { label: "Moving Range", color: "var(--chart-2)" },
} as const;

// ---------- Print Component ----------
export default function SpcPrintPage() {
    const search = useSearch({ from: "/spc/print" }) as {
        processId?: string;
        stepId?: string;
        measurementId?: string;
        mode?: string;
    };

    const processId = search.processId || "1";
    const stepId = search.stepId || "101";
    const measurementId = search.measurementId || "1001";
    const chartMode: ChartMode = (search.mode as ChartMode) || "xbar-r";

    const selectedProcess = processData.find(p => p.id === processId) ?? processData[0];
    const selectedStep = selectedProcess.steps.find(s => s.id === stepId) ?? selectedProcess.steps[0];
    const measurementDef = selectedStep.measurements.find(m => m.id === measurementId) ?? selectedStep.measurements[0];

    // X-bar/R data
    const spcData = useMemo(() => generateSpcData(measurementDef), [measurementDef]);
    const controlLimits = useMemo(() => calculateControlLimits(spcData), [spcData]);
    const outOfControl = useMemo(() => detectOutOfControl(spcData, controlLimits), [spcData, controlLimits]);
    const capability = useMemo(() => calculateCapability(spcData, controlLimits, measurementDef), [spcData, controlLimits, measurementDef]);
    const histogramData = useMemo(() => generateHistogramData(spcData, measurementDef), [spcData, measurementDef]);

    // I-MR data
    const imrData = useMemo(() => generateIMRData(measurementDef), [measurementDef]);
    const imrControlLimits = useMemo(() => calculateIMRControlLimits(imrData), [imrData]);
    const imrOutOfControl = useMemo(() => detectIMROutOfControl(imrData, imrControlLimits), [imrData, imrControlLimits]);

    const activeOutOfControl = chartMode === "xbar-r" ? outOfControl : imrOutOfControl;
    const usl = measurementDef.nominal + measurementDef.tolerancePlus;
    const lsl = measurementDef.nominal - Math.abs(measurementDef.toleranceMinus);
    const isProcessCapable = capability.cpk >= 1.33;
    const hasOutOfControl = activeOutOfControl.length > 0;

    return (
        <PrintLayout
            title="SPC Report"
            subtitle={`${selectedProcess.name} → ${selectedStep.name} → ${measurementDef.name}`}
        >
            <div className="space-y-6">
                {/* Specification badges */}
                <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline" className="font-mono">
                        Nominal: {measurementDef.nominal} {measurementDef.unit}
                    </Badge>
                    <Badge variant="outline" className="font-mono">
                        Tolerance: +{measurementDef.tolerancePlus}/-{Math.abs(measurementDef.toleranceMinus)} {measurementDef.unit}
                    </Badge>
                    <Badge variant="secondary" className="font-mono">
                        USL: {usl.toFixed(3)} {measurementDef.unit}
                    </Badge>
                    <Badge variant="secondary" className="font-mono">
                        LSL: {lsl.toFixed(3)} {measurementDef.unit}
                    </Badge>
                    <Badge variant="outline" className="font-mono">
                        Mode: {chartMode === "xbar-r" ? "X-bar/R" : "I-MR"}
                    </Badge>
                </div>

                {/* KPI Cards */}
                <div className="grid grid-cols-4 gap-3">
                    <Card className="border-muted/40">
                        <CardHeader className="pb-1 flex flex-row items-center justify-between space-y-0">
                            <CardTitle className="text-xs font-medium text-muted-foreground">Cpk</CardTitle>
                            {isProcessCapable ? (
                                <CheckCircle className="h-4 w-4 text-green-500" />
                            ) : (
                                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                            )}
                        </CardHeader>
                        <CardContent className="pt-0">
                            <div className={`text-2xl font-bold ${isProcessCapable ? "text-green-600" : "text-yellow-600"}`}>
                                {capability.cpk.toFixed(2)}
                            </div>
                            <p className="text-xs text-muted-foreground">Target: ≥1.33</p>
                        </CardContent>
                    </Card>

                    <Card className="border-muted/40">
                        <CardHeader className="pb-1 flex flex-row items-center justify-between space-y-0">
                            <CardTitle className="text-xs font-medium text-muted-foreground">Cp</CardTitle>
                            <TrendingUp className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent className="pt-0">
                            <div className="text-2xl font-bold">{capability.cp.toFixed(2)}</div>
                            <p className="text-xs text-muted-foreground">Process potential</p>
                        </CardContent>
                    </Card>

                    <Card className="border-muted/40">
                        <CardHeader className="pb-1 flex flex-row items-center justify-between space-y-0">
                            <CardTitle className="text-xs font-medium text-muted-foreground">Out of Control</CardTitle>
                            {hasOutOfControl ? (
                                <AlertTriangle className="h-4 w-4 text-destructive" />
                            ) : (
                                <CheckCircle className="h-4 w-4 text-green-500" />
                            )}
                        </CardHeader>
                        <CardContent className="pt-0">
                            <div className={`text-2xl font-bold ${hasOutOfControl ? "text-destructive" : "text-green-600"}`}>
                                {activeOutOfControl.length}
                            </div>
                            <p className="text-xs text-muted-foreground">Points flagged</p>
                        </CardContent>
                    </Card>

                    <Card className="border-muted/40">
                        <CardHeader className="pb-1 flex flex-row items-center justify-between space-y-0">
                            <CardTitle className="text-xs font-medium text-muted-foreground">Process σ</CardTitle>
                            <Activity className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent className="pt-0">
                            <div className="text-2xl font-bold">{capability.sigma.toFixed(4)}</div>
                            <p className="text-xs text-muted-foreground">{measurementDef.unit}</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Control Charts */}
                {chartMode === "xbar-r" ? (
                    <>
                        {/* X-bar Chart */}
                        <Card className="border-muted/40">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-base">X-bar Chart (Subgroup Means)</CardTitle>
                                <CardDescription className="text-xs">
                                    CL: {controlLimits.xBarCL} | UCL: {controlLimits.xBarUCL} | LCL: {controlLimits.xBarLCL} | USL: {usl.toFixed(3)} | LSL: {lsl.toFixed(3)}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="pt-0">
                                <ChartContainer className="h-[200px] w-full" config={xBarChartConfig}>
                                    <LineChart data={spcData} margin={{ left: 8, right: 40, top: 8, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                        <XAxis dataKey="subgroup" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                                        <YAxis
                                            width={60}
                                            tickLine={false}
                                            axisLine={false}
                                            domain={[
                                                Math.min(lsl, controlLimits.xBarLCL) - (controlLimits.xBarUCL - controlLimits.xBarLCL) * 0.1,
                                                Math.max(usl, controlLimits.xBarUCL) + (controlLimits.xBarUCL - controlLimits.xBarLCL) * 0.1,
                                            ]}
                                            tickFormatter={(v) => v.toFixed(3)}
                                        />
                                        <ChartTooltip content={<ChartTooltipContent formatter={(value) => (value as number).toFixed(4)} />} />
                                        <ReferenceLine y={usl} stroke="var(--chart-5)" strokeWidth={2} strokeDasharray="8 4" />
                                        <ReferenceLine y={lsl} stroke="var(--chart-5)" strokeWidth={2} strokeDasharray="8 4" />
                                        <ReferenceLine y={controlLimits.xBarUCL} stroke="var(--destructive)" strokeDasharray="5 5" />
                                        <ReferenceLine y={controlLimits.xBarCL} stroke="var(--chart-3)" strokeWidth={2} />
                                        <ReferenceLine y={controlLimits.xBarLCL} stroke="var(--destructive)" strokeDasharray="5 5" />
                                        <Line
                                            dataKey="xBar"
                                            stroke="var(--chart-1)"
                                            strokeWidth={2}
                                            dot={(props) => {
                                                const isOOC = outOfControl.some((o) => o.subgroup === props.payload.subgroup && o.type === "xBar");
                                                return (
                                                    <circle
                                                        cx={props.cx}
                                                        cy={props.cy}
                                                        r={isOOC ? 5 : 3}
                                                        fill={isOOC ? "var(--destructive)" : "var(--chart-1)"}
                                                        stroke={isOOC ? "var(--destructive)" : "var(--chart-1)"}
                                                    />
                                                );
                                            }}
                                        />
                                    </LineChart>
                                </ChartContainer>
                            </CardContent>
                        </Card>

                        {/* Range Chart */}
                        <Card className="border-muted/40">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-base">R Chart (Subgroup Ranges)</CardTitle>
                                <CardDescription className="text-xs">
                                    CL: {controlLimits.rangeCL} | UCL: {controlLimits.rangeUCL}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="pt-0">
                                <ChartContainer className="h-[160px] w-full" config={rangeChartConfig}>
                                    <LineChart data={spcData} margin={{ left: 8, right: 40, top: 8, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                        <XAxis dataKey="subgroup" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                                        <YAxis
                                            width={60}
                                            tickLine={false}
                                            axisLine={false}
                                            domain={[0, controlLimits.rangeUCL * 1.2]}
                                            tickFormatter={(v) => v.toFixed(3)}
                                        />
                                        <ChartTooltip content={<ChartTooltipContent formatter={(value) => (value as number).toFixed(4)} />} />
                                        <ReferenceLine y={controlLimits.rangeUCL} stroke="var(--destructive)" strokeDasharray="5 5" />
                                        <ReferenceLine y={controlLimits.rangeCL} stroke="var(--chart-3)" strokeWidth={2} />
                                        <Line
                                            dataKey="range"
                                            stroke="var(--chart-2)"
                                            strokeWidth={2}
                                            dot={(props) => {
                                                const isOOC = outOfControl.some((o) => o.subgroup === props.payload.subgroup && o.type === "range");
                                                return (
                                                    <circle
                                                        cx={props.cx}
                                                        cy={props.cy}
                                                        r={isOOC ? 5 : 3}
                                                        fill={isOOC ? "var(--destructive)" : "var(--chart-2)"}
                                                        stroke={isOOC ? "var(--destructive)" : "var(--chart-2)"}
                                                    />
                                                );
                                            }}
                                        />
                                    </LineChart>
                                </ChartContainer>
                            </CardContent>
                        </Card>
                    </>
                ) : (
                    <>
                        {/* Individual Chart */}
                        <Card className="border-muted/40">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-base">Individual Chart (I)</CardTitle>
                                <CardDescription className="text-xs">
                                    CL: {imrControlLimits.individualCL} | UCL: {imrControlLimits.individualUCL} | LCL: {imrControlLimits.individualLCL}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="pt-0">
                                <ChartContainer className="h-[200px] w-full" config={individualChartConfig}>
                                    <LineChart data={imrData} margin={{ left: 8, right: 40, top: 8, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                        <XAxis dataKey="index" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                                        <YAxis
                                            width={60}
                                            tickLine={false}
                                            axisLine={false}
                                            domain={[
                                                Math.min(lsl, imrControlLimits.individualLCL) - (imrControlLimits.individualUCL - imrControlLimits.individualLCL) * 0.1,
                                                Math.max(usl, imrControlLimits.individualUCL) + (imrControlLimits.individualUCL - imrControlLimits.individualLCL) * 0.1,
                                            ]}
                                            tickFormatter={(v) => v.toFixed(3)}
                                        />
                                        <ChartTooltip content={<ChartTooltipContent formatter={(value) => (value as number).toFixed(4)} />} />
                                        <ReferenceLine y={usl} stroke="var(--chart-5)" strokeWidth={2} strokeDasharray="8 4" />
                                        <ReferenceLine y={lsl} stroke="var(--chart-5)" strokeWidth={2} strokeDasharray="8 4" />
                                        <ReferenceLine y={imrControlLimits.individualUCL} stroke="var(--destructive)" strokeDasharray="5 5" />
                                        <ReferenceLine y={imrControlLimits.individualCL} stroke="var(--chart-3)" strokeWidth={2} />
                                        <ReferenceLine y={imrControlLimits.individualLCL} stroke="var(--destructive)" strokeDasharray="5 5" />
                                        <Line
                                            dataKey="value"
                                            stroke="var(--chart-1)"
                                            strokeWidth={2}
                                            dot={(props) => {
                                                const isOOC = imrOutOfControl.some((o) => o.subgroup === props.payload.index && o.type === "individual");
                                                return (
                                                    <circle
                                                        cx={props.cx}
                                                        cy={props.cy}
                                                        r={isOOC ? 5 : 3}
                                                        fill={isOOC ? "var(--destructive)" : "var(--chart-1)"}
                                                        stroke={isOOC ? "var(--destructive)" : "var(--chart-1)"}
                                                    />
                                                );
                                            }}
                                        />
                                    </LineChart>
                                </ChartContainer>
                            </CardContent>
                        </Card>

                        {/* Moving Range Chart */}
                        <Card className="border-muted/40">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-base">Moving Range Chart (MR)</CardTitle>
                                <CardDescription className="text-xs">
                                    CL: {imrControlLimits.mrCL} | UCL: {imrControlLimits.mrUCL}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="pt-0">
                                <ChartContainer className="h-[160px] w-full" config={mrChartConfig}>
                                    <LineChart data={imrData.slice(1)} margin={{ left: 8, right: 40, top: 8, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                        <XAxis dataKey="index" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                                        <YAxis
                                            width={60}
                                            tickLine={false}
                                            axisLine={false}
                                            domain={[0, imrControlLimits.mrUCL * 1.2]}
                                            tickFormatter={(v) => v.toFixed(3)}
                                        />
                                        <ChartTooltip content={<ChartTooltipContent formatter={(value) => (value as number).toFixed(4)} />} />
                                        <ReferenceLine y={imrControlLimits.mrUCL} stroke="var(--destructive)" strokeDasharray="5 5" />
                                        <ReferenceLine y={imrControlLimits.mrCL} stroke="var(--chart-3)" strokeWidth={2} />
                                        <Line
                                            dataKey="movingRange"
                                            stroke="var(--chart-2)"
                                            strokeWidth={2}
                                            dot={(props) => {
                                                const isOOC = imrOutOfControl.some((o) => o.subgroup === props.payload.index && o.type === "mr");
                                                return (
                                                    <circle
                                                        cx={props.cx}
                                                        cy={props.cy}
                                                        r={isOOC ? 5 : 3}
                                                        fill={isOOC ? "var(--destructive)" : "var(--chart-2)"}
                                                        stroke={isOOC ? "var(--destructive)" : "var(--chart-2)"}
                                                    />
                                                );
                                            }}
                                        />
                                    </LineChart>
                                </ChartContainer>
                            </CardContent>
                        </Card>
                    </>
                )}

                {/* Histogram */}
                <Card className="border-muted/40">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-base">Process Distribution</CardTitle>
                        <CardDescription className="text-xs">
                            Histogram with specification limits
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-0">
                        <ChartContainer className="h-[200px] w-full" config={{ count: { label: "Count", color: "var(--chart-1)" } }}>
                            <ComposedChart data={histogramData.bins} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis
                                    dataKey="bin"
                                    tickLine={false}
                                    axisLine={false}
                                    tick={{ fontSize: 9 }}
                                    angle={-45}
                                    textAnchor="end"
                                    height={50}
                                />
                                <YAxis width={35} tickLine={false} axisLine={false} />
                                <ChartTooltip content={<ChartTooltipContent />} />
                                <ReferenceLine x={histogramData.lsl.toFixed(3)} stroke="var(--destructive)" strokeWidth={2} />
                                <ReferenceLine x={histogramData.usl.toFixed(3)} stroke="var(--destructive)" strokeWidth={2} />
                                <Bar dataKey="count" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
                            </ComposedChart>
                        </ChartContainer>
                    </CardContent>
                </Card>

                {/* Out of Control Summary */}
                {activeOutOfControl.length > 0 && (
                    <Card className="border-destructive/50 bg-destructive/5">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-base flex items-center gap-2">
                                <AlertTriangle className="h-4 w-4 text-destructive" />
                                Out of Control Points ({activeOutOfControl.length})
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <div className="grid grid-cols-2 gap-2 text-sm">
                                {activeOutOfControl.slice(0, 10).map((ooc, i) => (
                                    <div key={i} className="flex items-center gap-2">
                                        <Badge variant="destructive" className="text-xs">
                                            {ooc.type === "xBar" ? "X-bar" : ooc.type === "range" ? "Range" : ooc.type === "individual" ? "I" : "MR"}
                                        </Badge>
                                        <span>Point {ooc.subgroup}</span>
                                        <span className="text-muted-foreground text-xs">{ooc.rule}</span>
                                    </div>
                                ))}
                                {activeOutOfControl.length > 10 && (
                                    <div className="col-span-2 text-muted-foreground text-xs">
                                        ...and {activeOutOfControl.length - 10} more
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Process Capability Summary */}
                <Card className="border-muted/40">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-base">Process Capability Summary</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-4 gap-4 text-sm">
                            <div>
                                <div className="text-muted-foreground">Cp (Potential)</div>
                                <div className="text-lg font-semibold">{capability.cp.toFixed(2)}</div>
                            </div>
                            <div>
                                <div className="text-muted-foreground">Cpk (Actual)</div>
                                <div className={`text-lg font-semibold ${capability.cpk >= 1.33 ? "text-green-600" : capability.cpk >= 1.0 ? "text-yellow-600" : "text-destructive"}`}>
                                    {capability.cpk.toFixed(2)}
                                </div>
                            </div>
                            <div>
                                <div className="text-muted-foreground">Pp (Performance)</div>
                                <div className="text-lg font-semibold">{capability.pp.toFixed(2)}</div>
                            </div>
                            <div>
                                <div className="text-muted-foreground">Ppk (Actual Perf.)</div>
                                <div className={`text-lg font-semibold ${capability.ppk >= 1.33 ? "text-green-600" : capability.ppk >= 1.0 ? "text-yellow-600" : "text-destructive"}`}>
                                    {capability.ppk.toFixed(2)}
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </PrintLayout>
    );
}
