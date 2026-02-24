import { useMemo, useState, useEffect } from "react";
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
import { Select, SelectTrigger, SelectItem, SelectContent, SelectValue } from "@/components/ui/select";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { AlertTriangle, CheckCircle, TrendingUp, Activity, FileWarning, Mail, Loader2, Lock, Unlock, HelpCircle } from "lucide-react";
import { Link, useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { useReportEmail } from "@/hooks/useReportEmail";
import { useSpcHierarchy, type ProcessSPC } from "@/hooks/useSpcHierarchy";
import { useSpcData } from "@/hooks/useSpcData";
import { useSpcCapability } from "@/hooks/useSpcCapability";
import {
    useSpcActiveBaseline,
    useFreezeSpcBaseline,
    useSupersedeSpcBaseline,
    toFreezeRequest,
    type ChartType as ApiChartType,
} from "@/hooks/useSpcBaseline";

// ---------- Types ----------
type ChartMode = "xbar-r" | "xbar-s" | "i-mr";
type SubgroupChartType = "xbar-r" | "xbar-s"; // For subgroup charts only

type SubgroupPoint = {
    subgroup: number;
    xBar: number;
    range: number;
    stdDev: number; // For X̄-S charts
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

// Note: Process/Step/Measurement hierarchy is now loaded from API via useSpcHierarchy()

// ---------- Control chart constants by subgroup size (n=2 to 25) ----------
// Reference: AIAG SPC Manual, Montgomery "Introduction to Statistical Quality Control"
// X̄-R constants (for n ≤ 8)
const XBAR_R_CONSTANTS: Record<number, { A2: number; D3: number; D4: number; d2: number }> = {
    2: { A2: 1.880, D3: 0, D4: 3.267, d2: 1.128 },
    3: { A2: 1.023, D3: 0, D4: 2.574, d2: 1.693 },
    4: { A2: 0.729, D3: 0, D4: 2.282, d2: 2.059 },
    5: { A2: 0.577, D3: 0, D4: 2.114, d2: 2.326 },
    6: { A2: 0.483, D3: 0, D4: 2.004, d2: 2.534 },
    7: { A2: 0.419, D3: 0.076, D4: 1.924, d2: 2.704 },
    8: { A2: 0.373, D3: 0.136, D4: 1.864, d2: 2.847 },
    9: { A2: 0.337, D3: 0.184, D4: 1.816, d2: 2.970 },
};

// X̄-S constants (for n > 8, but can be used for any n)
const XBAR_S_CONSTANTS: Record<number, { A3: number; B3: number; B4: number; c4: number }> = {
    2:  { A3: 2.659, B3: 0, B4: 3.267, c4: 0.7979 },
    3:  { A3: 1.954, B3: 0, B4: 2.568, c4: 0.8862 },
    4:  { A3: 1.628, B3: 0, B4: 2.266, c4: 0.9213 },
    5:  { A3: 1.427, B3: 0, B4: 2.089, c4: 0.9400 },
    6:  { A3: 1.287, B3: 0.030, B4: 1.970, c4: 0.9515 },
    7:  { A3: 1.182, B3: 0.118, B4: 1.882, c4: 0.9594 },
    8:  { A3: 1.099, B3: 0.185, B4: 1.815, c4: 0.9650 },
    9:  { A3: 1.032, B3: 0.239, B4: 1.761, c4: 0.9693 },
    10: { A3: 0.975, B3: 0.284, B4: 1.716, c4: 0.9727 },
    15: { A3: 0.789, B3: 0.428, B4: 1.572, c4: 0.9823 },
    20: { A3: 0.680, B3: 0.510, B4: 1.490, c4: 0.9869 },
    25: { A3: 0.606, B3: 0.565, B4: 1.435, c4: 0.9896 },
};

function getXbarRConstants(n: number) {
    return XBAR_R_CONSTANTS[n] || XBAR_R_CONSTANTS[5];
}

function getXbarSConstants(n: number) {
    // Find closest available constant
    const keys = Object.keys(XBAR_S_CONSTANTS).map(Number).sort((a, b) => a - b);
    const closest = keys.reduce((prev, curr) =>
        Math.abs(curr - n) < Math.abs(prev - n) ? curr : prev
    );
    return XBAR_S_CONSTANTS[closest];
}

// Determine recommended chart type based on subgroup size
function getRecommendedChartType(n: number): SubgroupChartType {
    return n <= 8 ? "xbar-r" : "xbar-s";
}

// ---------- I-MR chart constants (for moving range of 2 consecutive points) ----------
const d2_mr = 1.128; // d2 for n=2 (moving range)
const D4_mr = 3.267; // D4 for n=2 (moving range UCL)
const E2 = 2.66;     // Individual chart constant (3/d2 for n=2)

// ---------- Generate mock SPC data ----------
function generateSpcData(measurementDef: MeasurementDef, numSubgroups: number = 25): SubgroupPoint[] {
    const data: SubgroupPoint[] = [];
    const subgroupSize = 5;
    const baseDate = new Date();
    baseDate.setDate(baseDate.getDate() - numSubgroups);

    // Process parameters - slight drift and occasional special causes
    let processMean = measurementDef.nominal;
    const processStdDev = (measurementDef.tolerancePlus + Math.abs(measurementDef.toleranceMinus)) / 6; // Cp = 1.0

    for (let i = 0; i < numSubgroups; i++) {
        const values: number[] = [];

        // Simulate slight process drift
        if (i > 15) processMean = measurementDef.nominal + processStdDev * 0.3;

        // Generate subgroup values
        for (let j = 0; j < subgroupSize; j++) {
            // Add occasional special cause (1 in 20 chance)
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

// ---------- Generate mock I-MR data ----------
function generateIMRData(measurementDef: MeasurementDef, numPoints: number = 50): IndividualPoint[] {
    const data: IndividualPoint[] = [];
    const baseDate = new Date();
    baseDate.setDate(baseDate.getDate() - numPoints);

    let processMean = measurementDef.nominal;
    const processStdDev = (measurementDef.tolerancePlus + Math.abs(measurementDef.toleranceMinus)) / 6;

    for (let i = 0; i < numPoints; i++) {
        // Simulate slight process drift after point 30
        if (i > 30) processMean = measurementDef.nominal + processStdDev * 0.4;

        // Add occasional special cause (1 in 25 chance)
        const specialCause = Math.random() < 0.04 ? processStdDev * 2.5 : 0;
        const value = processMean + (Math.random() - 0.5) * 2 * processStdDev + specialCause;

        const timestamp = new Date(baseDate);
        timestamp.setDate(baseDate.getDate() + i);

        // Calculate moving range (difference from previous point)
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

// ---------- Calculate I-MR control limits ----------
function calculateIMRControlLimits(data: IndividualPoint[]): IMRControlLimits {
    const values = data.map(d => d.value);
    const xBar = values.reduce((sum, v) => sum + v, 0) / values.length;

    // Average moving range (excluding first point which has MR = 0)
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

// ---------- Detect out-of-control points for I-MR charts ----------
function detectIMROutOfControl(data: IndividualPoint[], limits: IMRControlLimits): OutOfControlPoint[] {
    const ooc: OutOfControlPoint[] = [];

    const isAlreadyFlagged = (index: number, type: "individual" | "mr") =>
        ooc.some(o => o.subgroup === index && o.type === type);

    // Calculate sigma for zone tests
    const sigma = (limits.individualUCL - limits.individualCL) / 3;
    const sigma1Upper = limits.individualCL + sigma;
    const sigma1Lower = limits.individualCL - sigma;
    const sigma2Upper = limits.individualCL + 2 * sigma;
    const sigma2Lower = limits.individualCL - 2 * sigma;

    // Rule 1: Point beyond 3σ
    data.forEach((point) => {
        if (point.value > limits.individualUCL || point.value < limits.individualLCL) {
            ooc.push({ subgroup: point.index, type: "individual", rule: "Rule 1: Beyond 3σ", value: point.value });
        }
        if (point.index > 1 && point.movingRange > limits.mrUCL) {
            ooc.push({ subgroup: point.index, type: "mr", rule: "Rule 1: Beyond UCL", value: point.movingRange });
        }
    });

    // Rule 2: Two of three beyond 2σ on same side
    for (let i = 2; i < data.length; i++) {
        const window = [data[i - 2], data[i - 1], data[i]];
        const upperCount = window.filter(p => p.value > sigma2Upper).length;
        const lowerCount = window.filter(p => p.value < sigma2Lower).length;

        if (upperCount >= 2 && !isAlreadyFlagged(data[i].index, "individual")) {
            ooc.push({ subgroup: data[i].index, type: "individual", rule: "Rule 2: 2 of 3 beyond 2σ", value: data[i].value });
        }
        if (lowerCount >= 2 && !isAlreadyFlagged(data[i].index, "individual")) {
            ooc.push({ subgroup: data[i].index, type: "individual", rule: "Rule 2: 2 of 3 beyond 2σ", value: data[i].value });
        }
    }

    // Rule 3: Four of five beyond 1σ on same side
    for (let i = 4; i < data.length; i++) {
        const window = [data[i - 4], data[i - 3], data[i - 2], data[i - 1], data[i]];
        const upperCount = window.filter(p => p.value > sigma1Upper).length;
        const lowerCount = window.filter(p => p.value < sigma1Lower).length;

        if (upperCount >= 4 && !isAlreadyFlagged(data[i].index, "individual")) {
            ooc.push({ subgroup: data[i].index, type: "individual", rule: "Rule 3: 4 of 5 beyond 1σ", value: data[i].value });
        }
        if (lowerCount >= 4 && !isAlreadyFlagged(data[i].index, "individual")) {
            ooc.push({ subgroup: data[i].index, type: "individual", rule: "Rule 3: 4 of 5 beyond 1σ", value: data[i].value });
        }
    }

    // Rule 4: Eight consecutive points on one side
    for (let i = 7; i < data.length; i++) {
        const window = data.slice(i - 7, i + 1);
        const allAbove = window.every(p => p.value > limits.individualCL);
        const allBelow = window.every(p => p.value < limits.individualCL);

        if ((allAbove || allBelow) && !isAlreadyFlagged(data[i].index, "individual")) {
            ooc.push({ subgroup: data[i].index, type: "individual", rule: "Rule 4: 8 same side", value: data[i].value });
        }
    }

    // Rule 5: Six consecutive trending
    for (let i = 5; i < data.length; i++) {
        let increasing = true;
        let decreasing = true;
        for (let j = i - 4; j <= i; j++) {
            if (data[j].value <= data[j - 1].value) increasing = false;
            if (data[j].value >= data[j - 1].value) decreasing = false;
        }
        if ((increasing || decreasing) && !isAlreadyFlagged(data[i].index, "individual")) {
            ooc.push({ subgroup: data[i].index, type: "individual", rule: "Rule 5: 6-point trend", value: data[i].value });
        }
    }

    return ooc;
}

// ---------- Calculate control limits for X̄-R charts ----------
function calculateXbarRLimits(data: SubgroupPoint[], subgroupSize: number): ControlLimits {
    const constants = getXbarRConstants(subgroupSize);
    const xBarBar = data.reduce((sum, d) => sum + d.xBar, 0) / data.length;
    const rBar = data.reduce((sum, d) => sum + d.range, 0) / data.length;

    return {
        xBarUCL: Math.round((xBarBar + constants.A2 * rBar) * 1000) / 1000,
        xBarLCL: Math.round((xBarBar - constants.A2 * rBar) * 1000) / 1000,
        xBarCL: Math.round(xBarBar * 1000) / 1000,
        rangeUCL: Math.round((constants.D4 * rBar) * 1000) / 1000,
        rangeLCL: Math.round((constants.D3 * rBar) * 1000) / 1000,
        rangeCL: Math.round(rBar * 1000) / 1000,
    };
}

// ---------- Calculate control limits for X̄-S charts ----------
function calculateXbarSLimits(data: SubgroupPoint[], subgroupSize: number): ControlLimits {
    const constants = getXbarSConstants(subgroupSize);
    const xBarBar = data.reduce((sum, d) => sum + d.xBar, 0) / data.length;
    const sBar = data.reduce((sum, d) => sum + d.stdDev, 0) / data.length;

    return {
        xBarUCL: Math.round((xBarBar + constants.A3 * sBar) * 1000) / 1000,
        xBarLCL: Math.round((xBarBar - constants.A3 * sBar) * 1000) / 1000,
        xBarCL: Math.round(xBarBar * 1000) / 1000,
        // For S chart, we reuse range fields for stdDev limits
        rangeUCL: Math.round((constants.B4 * sBar) * 1000) / 1000,
        rangeLCL: Math.round((constants.B3 * sBar) * 1000) / 1000,
        rangeCL: Math.round(sBar * 1000) / 1000,
    };
}

// Unified function to calculate control limits based on chart type
function calculateControlLimits(data: SubgroupPoint[], subgroupSize: number, chartType: SubgroupChartType): ControlLimits {
    return chartType === "xbar-s"
        ? calculateXbarSLimits(data, subgroupSize)
        : calculateXbarRLimits(data, subgroupSize);
}

// ---------- Detect out-of-control points (Western Electric Rules) ----------
function detectOutOfControl(data: SubgroupPoint[], limits: ControlLimits): OutOfControlPoint[] {
    const ooc: OutOfControlPoint[] = [];

    // Helper to check if a point is already flagged for a specific rule type
    const isAlreadyFlagged = (subgroup: number, type: "xBar" | "range") =>
        ooc.some(o => o.subgroup === subgroup && o.type === type);

    // Calculate zone boundaries for X-bar chart
    const xBarSigma = (limits.xBarUCL - limits.xBarCL) / 3;
    const xBar1SigmaUpper = limits.xBarCL + xBarSigma;
    const xBar1SigmaLower = limits.xBarCL - xBarSigma;
    const xBar2SigmaUpper = limits.xBarCL + 2 * xBarSigma;
    const xBar2SigmaLower = limits.xBarCL - 2 * xBarSigma;

    // Calculate zone boundaries for Range chart
    const rangeSigma = (limits.rangeUCL - limits.rangeCL) / 3;
    const range1SigmaUpper = limits.rangeCL + rangeSigma;
    const range2SigmaUpper = limits.rangeCL + 2 * rangeSigma;

    // Rule 1: One point beyond 3σ (Zone A)
    data.forEach((point) => {
        if (point.xBar > limits.xBarUCL || point.xBar < limits.xBarLCL) {
            ooc.push({ subgroup: point.subgroup, type: "xBar", rule: "Rule 1: Beyond 3σ", value: point.xBar });
        }
        if (point.range > limits.rangeUCL) {
            ooc.push({ subgroup: point.subgroup, type: "range", rule: "Rule 1: Beyond UCL", value: point.range });
        }
    });

    // Rule 2: Two out of three consecutive points beyond 2σ on same side (Zone A or B)
    for (let i = 2; i < data.length; i++) {
        const window = [data[i - 2], data[i - 1], data[i]];

        // Check upper side for X-bar
        const upperCount = window.filter(p => p.xBar > xBar2SigmaUpper).length;
        if (upperCount >= 2 && !isAlreadyFlagged(data[i].subgroup, "xBar")) {
            ooc.push({ subgroup: data[i].subgroup, type: "xBar", rule: "Rule 2: 2 of 3 beyond 2σ", value: data[i].xBar });
        }

        // Check lower side for X-bar
        const lowerCount = window.filter(p => p.xBar < xBar2SigmaLower).length;
        if (lowerCount >= 2 && !isAlreadyFlagged(data[i].subgroup, "xBar")) {
            ooc.push({ subgroup: data[i].subgroup, type: "xBar", rule: "Rule 2: 2 of 3 beyond 2σ", value: data[i].xBar });
        }

        // Check Range chart (upper only)
        const rangeUpperCount = window.filter(p => p.range > range2SigmaUpper).length;
        if (rangeUpperCount >= 2 && !isAlreadyFlagged(data[i].subgroup, "range")) {
            ooc.push({ subgroup: data[i].subgroup, type: "range", rule: "Rule 2: 2 of 3 beyond 2σ", value: data[i].range });
        }
    }

    // Rule 3: Four out of five consecutive points beyond 1σ on same side (Zone B or beyond)
    for (let i = 4; i < data.length; i++) {
        const window = [data[i - 4], data[i - 3], data[i - 2], data[i - 1], data[i]];

        // Check upper side for X-bar
        const upperCount = window.filter(p => p.xBar > xBar1SigmaUpper).length;
        if (upperCount >= 4 && !isAlreadyFlagged(data[i].subgroup, "xBar")) {
            ooc.push({ subgroup: data[i].subgroup, type: "xBar", rule: "Rule 3: 4 of 5 beyond 1σ", value: data[i].xBar });
        }

        // Check lower side for X-bar
        const lowerCount = window.filter(p => p.xBar < xBar1SigmaLower).length;
        if (lowerCount >= 4 && !isAlreadyFlagged(data[i].subgroup, "xBar")) {
            ooc.push({ subgroup: data[i].subgroup, type: "xBar", rule: "Rule 3: 4 of 5 beyond 1σ", value: data[i].xBar });
        }

        // Check Range chart (upper only)
        const rangeUpperCount = window.filter(p => p.range > range1SigmaUpper).length;
        if (rangeUpperCount >= 4 && !isAlreadyFlagged(data[i].subgroup, "range")) {
            ooc.push({ subgroup: data[i].subgroup, type: "range", rule: "Rule 3: 4 of 5 beyond 1σ", value: data[i].range });
        }
    }

    // Rule 4: Eight consecutive points on one side of centerline
    for (let i = 7; i < data.length; i++) {
        const window = data.slice(i - 7, i + 1);

        // Check X-bar
        const allAbove = window.every(p => p.xBar > limits.xBarCL);
        const allBelow = window.every(p => p.xBar < limits.xBarCL);
        if ((allAbove || allBelow) && !isAlreadyFlagged(data[i].subgroup, "xBar")) {
            ooc.push({ subgroup: data[i].subgroup, type: "xBar", rule: "Rule 4: 8 same side", value: data[i].xBar });
        }

        // Check Range
        const rangeAllAbove = window.every(p => p.range > limits.rangeCL);
        const rangeAllBelow = window.every(p => p.range < limits.rangeCL);
        if ((rangeAllAbove || rangeAllBelow) && !isAlreadyFlagged(data[i].subgroup, "range")) {
            ooc.push({ subgroup: data[i].subgroup, type: "range", rule: "Rule 4: 8 same side", value: data[i].range });
        }
    }

    // Rule 5: Six consecutive points steadily increasing or decreasing (trend)
    for (let i = 5; i < data.length; i++) {
        // Check increasing trend for X-bar
        let increasing = true;
        let decreasing = true;
        for (let j = i - 4; j <= i; j++) {
            if (data[j].xBar <= data[j - 1].xBar) increasing = false;
            if (data[j].xBar >= data[j - 1].xBar) decreasing = false;
        }
        if ((increasing || decreasing) && !isAlreadyFlagged(data[i].subgroup, "xBar")) {
            ooc.push({ subgroup: data[i].subgroup, type: "xBar", rule: "Rule 5: 6-point trend", value: data[i].xBar });
        }
    }

    // Rule 6: Fourteen consecutive points alternating up and down
    for (let i = 13; i < data.length; i++) {
        let alternating = true;
        for (let j = i - 12; j <= i; j++) {
            const prevDiff = data[j - 1].xBar - data[j - 2]?.xBar;
            const currDiff = data[j].xBar - data[j - 1].xBar;
            if (j > i - 12 && prevDiff * currDiff >= 0) {
                alternating = false;
                break;
            }
        }
        if (alternating && !isAlreadyFlagged(data[i].subgroup, "xBar")) {
            ooc.push({ subgroup: data[i].subgroup, type: "xBar", rule: "Rule 6: 14 alternating", value: data[i].xBar });
        }
    }

    // Rule 7: Fifteen consecutive points within 1σ (stratification - hugging centerline)
    for (let i = 14; i < data.length; i++) {
        const window = data.slice(i - 14, i + 1);
        const allWithin1Sigma = window.every(p => p.xBar > xBar1SigmaLower && p.xBar < xBar1SigmaUpper);
        if (allWithin1Sigma && !isAlreadyFlagged(data[i].subgroup, "xBar")) {
            ooc.push({ subgroup: data[i].subgroup, type: "xBar", rule: "Rule 7: 15 within 1σ", value: data[i].xBar });
        }
    }

    // Rule 8: Eight consecutive points beyond 1σ on either side (mixture pattern)
    for (let i = 7; i < data.length; i++) {
        const window = data.slice(i - 7, i + 1);
        const allBeyond1Sigma = window.every(p => p.xBar > xBar1SigmaUpper || p.xBar < xBar1SigmaLower);
        if (allBeyond1Sigma && !isAlreadyFlagged(data[i].subgroup, "xBar")) {
            ooc.push({ subgroup: data[i].subgroup, type: "xBar", rule: "Rule 8: 8 beyond 1σ", value: data[i].xBar });
        }
    }

    return ooc;
}

// ---------- Calculate process capability ----------
function calculateCapability(
    data: SubgroupPoint[],
    limits: ControlLimits,
    measurementDef: MeasurementDef,
    subgroupSize: number,
    chartType: SubgroupChartType
): { cp: number; cpk: number; pp: number; ppk: number; sigma: number } {
    // Estimate sigma based on chart type
    let sigma: number;
    if (chartType === "xbar-s") {
        const constants = getXbarSConstants(subgroupSize);
        sigma = limits.rangeCL / constants.c4; // rangeCL holds sBar for X̄-S charts
    } else {
        const constants = getXbarRConstants(subgroupSize);
        sigma = limits.rangeCL / constants.d2;
    }

    const usl = measurementDef.nominal + measurementDef.tolerancePlus;
    const lsl = measurementDef.nominal - Math.abs(measurementDef.toleranceMinus);
    const tolerance = usl - lsl;

    const cp = tolerance / (6 * sigma);
    const cpupper = (usl - limits.xBarCL) / (3 * sigma);
    const cplower = (limits.xBarCL - lsl) / (3 * sigma);
    const cpk = Math.min(cpupper, cplower);

    // Pp/Ppk using overall standard deviation
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

// ---------- Chart configs ----------
const xBarChartConfig = {
    xBar: { label: "X-bar", color: "var(--chart-1)" },
    ucl: { label: "UCL", color: "var(--destructive)" },
    lcl: { label: "LCL", color: "var(--destructive)" },
    cl: { label: "CL", color: "var(--chart-3)" },
} as const;

const rangeChartConfig = {
    range: { label: "Range", color: "var(--chart-2)" },
    ucl: { label: "UCL", color: "var(--destructive)" },
    cl: { label: "CL", color: "var(--chart-3)" },
} as const;

const stdDevChartConfig = {
    stdDev: { label: "Std Dev (S)", color: "var(--chart-2)" },
    ucl: { label: "UCL", color: "var(--destructive)" },
    lcl: { label: "LCL", color: "var(--destructive)" },
    cl: { label: "CL", color: "var(--chart-3)" },
} as const;

const individualChartConfig = {
    value: { label: "Individual", color: "var(--chart-1)" },
    ucl: { label: "UCL", color: "var(--destructive)" },
    lcl: { label: "LCL", color: "var(--destructive)" },
    cl: { label: "CL", color: "var(--chart-3)" },
} as const;

const mrChartConfig = {
    movingRange: { label: "Moving Range", color: "var(--chart-2)" },
    ucl: { label: "UCL", color: "var(--destructive)" },
    cl: { label: "CL", color: "var(--chart-3)" },
} as const;

// ---------- Histogram data generator ----------
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

// ---------- Component ----------
export default function SpcPage() {
    const navigate = useNavigate();
    const [selectedProcessId, setSelectedProcessId] = useState<string | null>(null);
    const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
    const [selectedMeasurementId, setSelectedMeasurementId] = useState<string | null>(null);
    const [selectedPoint, setSelectedPoint] = useState<SubgroupPoint | null>(null);
    const [selectedIMRPoint, setSelectedIMRPoint] = useState<IndividualPoint | null>(null);
    const [chartMode, setChartMode] = useState<ChartMode>("xbar-r");

    // SPC configuration controls
    const [dateRange, setDateRange] = useState<number>(90); // days
    const [subgroupSize, setSubgroupSize] = useState<number>(5);

    // Auto-select chart type based on subgroup size (X̄-R for n≤8, X̄-S for n>8)
    const subgroupChartType: SubgroupChartType = useMemo(() =>
        getRecommendedChartType(subgroupSize), [subgroupSize]);

    // Help dialog
    const [showHelp, setShowHelp] = useState(false);

    // API Hooks
    const { data: processData, isLoading: isLoadingHierarchy } = useSpcHierarchy();

    // SPC Baseline hooks - persist frozen limits to backend
    const { data: activeBaseline, isLoading: isLoadingBaseline } = useSpcActiveBaseline(selectedMeasurementId);
    const freezeBaselineMutation = useFreezeSpcBaseline();
    const supersedeBaselineMutation = useSupersedeSpcBaseline();

    // Derive frozen limits from active baseline (if exists)
    const frozenLimits: ControlLimits | null = useMemo(() => {
        if (!activeBaseline || activeBaseline.chart_type === "I_MR") return null;
        const limits = activeBaseline.control_limits;
        if (!limits.xBarUCL || !limits.xBarLCL || !limits.xBarCL) return null;
        return {
            xBarUCL: limits.xBarUCL,
            xBarLCL: limits.xBarLCL,
            xBarCL: limits.xBarCL,
            rangeUCL: limits.rangeUCL ?? 0,
            rangeLCL: limits.rangeLCL ?? 0,
            rangeCL: limits.rangeCL ?? 0,
        };
    }, [activeBaseline]);

    const frozenIMRLimits: IMRControlLimits | null = useMemo(() => {
        if (!activeBaseline || activeBaseline.chart_type !== "I_MR") return null;
        const limits = activeBaseline.control_limits;
        if (!limits.individualUCL || !limits.individualLCL || !limits.individualCL) return null;
        return {
            individualUCL: limits.individualUCL,
            individualLCL: limits.individualLCL,
            individualCL: limits.individualCL,
            mrUCL: limits.mrUCL ?? 0,
            mrCL: limits.mrCL ?? 0,
        };
    }, [activeBaseline]);

    // Baseline vs Monitoring mode - derived from whether an active baseline exists
    const spcMode: "baseline" | "monitoring" = activeBaseline ? "monitoring" : "baseline";
    const { data: spcApiData, isLoading: isLoadingSpcData, error: spcDataError, status: spcDataStatus } = useSpcData({
        measurementId: selectedMeasurementId,
        days: dateRange,
        limit: 1000,
        enabled: selectedMeasurementId !== null,
    });
    const { data: capabilityData, error: capabilityError } = useSpcCapability({
        measurementId: selectedMeasurementId,
        days: dateRange,
        enabled: selectedMeasurementId !== null,
    });

    // Report email hook
    const { requestReport, isRequesting } = useReportEmail();

    // Initialize selections when hierarchy loads
    useEffect(() => {
        if (processData && processData.length > 0 && selectedProcessId === null) {
            const firstProcess = processData[0];
            setSelectedProcessId(firstProcess.id);
            if (firstProcess.steps.length > 0) {
                setSelectedStepId(firstProcess.steps[0].id);
                if (firstProcess.steps[0].measurements.length > 0) {
                    setSelectedMeasurementId(firstProcess.steps[0].measurements[0].id);
                }
            }
        }
    }, [processData, selectedProcessId]);

    const handleEmailReport = () => {
        if (selectedProcessId && selectedStepId && selectedMeasurementId) {
            requestReport("spc", {
                process_id: selectedProcessId,
                step_id: selectedStepId,
                measurement_id: selectedMeasurementId,
                mode: chartMode
            });
        }
    };

    const selectedProcess = processData?.find(p => p.id === selectedProcessId);
    const selectedStep = selectedProcess?.steps.find(s => s.id === selectedStepId);
    const selectedMeasurement = selectedStep?.measurements.find(m => m.id === selectedMeasurementId);

    // Build measurementDef from API data for compatibility with existing calculations
    // Note: API may return strings, so we parse to ensure numbers for arithmetic
    const measurementDef: MeasurementDef | null = selectedMeasurement ? {
        id: selectedMeasurement.id,
        name: selectedMeasurement.label,
        nominal: Number(selectedMeasurement.nominal) || 0,
        tolerancePlus: Number(selectedMeasurement.upper_tol) || 0,
        toleranceMinus: Number(selectedMeasurement.lower_tol) || 0,
        unit: selectedMeasurement.unit,
    } : null;

    // Reset step when process changes
    const handleProcessChange = (processId: string) => {
        setSelectedProcessId(processId);
        const process = processData?.find(p => p.id === processId);
        if (process && process.steps.length > 0) {
            setSelectedStepId(process.steps[0].id);
            if (process.steps[0].measurements.length > 0) {
                setSelectedMeasurementId(process.steps[0].measurements[0].id);
            }
        }
    };

    // Reset measurement when step changes
    const handleStepChange = (stepId: string) => {
        setSelectedStepId(stepId);
        const step = selectedProcess?.steps.find(s => s.id === stepId);
        if (step && step.measurements.length > 0) {
            setSelectedMeasurementId(step.measurements[0].id);
        } else {
            setSelectedMeasurementId(null);
        }
    };

    // Convert API data to SubgroupPoint format for X-bar/R and X-bar/S charts
    // Uses consecutive subgrouping (standard SPC practice)
    const spcData = useMemo((): SubgroupPoint[] => {
        if (!spcApiData?.data_points || spcApiData.data_points.length === 0 || !measurementDef) {
            return [];
        }

        const points = spcApiData.data_points;
        const subgroups: SubgroupPoint[] = [];

        // Consecutive subgrouping - take n consecutive measurements
        for (let i = 0; i < points.length; i += subgroupSize) {
            const groupPoints = points.slice(i, i + subgroupSize);
            if (groupPoints.length < 2) continue;

            const values = groupPoints.map(p => p.value);
            const xBar = values.reduce((a, b) => a + b, 0) / values.length;
            const range = Math.max(...values) - Math.min(...values);
            // Calculate sample standard deviation for X̄-S charts
            const stdDev = Math.sqrt(
                values.reduce((sum, v) => sum + Math.pow(v - xBar, 2), 0) / (values.length - 1)
            );
            const timestamp = new Date(groupPoints[0].timestamp);

            subgroups.push({
                subgroup: subgroups.length + 1,
                xBar: Math.round(xBar * 1000) / 1000,
                range: Math.round(range * 1000) / 1000,
                stdDev: Math.round(stdDev * 10000) / 10000,
                values,
                timestamp,
                label: timestamp.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
            });
        }

        return subgroups;
    }, [spcApiData, measurementDef, subgroupSize]);

    // Convert API data to IndividualPoint format for I-MR charts
    const imrData = useMemo((): IndividualPoint[] => {
        if (!spcApiData?.data_points || spcApiData.data_points.length === 0) {
            return [];
        }

        return spcApiData.data_points.map((point, i, arr) => {
            const timestamp = new Date(point.timestamp);
            const prevValue = i > 0 ? arr[i - 1].value : point.value;
            const movingRange = Math.abs(point.value - prevValue);

            return {
                index: i + 1,
                value: Math.round(point.value * 1000) / 1000,
                movingRange: i === 0 ? 0 : Math.round(movingRange * 1000) / 1000,
                timestamp,
                label: timestamp.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
            };
        });
    }, [spcApiData]);

    // X-bar/R or X-bar/S calculations (auto-selected based on subgroup size)
    const calculatedLimits = useMemo(() =>
        spcData.length > 0 ? calculateControlLimits(spcData, subgroupSize, subgroupChartType) : null,
        [spcData, subgroupSize, subgroupChartType]
    );

    // Use frozen limits in monitoring mode, calculated limits in baseline mode
    const controlLimits = spcMode === "monitoring" && frozenLimits ? frozenLimits : calculatedLimits;

    // Helper to convert chart mode to API chart type
    const getApiChartType = (mode: ChartMode): ApiChartType => {
        switch (mode) {
            case "xbar-r": return "XBAR_R";
            case "xbar-s": return "XBAR_S";
            case "i-mr": return "I_MR";
        }
    };

    // Freeze current limits as baseline (persisted to backend)
    const freezeLimits = () => {
        if (!calculatedLimits || !selectedMeasurementId) return;

        const request = toFreezeRequest(
            selectedMeasurementId,
            getApiChartType(chartMode),
            subgroupSize,
            {
                xBarUCL: calculatedLimits.xBarUCL,
                xBarLCL: calculatedLimits.xBarLCL,
                xBarCL: calculatedLimits.xBarCL,
                rangeUCL: calculatedLimits.rangeUCL,
                rangeLCL: calculatedLimits.rangeLCL,
                rangeCL: calculatedLimits.rangeCL,
            },
            spcData.length * subgroupSize, // sample count
        );

        freezeBaselineMutation.mutate(request);
    };

    // Freeze IMR limits (persisted to backend)
    const freezeIMRLimits = () => {
        if (!calculatedIMRLimits || !selectedMeasurementId) return;

        const request = toFreezeRequest(
            selectedMeasurementId,
            "I_MR",
            1, // subgroup size is always 1 for I-MR
            {
                individualUCL: calculatedIMRLimits.individualUCL,
                individualLCL: calculatedIMRLimits.individualLCL,
                individualCL: calculatedIMRLimits.individualCL,
                mrUCL: calculatedIMRLimits.mrUCL,
                mrCL: calculatedIMRLimits.mrCL,
            },
            imrData.length, // sample count
        );

        freezeBaselineMutation.mutate(request);
    };

    // Clear frozen limits and return to baseline mode (supersedes backend baseline)
    const clearFrozenLimits = () => {
        if (!activeBaseline) return;
        supersedeBaselineMutation.mutate({
            id: activeBaseline.id,
            reason: "User requested unfreeze from SPC page",
        });
    };

    const outOfControl = useMemo(() => controlLimits ? detectOutOfControl(spcData, controlLimits) : [], [spcData, controlLimits]);

    // Use API capability data if available, otherwise calculate from local data
    const capability = useMemo(() => {
        if (capabilityData && capabilityData.cpk !== undefined && capabilityData.cpk !== null) {
            return {
                cp: capabilityData.cp ?? 0,
                cpk: capabilityData.cpk ?? 0,
                pp: capabilityData.pp ?? 0,
                ppk: capabilityData.ppk ?? 0,
                sigma: capabilityData.std_dev_within ?? 0,
            };
        }
        if (spcData.length > 0 && controlLimits && measurementDef) {
            return calculateCapability(spcData, controlLimits, measurementDef, subgroupSize, subgroupChartType);
        }
        return { cp: 0, cpk: 0, pp: 0, ppk: 0, sigma: 0 };
    }, [capabilityData, spcData, controlLimits, measurementDef, subgroupSize, subgroupChartType]);

    const histogramData = useMemo(() => {
        if (spcData.length > 0 && measurementDef) {
            return generateHistogramData(spcData, measurementDef);
        }
        return { bins: [], lsl: 0, usl: 0 };
    }, [spcData, measurementDef]);

    // I-MR calculations
    const calculatedIMRLimits = useMemo(() => imrData.length > 1 ? calculateIMRControlLimits(imrData) : null, [imrData]);

    // Use frozen IMR limits in monitoring mode
    const imrControlLimits = spcMode === "monitoring" && frozenIMRLimits ? frozenIMRLimits : calculatedIMRLimits;

    const imrOutOfControl = useMemo(() => imrControlLimits ? detectIMROutOfControl(imrData, imrControlLimits) : [], [imrData, imrControlLimits]);

    // Active data based on chart mode (xbar-r and xbar-s share the same out-of-control detection)
    const activeOutOfControl = chartMode === "i-mr" ? imrOutOfControl : outOfControl;

    // Calculate spec limits
    const usl = measurementDef ? measurementDef.nominal + measurementDef.tolerancePlus : 0;
    const lsl = measurementDef ? measurementDef.nominal - Math.abs(measurementDef.toleranceMinus) : 0;

    // Loading state
    if (isLoadingHierarchy) {
        return (
            <div className="container mx-auto p-5 flex items-center justify-center min-h-[400px]">
                <div className="flex flex-col items-center gap-2">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Loading SPC data...</p>
                </div>
            </div>
        );
    }

    // No data state
    if (!processData || processData.length === 0) {
        return (
            <div className="container mx-auto p-5">
                <Card className="border-muted/40">
                    <CardContent className="flex flex-col items-center justify-center py-12">
                        <Activity className="h-12 w-12 text-muted-foreground mb-4" />
                        <h2 className="text-lg font-semibold mb-2">No SPC Data Available</h2>
                        <p className="text-sm text-muted-foreground text-center max-w-md">
                            No processes with numeric measurement definitions were found.
                            Create measurement definitions for your process steps to enable SPC analysis.
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Guard against null selections
    if (!selectedProcess || !selectedStep || !measurementDef) {
        return (
            <div className="container mx-auto p-5 flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    const isProcessCapable = capability.cpk >= 1.33;
    const hasOutOfControl = activeOutOfControl.length > 0;

    // Get violations for selected point (X-bar/R mode)
    const selectedPointViolations = selectedPoint
        ? outOfControl.filter(o => o.subgroup === selectedPoint.subgroup)
        : [];

    // Get violations for selected I-MR point
    const selectedIMRPointViolations = selectedIMRPoint
        ? imrOutOfControl.filter(o => o.subgroup === selectedIMRPoint.index)
        : [];

    // Handle creating CAPA from OOC point (X-bar/R)
    const handleInvestigate = () => {
        if (!selectedPoint) return;

        const violations = selectedPointViolations.map(v => v.rule).join(", ");
        const problemStatement = `SPC Out-of-Control Condition Detected

Process: ${selectedProcess.name}
Step: ${selectedStep.name}
Measurement: ${measurementDef.name}
Subgroup: ${selectedPoint.subgroup}
Date: ${selectedPoint.timestamp.toLocaleDateString()}

Violation(s): ${violations || "Manual investigation requested"}

X-bar Value: ${selectedPoint.xBar.toFixed(4)} ${measurementDef.unit}
Range: ${selectedPoint.range.toFixed(4)} ${measurementDef.unit}
Individual Values: ${selectedPoint.values.map(v => v.toFixed(3)).join(", ")}

Control Limits:
- UCL: ${controlLimits.xBarUCL} ${measurementDef.unit}
- CL: ${controlLimits.xBarCL} ${measurementDef.unit}
- LCL: ${controlLimits.xBarLCL} ${measurementDef.unit}

Specification Limits:
- USL: ${usl.toFixed(3)} ${measurementDef.unit}
- LSL: ${lsl.toFixed(3)} ${measurementDef.unit}`;

        sessionStorage.setItem('spc_capa_problem_statement', problemStatement);
        setSelectedPoint(null);
        navigate({ to: '/quality/capas/new' });
    };

    // Handle creating CAPA from I-MR point
    const handleIMRInvestigate = () => {
        if (!selectedIMRPoint) return;

        const violations = selectedIMRPointViolations.map(v => v.rule).join(", ");
        const problemStatement = `SPC Out-of-Control Condition Detected (I-MR Chart)

Process: ${selectedProcess.name}
Step: ${selectedStep.name}
Measurement: ${measurementDef.name}
Point: ${selectedIMRPoint.index}
Date: ${selectedIMRPoint.timestamp.toLocaleDateString()}

Violation(s): ${violations || "Manual investigation requested"}

Individual Value: ${selectedIMRPoint.value.toFixed(4)} ${measurementDef.unit}
Moving Range: ${selectedIMRPoint.movingRange.toFixed(4)} ${measurementDef.unit}

Control Limits (Individual):
- UCL: ${imrControlLimits.individualUCL} ${measurementDef.unit}
- CL: ${imrControlLimits.individualCL} ${measurementDef.unit}
- LCL: ${imrControlLimits.individualLCL} ${measurementDef.unit}

Control Limits (Moving Range):
- UCL: ${imrControlLimits.mrUCL} ${measurementDef.unit}
- CL: ${imrControlLimits.mrCL} ${measurementDef.unit}

Specification Limits:
- USL: ${usl.toFixed(3)} ${measurementDef.unit}
- LSL: ${lsl.toFixed(3)} ${measurementDef.unit}`;

        sessionStorage.setItem('spc_capa_problem_statement', problemStatement);
        setSelectedIMRPoint(null);
        navigate({ to: '/quality/capas/new' });
    };

    return (
        <div className="container mx-auto p-5 space-y-5">
            {/* Header */}
            <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                    <Link to="/analysis" className="text-sm text-muted-foreground hover:text-foreground">
                        Analytics
                    </Link>
                    <span className="text-muted-foreground">/</span>
                    <span className="text-sm">SPC</span>
                </div>
                <div className="flex items-center justify-between">
                    <h1 className="text-2xl font-semibold tracking-tight">Statistical Process Control</h1>
                    <Button variant="ghost" size="sm" onClick={() => setShowHelp(true)} className="text-muted-foreground">
                        <HelpCircle className="h-4 w-4 mr-1.5" />
                        How to use SPC
                    </Button>
                </div>
                <p className="text-sm text-muted-foreground">
                    {selectedProcess.name} → {selectedStep.name} → {measurementDef.name}
                    {isLoadingSpcData && <Loader2 className="inline-block ml-2 h-3 w-3 animate-spin" />}
                </p>
            </div>

            {/* Help Dialog */}
            <Dialog open={showHelp} onOpenChange={setShowHelp}>
                <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <HelpCircle className="h-5 w-5" />
                            Getting Started with SPC
                        </DialogTitle>
                        <DialogDescription>
                            A quick guide to understanding and using Statistical Process Control
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-6 py-4">
                        {/* What is SPC */}
                        <div>
                            <h3 className="font-semibold text-base mb-2">What is SPC?</h3>
                            <p className="text-sm text-muted-foreground">
                                Statistical Process Control helps you monitor your manufacturing process to catch problems early.
                                Instead of checking if parts are "good" or "bad," SPC watches for <strong>changes in the pattern</strong> that
                                might lead to problems before they happen.
                            </p>
                        </div>

                        {/* Reading the Charts */}
                        <div>
                            <h3 className="font-semibold text-base mb-2">Reading the Charts</h3>
                            <div className="space-y-3 text-sm text-muted-foreground">
                                <div className="flex gap-3">
                                    <div className="w-3 h-3 rounded-full bg-green-500 mt-1 shrink-0" />
                                    <p><strong>Green zone:</strong> Points between the control limits (UCL/LCL) are normal variation. Your process is stable.</p>
                                </div>
                                <div className="flex gap-3">
                                    <div className="w-3 h-3 rounded-full bg-red-500 mt-1 shrink-0" />
                                    <p><strong>Red points:</strong> These violate run rules and need investigation. Something may have changed in your process.</p>
                                </div>
                                <div className="flex gap-3">
                                    <div className="w-3 h-3 rounded-full bg-purple-500 mt-1 shrink-0" />
                                    <p><strong>Spec limits (USL/LSL):</strong> The dashed purple lines show customer requirements. Points should stay well inside these.</p>
                                </div>
                            </div>
                        </div>

                        {/* Key Metrics */}
                        <div>
                            <h3 className="font-semibold text-base mb-2">Key Metrics Explained</h3>
                            <div className="grid grid-cols-2 gap-3 text-sm">
                                <div className="p-3 rounded-lg bg-muted/50">
                                    <p className="font-medium">Cpk (Capability)</p>
                                    <p className="text-muted-foreground text-xs mt-1">
                                        How well your process fits within specs. Target: ≥1.33. Higher = more margin for error.
                                    </p>
                                </div>
                                <div className="p-3 rounded-lg bg-muted/50">
                                    <p className="font-medium">Out of Control</p>
                                    <p className="text-muted-foreground text-xs mt-1">
                                        Number of points that need investigation. Zero is ideal, but occasional flags are normal.
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Quick Start Steps */}
                        <div>
                            <h3 className="font-semibold text-base mb-2">Quick Start</h3>
                            <ol className="space-y-2 text-sm text-muted-foreground list-decimal list-inside">
                                <li><strong>Select your measurement</strong> using the Process → Step → Measurement dropdowns</li>
                                <li><strong>Check the Cpk card</strong> — green checkmark means your process is capable</li>
                                <li><strong>Look for red points</strong> — click them to see details and investigate</li>
                                <li><strong>Once stable, click "Freeze Limits"</strong> to lock your baseline and monitor for changes</li>
                            </ol>
                        </div>

                        {/* When to Take Action */}
                        <div>
                            <h3 className="font-semibold text-base mb-2">When to Take Action</h3>
                            <div className="space-y-2 text-sm text-muted-foreground">
                                <p>🔴 <strong>Investigate immediately:</strong> Points outside control limits (UCL/LCL)</p>
                                <p>🟡 <strong>Watch closely:</strong> Trends, runs of 7+ points on one side, or patterns</p>
                                <p>🟢 <strong>Process is stable:</strong> Random scatter between control limits</p>
                            </div>
                        </div>

                        {/* Pro Tips */}
                        <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900">
                            <h3 className="font-semibold text-base mb-2 text-blue-800 dark:text-blue-200">💡 Pro Tips</h3>
                            <ul className="space-y-1 text-sm text-blue-700 dark:text-blue-300">
                                <li>• Hover over any control or metric for detailed explanations</li>
                                <li>• Use "Freeze Limits" once your process is stable to detect future shifts</li>
                                <li>• Click on flagged points to open a CAPA investigation</li>
                                <li>• Subgroup size of 5 is standard — only change if you have a reason</li>
                            </ul>
                        </div>
                    </div>

                    <div className="flex justify-end">
                        <Button onClick={() => setShowHelp(false)}>Got it</Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Chart Mode Toggle */}
            <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Chart Type:</span>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <div>
                                <Tabs
                                    value={chartMode === "i-mr" ? "i-mr" : "subgroup"}
                                    onValueChange={(v) => setChartMode(v === "subgroup" ? subgroupChartType : "i-mr")}
                                    className="w-auto"
                                >
                                    <TabsList className="h-8">
                                        <TabsTrigger value="subgroup" className="text-xs px-3 h-7">
                                            {subgroupChartType === "xbar-s" ? "X̄-S" : "X̄-R"}
                                            {subgroupSize > 8 && <span className="ml-1 text-[10px] opacity-70">(auto)</span>}
                                        </TabsTrigger>
                                        <TabsTrigger value="i-mr" className="text-xs px-3 h-7">I-MR</TabsTrigger>
                                    </TabsList>
                                </Tabs>
                            </div>
                        </TooltipTrigger>
                        <TooltipContent side="bottom" className="max-w-[280px]">
                            <p className="font-medium mb-1">Chart Types:</p>
                            <p><strong>X̄-R:</strong> For subgroups of 2-8 samples. Uses Range to estimate variation.</p>
                            <p><strong>X̄-S:</strong> For subgroups of 9+. Uses Std Dev for better accuracy.</p>
                            <p><strong>I-MR:</strong> For individual measurements (n=1).</p>
                        </TooltipContent>
                    </Tooltip>
                </div>

                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Date Range:</span>
                    <Select value={dateRange.toString()} onValueChange={(v) => setDateRange(parseInt(v))}>
                        <SelectTrigger className="w-[120px] h-8">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="30">Last 30 days</SelectItem>
                            <SelectItem value="60">Last 60 days</SelectItem>
                            <SelectItem value="90">Last 90 days</SelectItem>
                            <SelectItem value="180">Last 180 days</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                {chartMode !== "i-mr" && (
                    <>
                        <div className="flex items-center gap-2">
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <span className="text-sm font-medium flex items-center gap-1 cursor-help">
                                        Subgroup Size (n):
                                        <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                                    </span>
                                </TooltipTrigger>
                                <TooltipContent side="bottom" className="max-w-[260px]">
                                    <p>Number of consecutive measurements grouped together. Standard practice is n=3-5.</p>
                                    <p className="mt-1 text-muted-foreground">Larger subgroups detect smaller shifts but require more samples.</p>
                                </TooltipContent>
                            </Tooltip>
                            <Select value={subgroupSize.toString()} onValueChange={(v) => setSubgroupSize(parseInt(v))}>
                                <SelectTrigger className="w-[80px] h-8">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="2">2</SelectItem>
                                    <SelectItem value="3">3</SelectItem>
                                    <SelectItem value="4">4</SelectItem>
                                    <SelectItem value="5">5</SelectItem>
                                    <SelectItem value="6">6</SelectItem>
                                    <SelectItem value="7">7</SelectItem>
                                    <SelectItem value="8">8</SelectItem>
                                    <SelectItem value="9">9</SelectItem>
                                    <SelectItem value="10">10</SelectItem>
                                    <SelectItem value="15">15</SelectItem>
                                    <SelectItem value="20">20</SelectItem>
                                    <SelectItem value="25">25</SelectItem>
                                </SelectContent>
                            </Select>
                            {subgroupSize > 8 && (
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <Badge variant="secondary" className="text-[10px] cursor-help">
                                            Using S chart (n&gt;8)
                                        </Badge>
                                    </TooltipTrigger>
                                    <TooltipContent side="bottom" className="max-w-[240px]">
                                        <p>For subgroups larger than 8, the S chart (standard deviation) is more accurate than the R chart (range).</p>
                                    </TooltipContent>
                                </Tooltip>
                            )}
                        </div>
                    </>
                )}

                {/* Baseline vs Monitoring Mode */}
                <div className="flex items-center gap-2 ml-auto">
                    {spcMode === "baseline" ? (
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => chartMode === "i-mr" ? freezeIMRLimits() : freezeLimits()}
                                    disabled={
                                        freezeBaselineMutation.isPending ||
                                        (chartMode === "i-mr" ? !calculatedIMRLimits : !calculatedLimits)
                                    }
                                    className="h-8"
                                >
                                    {freezeBaselineMutation.isPending ? (
                                        <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                                    ) : (
                                        <Lock className="h-3.5 w-3.5 mr-1.5" />
                                    )}
                                    {freezeBaselineMutation.isPending ? "Freezing..." : "Freeze Limits"}
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent side="bottom" className="max-w-[280px]">
                                <p className="font-medium">Freeze Control Limits</p>
                                <p className="mt-1">Lock the current control limits as a baseline. New data will be monitored against these fixed limits instead of recalculating.</p>
                                <p className="mt-1 text-muted-foreground">Use this once your process is stable and you want to detect future shifts.</p>
                            </TooltipContent>
                        </Tooltip>
                    ) : (
                        <>
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <Badge variant="default" className="bg-blue-600 text-[10px] cursor-help">
                                        <Lock className="h-3 w-3 mr-1" />
                                        Monitoring Mode
                                    </Badge>
                                </TooltipTrigger>
                                <TooltipContent side="bottom" className="max-w-[260px]">
                                    <p className="font-medium">Monitoring Mode Active</p>
                                    <p className="mt-1">Control limits are frozen from a baseline period. Out-of-control signals indicate the process has shifted from baseline.</p>
                                </TooltipContent>
                            </Tooltip>
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={clearFrozenLimits}
                                        disabled={supersedeBaselineMutation.isPending}
                                        className="h-8"
                                    >
                                        {supersedeBaselineMutation.isPending ? (
                                            <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                                        ) : (
                                            <Unlock className="h-3.5 w-3.5 mr-1.5" />
                                        )}
                                        {supersedeBaselineMutation.isPending ? "Unfreezing..." : "Unfreeze"}
                                    </Button>
                                </TooltipTrigger>
                                <TooltipContent side="bottom">
                                    <p>Return to baseline mode with recalculated limits</p>
                                </TooltipContent>
                            </Tooltip>
                        </>
                    )}
                </div>
            </div>

            {/* Controls */}
            <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Process:</span>
                    <Select
                        value={selectedProcessId?.toString() ?? ""}
                        onValueChange={(v) => handleProcessChange(v)}
                    >
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="Select process" />
                        </SelectTrigger>
                        <SelectContent>
                            {processData?.map((p) => (
                                <SelectItem key={p.id} value={p.id.toString()}>
                                    {p.name}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Step:</span>
                    <Select
                        value={selectedStepId?.toString() ?? ""}
                        onValueChange={(v) => handleStepChange(v)}
                    >
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="Select step" />
                        </SelectTrigger>
                        <SelectContent>
                            {selectedProcess?.steps.map((s) => (
                                <SelectItem key={s.id} value={s.id.toString()}>
                                    {s.name}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Measurement:</span>
                    <Select
                        value={selectedMeasurementId?.toString() ?? ""}
                        onValueChange={(v) => setSelectedMeasurementId(v)}
                    >
                        <SelectTrigger className="w-[200px]">
                            <SelectValue placeholder="Select measurement" />
                        </SelectTrigger>
                        <SelectContent>
                            {selectedStep.measurements.map((m) => (
                                <SelectItem key={m.id} value={m.id.toString()}>
                                    {m.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                {/* Email Report Button */}
                <Button
                    variant="outline"
                    size="sm"
                    onClick={handleEmailReport}
                    disabled={isRequesting}
                    className="ml-auto"
                >
                    <Mail className="h-4 w-4 mr-2" />
                    {isRequesting ? "Requesting..." : "Email Report"}
                </Button>
            </div>

            {/* Specification badges with tooltips */}
            <div className="flex flex-wrap items-center gap-2">
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Badge variant="outline" className="font-mono cursor-help">
                            Nominal: {measurementDef.nominal} {measurementDef.unit}
                        </Badge>
                    </TooltipTrigger>
                    <TooltipContent>The target value for this measurement</TooltipContent>
                </Tooltip>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Badge variant="outline" className="font-mono cursor-help">
                            Tolerance: +{measurementDef.tolerancePlus}/-{Math.abs(measurementDef.toleranceMinus)} {measurementDef.unit}
                        </Badge>
                    </TooltipTrigger>
                    <TooltipContent>Acceptable deviation from nominal (+ above, - below)</TooltipContent>
                </Tooltip>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Badge variant="secondary" className="font-mono cursor-help">
                            USL: {(measurementDef.nominal + measurementDef.tolerancePlus).toFixed(3)} {measurementDef.unit}
                        </Badge>
                    </TooltipTrigger>
                    <TooltipContent>Upper Spec Limit — maximum acceptable value</TooltipContent>
                </Tooltip>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Badge variant="secondary" className="font-mono cursor-help">
                            LSL: {(measurementDef.nominal - Math.abs(measurementDef.toleranceMinus)).toFixed(3)} {measurementDef.unit}
                        </Badge>
                    </TooltipTrigger>
                    <TooltipContent>Lower Spec Limit — minimum acceptable value</TooltipContent>
                </Tooltip>
            </div>

            {/* Process Health Summary - Plain English interpretation */}
            {spcData.length > 0 && (
                <Card className={`border-l-4 ${
                    hasOutOfControl
                        ? "border-l-destructive bg-destructive/5"
                        : isProcessCapable
                            ? "border-l-green-500 bg-green-50 dark:bg-green-950/20"
                            : "border-l-yellow-500 bg-yellow-50 dark:bg-yellow-950/20"
                }`}>
                    <CardContent className="py-4">
                        <div className="flex items-start gap-4">
                            <div className={`rounded-full p-2 ${
                                hasOutOfControl
                                    ? "bg-destructive/10 text-destructive"
                                    : isProcessCapable
                                        ? "bg-green-100 dark:bg-green-900/30 text-green-600"
                                        : "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600"
                            }`}>
                                {hasOutOfControl ? (
                                    <AlertTriangle className="h-5 w-5" />
                                ) : isProcessCapable ? (
                                    <CheckCircle className="h-5 w-5" />
                                ) : (
                                    <AlertTriangle className="h-5 w-5" />
                                )}
                            </div>
                            <div className="flex-1">
                                <h3 className="font-semibold text-sm">
                                    {hasOutOfControl
                                        ? "Action Needed"
                                        : isProcessCapable
                                            ? "Process Healthy"
                                            : "Monitor Closely"}
                                </h3>
                                <p className="text-sm text-muted-foreground mt-1">
                                    {hasOutOfControl ? (
                                        <>
                                            <strong>{activeOutOfControl.length} point{activeOutOfControl.length !== 1 ? "s" : ""}</strong> show unusual variation.
                                            Click on red points in the chart to investigate.
                                        </>
                                    ) : isProcessCapable ? (
                                        <>
                                            Your process is stable and capable. Measurements are consistently within specification limits
                                            with good margin (Cpk = {capability.cpk.toFixed(2)}).
                                        </>
                                    ) : (
                                        <>
                                            Process is stable but capability is below target (Cpk = {capability.cpk.toFixed(2)}, target ≥1.33).
                                            Consider process improvements to reduce variation.
                                        </>
                                    )}
                                </p>
                                {/* Contextual Next Steps */}
                                <div className="mt-3 pt-3 border-t border-border/50">
                                    <p className="text-xs font-medium mb-1">Next Step:</p>
                                    <p className="text-xs text-muted-foreground">
                                        {hasOutOfControl ? (
                                            <>Click on any red point in the chart below, then select "Create CAPA" to start an investigation.</>
                                        ) : spcMode === "baseline" && isProcessCapable ? (
                                            <>Your process is stable. Click "Freeze Limits" above to lock these control limits and start monitoring for future changes.</>
                                        ) : spcMode === "baseline" && !isProcessCapable ? (
                                            <>Focus on reducing process variation. Check tooling, materials, and methods for sources of inconsistency.</>
                                        ) : spcMode === "monitoring" && !hasOutOfControl ? (
                                            <>Process is running within your baseline. Continue monitoring — any future shifts will trigger out-of-control signals.</>
                                        ) : (
                                            <>Review the charts for patterns and investigate any concerning trends.</>
                                        )}
                                    </p>
                                </div>
                                {hasOutOfControl && (
                                    <p className="text-xs text-muted-foreground mt-2">
                                        💡 Common causes: material changes, equipment wear, operator differences, environmental factors.
                                    </p>
                                )}
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* KPI Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Card className="border-muted/40 cursor-help">
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
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="max-w-[260px]">
                        <p className="font-medium">Process Capability Index (Cpk)</p>
                        <p className="mt-1">Measures how well the process fits within spec limits, accounting for centering.</p>
                        <p className="mt-1 text-muted-foreground">≥1.33 = Capable | ≥1.67 = Excellent</p>
                    </TooltipContent>
                </Tooltip>

                <Tooltip>
                    <TooltipTrigger asChild>
                        <Card className="border-muted/40 cursor-help">
                            <CardHeader className="pb-1 flex flex-row items-center justify-between space-y-0">
                                <CardTitle className="text-xs font-medium text-muted-foreground">Cp</CardTitle>
                                <TrendingUp className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent className="pt-0">
                                <div className="text-2xl font-bold">{capability.cp.toFixed(2)}</div>
                                <p className="text-xs text-muted-foreground">Process potential</p>
                            </CardContent>
                        </Card>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="max-w-[260px]">
                        <p className="font-medium">Process Potential (Cp)</p>
                        <p className="mt-1">Measures process spread vs spec width, assuming perfect centering.</p>
                        <p className="mt-1 text-muted-foreground">If Cp &gt; Cpk, the process is off-center.</p>
                    </TooltipContent>
                </Tooltip>

                <Tooltip>
                    <TooltipTrigger asChild>
                        <Card className="border-muted/40 cursor-help">
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
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="max-w-[280px]">
                        <p className="font-medium">Out of Control Points</p>
                        <p className="mt-1">Points violating Western Electric run rules, indicating special cause variation.</p>
                        <p className="mt-1 text-muted-foreground">Investigate flagged points to find and eliminate root causes.</p>
                    </TooltipContent>
                </Tooltip>

                <Tooltip>
                    <TooltipTrigger asChild>
                        <Card className="border-muted/40 cursor-help">
                            <CardHeader className="pb-1 flex flex-row items-center justify-between space-y-0">
                                <CardTitle className="text-xs font-medium text-muted-foreground">Process σ</CardTitle>
                                <Activity className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent className="pt-0">
                                <div className="text-2xl font-bold">{capability.sigma.toFixed(4)}</div>
                                <p className="text-xs text-muted-foreground">{measurementDef.unit}</p>
                            </CardContent>
                        </Card>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="max-w-[260px]">
                        <p className="font-medium">Process Standard Deviation (σ)</p>
                        <p className="mt-1">Estimated within-subgroup variation. Lower is better.</p>
                        <p className="mt-1 text-muted-foreground">Used to calculate control limits and capability indices.</p>
                    </TooltipContent>
                </Tooltip>
            </div>

            {/* Charts */}
            <Tabs defaultValue="control" className="w-full">
                <TabsList>
                    <TabsTrigger value="control">Control Charts</TabsTrigger>
                    <TabsTrigger value="histogram">Histogram</TabsTrigger>
                    <TabsTrigger value="data">Data Table</TabsTrigger>
                </TabsList>

                <TabsContent value="control" className="space-y-4">
                    {/* No data message */}
                    {spcData.length === 0 && (
                        <Card className="border-muted/40">
                            <CardContent className="flex flex-col items-center justify-center py-12">
                                <Activity className="h-8 w-8 text-muted-foreground mb-3" />
                                <p className="text-sm text-muted-foreground">
                                    {isLoadingSpcData ? "Loading measurement data..." : "No measurement data available for this selection."}
                                </p>
                            </CardContent>
                        </Card>
                    )}

                    {chartMode !== "i-mr" && spcData.length > 0 && controlLimits ? (
                        <>
                    {/* X-bar Chart */}
                    <Card className="border-muted/40">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-base">X̄ Chart (Subgroup Means)</CardTitle>
                            <CardDescription className="text-xs">
                                <span className="text-muted-foreground block mb-1">Tracks the average of each measurement group — watch for shifts in the process center</span>
                                CL: {controlLimits.xBarCL} | UCL: {controlLimits.xBarUCL} | LCL: {controlLimits.xBarLCL} | USL: {usl.toFixed(3)} | LSL: {lsl.toFixed(3)}
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <ChartContainer className="h-[250px] w-full" config={xBarChartConfig}>
                                <LineChart data={spcData} margin={{ left: 8, right: 40, top: 8, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis
                                        dataKey="label"
                                        tickLine={false}
                                        axisLine={false}
                                        tick={{ fontSize: 10 }}
                                        interval="preserveStartEnd"
                                    />
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
                                    <ChartTooltip
                                        content={<ChartTooltipContent formatter={(value) => (value as number).toFixed(4)} />}
                                    />
                                    {/* Spec Limits */}
                                    <ReferenceLine y={usl} stroke="var(--chart-5)" strokeWidth={2} strokeDasharray="8 4" label={{ value: "USL", position: "right", fontSize: 10, fill: "var(--chart-5)" }} />
                                    <ReferenceLine y={lsl} stroke="var(--chart-5)" strokeWidth={2} strokeDasharray="8 4" label={{ value: "LSL", position: "right", fontSize: 10, fill: "var(--chart-5)" }} />
                                    {/* Zone Lines (±1σ, ±2σ) */}
                                    {(() => {
                                        const sigma = (controlLimits.xBarUCL - controlLimits.xBarCL) / 3;
                                        return (
                                            <>
                                                <ReferenceLine y={controlLimits.xBarCL + 2 * sigma} stroke="hsl(var(--muted-foreground))" strokeWidth={1} strokeDasharray="2 4" strokeOpacity={0.5} />
                                                <ReferenceLine y={controlLimits.xBarCL + sigma} stroke="hsl(var(--muted-foreground))" strokeWidth={1} strokeDasharray="2 4" strokeOpacity={0.5} />
                                                <ReferenceLine y={controlLimits.xBarCL - sigma} stroke="hsl(var(--muted-foreground))" strokeWidth={1} strokeDasharray="2 4" strokeOpacity={0.5} />
                                                <ReferenceLine y={controlLimits.xBarCL - 2 * sigma} stroke="hsl(var(--muted-foreground))" strokeWidth={1} strokeDasharray="2 4" strokeOpacity={0.5} />
                                            </>
                                        );
                                    })()}
                                    {/* Control Limits (±3σ) */}
                                    <ReferenceLine y={controlLimits.xBarUCL} stroke="var(--destructive)" strokeDasharray="5 5" label={{ value: "UCL", position: "right", fontSize: 10 }} />
                                    <ReferenceLine y={controlLimits.xBarCL} stroke="var(--chart-3)" strokeWidth={2} label={{ value: "CL", position: "right", fontSize: 10 }} />
                                    <ReferenceLine y={controlLimits.xBarLCL} stroke="var(--destructive)" strokeDasharray="5 5" label={{ value: "LCL", position: "right", fontSize: 10 }} />
                                    <Line
                                        dataKey="xBar"
                                        stroke="var(--chart-1)"
                                        strokeWidth={2}
                                        dot={(props) => {
                                            const isOOC = outOfControl.some(
                                                (o) => o.subgroup === props.payload.subgroup && o.type === "xBar"
                                            );
                                            return (
                                                <circle
                                                    cx={props.cx}
                                                    cy={props.cy}
                                                    r={isOOC ? 6 : 4}
                                                    fill={isOOC ? "var(--destructive)" : "var(--chart-1)"}
                                                    stroke={isOOC ? "var(--destructive)" : "var(--chart-1)"}
                                                    style={{ cursor: "pointer" }}
                                                    onClick={() => setSelectedPoint(props.payload)}
                                                />
                                            );
                                        }}
                                        activeDot={{
                                            r: 6,
                                            style: { cursor: "pointer" },
                                            onClick: (_, payload) => {
                                                if (payload && payload.payload) {
                                                    setSelectedPoint(payload.payload as SubgroupPoint);
                                                }
                                            }
                                        }}
                                    />
                                </LineChart>
                            </ChartContainer>
                        </CardContent>
                    </Card>

                    {/* Range or Std Dev Chart (based on subgroup size) */}
                    <Card className="border-muted/40">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-base">
                                {subgroupChartType === "xbar-s" ? "S Chart (Subgroup Std Dev)" : "R Chart (Subgroup Ranges)"}
                            </CardTitle>
                            <CardDescription className="text-xs">
                                <span className="text-muted-foreground block mb-1">
                                    {subgroupChartType === "xbar-s"
                                        ? "Tracks variation within each group — watch for increased inconsistency"
                                        : "Tracks the spread within each group — watch for increased variation"}
                                </span>
                                CL: {controlLimits.rangeCL.toFixed(4)} | UCL: {controlLimits.rangeUCL.toFixed(4)} | LCL: {controlLimits.rangeLCL.toFixed(4)}
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <ChartContainer className="h-[200px] w-full" config={subgroupChartType === "xbar-s" ? stdDevChartConfig : rangeChartConfig}>
                                <LineChart data={spcData} margin={{ left: 8, right: 40, top: 8, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis
                                        dataKey="label"
                                        tickLine={false}
                                        axisLine={false}
                                        tick={{ fontSize: 10 }}
                                        interval="preserveStartEnd"
                                    />
                                    <YAxis
                                        width={60}
                                        tickLine={false}
                                        axisLine={false}
                                        domain={[
                                            Math.max(0, controlLimits.rangeLCL - (controlLimits.rangeUCL - controlLimits.rangeLCL) * 0.1),
                                            controlLimits.rangeUCL * 1.2
                                        ]}
                                        tickFormatter={(v) => v.toFixed(4)}
                                    />
                                    <ChartTooltip
                                        content={<ChartTooltipContent formatter={(value) => (value as number).toFixed(4)} />}
                                    />
                                    <ReferenceLine y={controlLimits.rangeUCL} stroke="var(--destructive)" strokeDasharray="5 5" label={{ value: "UCL", position: "right", fontSize: 10 }} />
                                    <ReferenceLine y={controlLimits.rangeCL} stroke="var(--chart-3)" strokeWidth={2} label={{ value: "CL", position: "right", fontSize: 10 }} />
                                    {controlLimits.rangeLCL > 0 && (
                                        <ReferenceLine y={controlLimits.rangeLCL} stroke="var(--destructive)" strokeDasharray="5 5" label={{ value: "LCL", position: "right", fontSize: 10 }} />
                                    )}
                                    <Line
                                        dataKey={subgroupChartType === "xbar-s" ? "stdDev" : "range"}
                                        stroke="var(--chart-2)"
                                        strokeWidth={2}
                                        dot={(props) => {
                                            const isOOC = outOfControl.some(
                                                (o) => o.subgroup === props.payload.subgroup && o.type === "range"
                                            );
                                            return (
                                                <circle
                                                    cx={props.cx}
                                                    cy={props.cy}
                                                    r={isOOC ? 6 : 4}
                                                    fill={isOOC ? "var(--destructive)" : "var(--chart-2)"}
                                                    stroke={isOOC ? "var(--destructive)" : "var(--chart-2)"}
                                                    style={{ cursor: "pointer" }}
                                                    onClick={() => setSelectedPoint(props.payload)}
                                                />
                                            );
                                        }}
                                        activeDot={{
                                            r: 6,
                                            style: { cursor: "pointer" },
                                            onClick: (_, payload) => {
                                                if (payload && payload.payload) {
                                                    setSelectedPoint(payload.payload as SubgroupPoint);
                                                }
                                            }
                                        }}
                                    />
                                </LineChart>
                            </ChartContainer>
                        </CardContent>
                    </Card>
                        </>
                    ) : null}

                    {chartMode === "i-mr" && imrData.length > 0 && imrControlLimits ? (
                        <>
                    {/* Individual Chart (I-MR) */}
                    <Card className="border-muted/40">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-base">Individual Chart (I)</CardTitle>
                            <CardDescription className="text-xs">
                                <span className="text-muted-foreground block mb-1">Tracks each measurement — watch for sudden shifts or trends in the data</span>
                                CL: {imrControlLimits.individualCL} | UCL: {imrControlLimits.individualUCL} | LCL: {imrControlLimits.individualLCL} | USL: {usl.toFixed(3)} | LSL: {lsl.toFixed(3)}
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <ChartContainer className="h-[250px] w-full" config={individualChartConfig}>
                                <LineChart data={imrData} margin={{ left: 8, right: 40, top: 8, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis
                                        dataKey="label"
                                        tickLine={false}
                                        axisLine={false}
                                        tick={{ fontSize: 10 }}
                                        interval="preserveStartEnd"
                                    />
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
                                    <ChartTooltip
                                        content={<ChartTooltipContent formatter={(value) => (value as number).toFixed(4)} />}
                                    />
                                    {/* Spec Limits */}
                                    <ReferenceLine y={usl} stroke="var(--chart-5)" strokeWidth={2} strokeDasharray="8 4" label={{ value: "USL", position: "right", fontSize: 10, fill: "var(--chart-5)" }} />
                                    <ReferenceLine y={lsl} stroke="var(--chart-5)" strokeWidth={2} strokeDasharray="8 4" label={{ value: "LSL", position: "right", fontSize: 10, fill: "var(--chart-5)" }} />
                                    {/* Zone Lines (±1σ, ±2σ) */}
                                    {(() => {
                                        const sigma = (imrControlLimits.individualUCL - imrControlLimits.individualCL) / 3;
                                        return (
                                            <>
                                                <ReferenceLine y={imrControlLimits.individualCL + 2 * sigma} stroke="hsl(var(--muted-foreground))" strokeWidth={1} strokeDasharray="2 4" strokeOpacity={0.5} />
                                                <ReferenceLine y={imrControlLimits.individualCL + sigma} stroke="hsl(var(--muted-foreground))" strokeWidth={1} strokeDasharray="2 4" strokeOpacity={0.5} />
                                                <ReferenceLine y={imrControlLimits.individualCL - sigma} stroke="hsl(var(--muted-foreground))" strokeWidth={1} strokeDasharray="2 4" strokeOpacity={0.5} />
                                                <ReferenceLine y={imrControlLimits.individualCL - 2 * sigma} stroke="hsl(var(--muted-foreground))" strokeWidth={1} strokeDasharray="2 4" strokeOpacity={0.5} />
                                            </>
                                        );
                                    })()}
                                    {/* Control Limits (±3σ) */}
                                    <ReferenceLine y={imrControlLimits.individualUCL} stroke="var(--destructive)" strokeDasharray="5 5" label={{ value: "UCL", position: "right", fontSize: 10 }} />
                                    <ReferenceLine y={imrControlLimits.individualCL} stroke="var(--chart-3)" strokeWidth={2} label={{ value: "CL", position: "right", fontSize: 10 }} />
                                    <ReferenceLine y={imrControlLimits.individualLCL} stroke="var(--destructive)" strokeDasharray="5 5" label={{ value: "LCL", position: "right", fontSize: 10 }} />
                                    <Line
                                        dataKey="value"
                                        stroke="var(--chart-1)"
                                        strokeWidth={2}
                                        dot={(props) => {
                                            const isOOC = imrOutOfControl.some(
                                                (o) => o.subgroup === props.payload.index && o.type === "individual"
                                            );
                                            return (
                                                <circle
                                                    cx={props.cx}
                                                    cy={props.cy}
                                                    r={isOOC ? 6 : 4}
                                                    fill={isOOC ? "var(--destructive)" : "var(--chart-1)"}
                                                    stroke={isOOC ? "var(--destructive)" : "var(--chart-1)"}
                                                    style={{ cursor: "pointer" }}
                                                    onClick={() => setSelectedIMRPoint(props.payload)}
                                                />
                                            );
                                        }}
                                        activeDot={{
                                            r: 6,
                                            style: { cursor: "pointer" },
                                            onClick: (_, payload) => {
                                                if (payload && payload.payload) {
                                                    setSelectedIMRPoint(payload.payload as IndividualPoint);
                                                }
                                            }
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
                                <span className="text-muted-foreground block mb-1">Tracks point-to-point changes — large jumps indicate something changed</span>
                                CL: {imrControlLimits.mrCL} | UCL: {imrControlLimits.mrUCL}
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <ChartContainer className="h-[200px] w-full" config={mrChartConfig}>
                                <LineChart data={imrData.slice(1)} margin={{ left: 8, right: 40, top: 8, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis
                                        dataKey="label"
                                        tickLine={false}
                                        axisLine={false}
                                        tick={{ fontSize: 10 }}
                                        interval="preserveStartEnd"
                                    />
                                    <YAxis
                                        width={60}
                                        tickLine={false}
                                        axisLine={false}
                                        domain={[0, imrControlLimits.mrUCL * 1.2]}
                                        tickFormatter={(v) => v.toFixed(3)}
                                    />
                                    <ChartTooltip
                                        content={<ChartTooltipContent formatter={(value) => (value as number).toFixed(4)} />}
                                    />
                                    <ReferenceLine y={imrControlLimits.mrUCL} stroke="var(--destructive)" strokeDasharray="5 5" label={{ value: "UCL", position: "right", fontSize: 10 }} />
                                    <ReferenceLine y={imrControlLimits.mrCL} stroke="var(--chart-3)" strokeWidth={2} label={{ value: "CL", position: "right", fontSize: 10 }} />
                                    <Line
                                        dataKey="movingRange"
                                        stroke="var(--chart-2)"
                                        strokeWidth={2}
                                        dot={(props) => {
                                            const isOOC = imrOutOfControl.some(
                                                (o) => o.subgroup === props.payload.index && o.type === "mr"
                                            );
                                            return (
                                                <circle
                                                    cx={props.cx}
                                                    cy={props.cy}
                                                    r={isOOC ? 6 : 4}
                                                    fill={isOOC ? "var(--destructive)" : "var(--chart-2)"}
                                                    stroke={isOOC ? "var(--destructive)" : "var(--chart-2)"}
                                                    style={{ cursor: "pointer" }}
                                                    onClick={() => setSelectedIMRPoint(props.payload)}
                                                />
                                            );
                                        }}
                                        activeDot={{
                                            r: 6,
                                            style: { cursor: "pointer" },
                                            onClick: (_, payload) => {
                                                if (payload && payload.payload) {
                                                    setSelectedIMRPoint(payload.payload as IndividualPoint);
                                                }
                                            }
                                        }}
                                    />
                                </LineChart>
                            </ChartContainer>
                        </CardContent>
                    </Card>
                        </>
                    ) : null}
                </TabsContent>

                <TabsContent value="histogram">
                    <Card className="border-muted/40">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-base">Process Distribution</CardTitle>
                            <CardDescription className="text-xs">
                                Histogram of all measurements with specification limits
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <ChartContainer className="h-[300px] w-full" config={{ count: { label: "Count", color: "var(--chart-1)" } }}>
                                <ComposedChart data={histogramData.bins} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis
                                        dataKey="bin"
                                        tickLine={false}
                                        axisLine={false}
                                        tick={{ fontSize: 10 }}
                                        angle={-45}
                                        textAnchor="end"
                                        height={60}
                                    />
                                    <YAxis width={40} tickLine={false} axisLine={false} />
                                    <ChartTooltip content={<ChartTooltipContent />} />
                                    <ReferenceLine x={histogramData.lsl.toFixed(3)} stroke="var(--destructive)" strokeWidth={2} label={{ value: "LSL", position: "top", fontSize: 10 }} />
                                    <ReferenceLine x={histogramData.usl.toFixed(3)} stroke="var(--destructive)" strokeWidth={2} label={{ value: "USL", position: "top", fontSize: 10 }} />
                                    <Bar dataKey="count" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
                                </ComposedChart>
                            </ChartContainer>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="data">
                    <Card className="border-muted/40">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-base">Subgroup Data</CardTitle>
                            <CardDescription className="text-xs">
                                Raw measurement data by subgroup
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <div className="overflow-x-auto max-h-[400px]">
                                <table className="w-full text-sm">
                                    <thead className="sticky top-0 bg-background border-b">
                                        <tr>
                                            <th className="text-left p-2 font-medium">Subgroup</th>
                                            <th className="text-left p-2 font-medium">Date</th>
                                            <th className="text-right p-2 font-medium">X-bar</th>
                                            <th className="text-right p-2 font-medium">Range</th>
                                            <th className="text-left p-2 font-medium">Values</th>
                                            <th className="text-left p-2 font-medium">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {spcData.map((point) => {
                                            const ooc = outOfControl.filter((o) => o.subgroup === point.subgroup);
                                            return (
                                                <tr key={point.subgroup} className={ooc.length > 0 ? "bg-destructive/5" : ""}>
                                                    <td className="p-2">{point.subgroup}</td>
                                                    <td className="p-2 text-muted-foreground">{point.label}</td>
                                                    <td className="p-2 text-right font-mono">{point.xBar.toFixed(4)}</td>
                                                    <td className="p-2 text-right font-mono">{point.range.toFixed(4)}</td>
                                                    <td className="p-2 font-mono text-xs">
                                                        {point.values.map((v) => v.toFixed(3)).join(", ")}
                                                    </td>
                                                    <td className="p-2">
                                                        {ooc.length > 0 ? (
                                                            <Badge variant="destructive" className="text-xs">
                                                                {ooc.map((o) => o.rule).join(", ")}
                                                            </Badge>
                                                        ) : (
                                                            <Badge variant="outline" className="text-xs">OK</Badge>
                                                        )}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* Out of Control Summary */}
            {outOfControl.length > 0 && (
                <Card className="border-destructive/50 bg-destructive/5">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-base flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-destructive" />
                            Out of Control Points Detected
                        </CardTitle>
                        <CardDescription className="text-xs">
                            {outOfControl.length} point(s) require investigation
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-0">
                        <div className="space-y-2">
                            {outOfControl.map((ooc, i) => (
                                <div key={i} className="flex items-center gap-3 text-sm">
                                    <Badge variant="destructive">{ooc.type === "xBar" ? "X-bar" : "Range"}</Badge>
                                    <span>Subgroup {ooc.subgroup}</span>
                                    <span className="text-muted-foreground">•</span>
                                    <span className="text-muted-foreground">{ooc.rule}</span>
                                    <span className="text-muted-foreground">•</span>
                                    <span className="font-mono">{ooc.value.toFixed(4)}</span>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Process Capability Summary */}
            <Card className="border-muted/40">
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">Process Capability Summary</CardTitle>
                    <CardDescription className="text-xs">
                        Statistical capability indices for {measurementDef.name}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
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
                    <div className="mt-4 pt-4 border-t text-xs text-muted-foreground">
                        <p><strong>Interpretation:</strong> Cpk ≥ 1.33 indicates a capable process. Cpk between 1.0-1.33 is marginally capable. Cpk &lt; 1.0 indicates the process needs improvement.</p>
                    </div>
                </CardContent>
            </Card>

            {/* Point Detail Modal */}
            <Dialog open={selectedPoint !== null} onOpenChange={(open) => !open && setSelectedPoint(null)}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            Subgroup {selectedPoint?.subgroup} Details
                            {selectedPointViolations.length > 0 && (
                                <Badge variant="destructive" className="ml-2">Out of Control</Badge>
                            )}
                        </DialogTitle>
                        <DialogDescription>
                            {selectedPoint?.timestamp.toLocaleDateString(undefined, {
                                weekday: "long",
                                year: "numeric",
                                month: "long",
                                day: "numeric"
                            })}
                        </DialogDescription>
                    </DialogHeader>

                    {selectedPoint && (
                        <div className="space-y-4">
                            {/* Summary Stats */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-muted/50 rounded-lg p-3">
                                    <div className="text-xs text-muted-foreground">X-bar (Mean)</div>
                                    <div className="text-lg font-mono font-semibold">
                                        {selectedPoint.xBar.toFixed(4)} {measurementDef.unit}
                                    </div>
                                </div>
                                <div className="bg-muted/50 rounded-lg p-3">
                                    <div className="text-xs text-muted-foreground">Range</div>
                                    <div className="text-lg font-mono font-semibold">
                                        {selectedPoint.range.toFixed(4)} {measurementDef.unit}
                                    </div>
                                </div>
                            </div>

                            {/* Individual Values */}
                            <div>
                                <div className="text-sm font-medium mb-2">Individual Measurements</div>
                                <div className="bg-muted/30 rounded-lg p-3">
                                    <div className="grid grid-cols-5 gap-2">
                                        {selectedPoint.values.map((value, idx) => {
                                            const isOutOfSpec = value > usl || value < lsl;
                                            return (
                                                <div
                                                    key={idx}
                                                    className={`text-center p-2 rounded ${isOutOfSpec ? "bg-destructive/20 text-destructive" : "bg-background"}`}
                                                >
                                                    <div className="text-xs text-muted-foreground">#{idx + 1}</div>
                                                    <div className="font-mono text-sm">{value.toFixed(3)}</div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                    <div className="mt-2 pt-2 border-t flex justify-between text-xs text-muted-foreground">
                                        <span>Min: {Math.min(...selectedPoint.values).toFixed(3)}</span>
                                        <span>Max: {Math.max(...selectedPoint.values).toFixed(3)}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Violations */}
                            {selectedPointViolations.length > 0 && (
                                <div>
                                    <div className="text-sm font-medium mb-2 text-destructive">Rule Violations</div>
                                    <div className="space-y-2">
                                        {selectedPointViolations.map((violation, idx) => (
                                            <div key={idx} className="flex items-center gap-2 text-sm bg-destructive/10 rounded-lg p-2">
                                                <AlertTriangle className="h-4 w-4 text-destructive" />
                                                <span className="font-medium">{violation.type === "xBar" ? "X-bar" : "Range"}:</span>
                                                <span className="text-muted-foreground">{violation.rule}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Spec Comparison */}
                            <div>
                                <div className="text-sm font-medium mb-2">Specification Status</div>
                                <div className="grid grid-cols-3 gap-2 text-xs">
                                    <div className="text-center p-2 bg-muted/30 rounded">
                                        <div className="text-muted-foreground">LSL</div>
                                        <div className="font-mono">{lsl.toFixed(3)}</div>
                                    </div>
                                    <div className="text-center p-2 bg-muted/30 rounded">
                                        <div className="text-muted-foreground">Nominal</div>
                                        <div className="font-mono">{measurementDef.nominal.toFixed(3)}</div>
                                    </div>
                                    <div className="text-center p-2 bg-muted/30 rounded">
                                        <div className="text-muted-foreground">USL</div>
                                        <div className="font-mono">{usl.toFixed(3)}</div>
                                    </div>
                                </div>
                                <div className="mt-2 text-xs text-muted-foreground text-center">
                                    Mean deviation from nominal: {((selectedPoint.xBar - measurementDef.nominal) >= 0 ? "+" : "")}{(selectedPoint.xBar - measurementDef.nominal).toFixed(4)} {measurementDef.unit}
                                </div>
                            </div>

                            {/* Action Buttons */}
                            <div className="pt-4 border-t flex justify-end gap-2">
                                <Button variant="outline" onClick={() => setSelectedPoint(null)}>
                                    Close
                                </Button>
                                <Button onClick={handleInvestigate} className="gap-2">
                                    <FileWarning className="h-4 w-4" />
                                    Investigate (Create CAPA)
                                </Button>
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            {/* I-MR Point Detail Modal */}
            <Dialog open={selectedIMRPoint !== null} onOpenChange={(open) => !open && setSelectedIMRPoint(null)}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            Point {selectedIMRPoint?.index} Details
                            {selectedIMRPointViolations.length > 0 && (
                                <Badge variant="destructive" className="ml-2">Out of Control</Badge>
                            )}
                        </DialogTitle>
                        <DialogDescription>
                            {selectedIMRPoint?.timestamp.toLocaleDateString(undefined, {
                                weekday: "long",
                                year: "numeric",
                                month: "long",
                                day: "numeric"
                            })}
                        </DialogDescription>
                    </DialogHeader>

                    {selectedIMRPoint && (
                        <div className="space-y-4">
                            {/* Summary Stats */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-muted/50 rounded-lg p-3">
                                    <div className="text-xs text-muted-foreground">Individual Value</div>
                                    <div className="text-lg font-mono font-semibold">
                                        {selectedIMRPoint.value.toFixed(4)} {measurementDef.unit}
                                    </div>
                                </div>
                                <div className="bg-muted/50 rounded-lg p-3">
                                    <div className="text-xs text-muted-foreground">Moving Range</div>
                                    <div className="text-lg font-mono font-semibold">
                                        {selectedIMRPoint.movingRange.toFixed(4)} {measurementDef.unit}
                                    </div>
                                </div>
                            </div>

                            {/* Value Status */}
                            <div className="bg-muted/30 rounded-lg p-3">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-muted-foreground">Value Status:</span>
                                    {selectedIMRPoint.value > usl || selectedIMRPoint.value < lsl ? (
                                        <Badge variant="destructive">Out of Spec</Badge>
                                    ) : (
                                        <Badge variant="outline" className="text-green-600 border-green-600">Within Spec</Badge>
                                    )}
                                </div>
                                <div className="mt-2 text-xs text-muted-foreground text-center">
                                    Deviation from nominal: {((selectedIMRPoint.value - measurementDef.nominal) >= 0 ? "+" : "")}{(selectedIMRPoint.value - measurementDef.nominal).toFixed(4)} {measurementDef.unit}
                                </div>
                            </div>

                            {/* Violations */}
                            {selectedIMRPointViolations.length > 0 && (
                                <div>
                                    <div className="text-sm font-medium mb-2 text-destructive">Rule Violations</div>
                                    <div className="space-y-2">
                                        {selectedIMRPointViolations.map((violation, idx) => (
                                            <div key={idx} className="flex items-center gap-2 text-sm bg-destructive/10 rounded-lg p-2">
                                                <AlertTriangle className="h-4 w-4 text-destructive" />
                                                <span className="font-medium">{violation.type === "individual" ? "Individual" : "MR"}:</span>
                                                <span className="text-muted-foreground">{violation.rule}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Spec Comparison */}
                            <div>
                                <div className="text-sm font-medium mb-2">Specification Status</div>
                                <div className="grid grid-cols-3 gap-2 text-xs">
                                    <div className="text-center p-2 bg-muted/30 rounded">
                                        <div className="text-muted-foreground">LSL</div>
                                        <div className="font-mono">{lsl.toFixed(3)}</div>
                                    </div>
                                    <div className="text-center p-2 bg-muted/30 rounded">
                                        <div className="text-muted-foreground">Nominal</div>
                                        <div className="font-mono">{measurementDef.nominal.toFixed(3)}</div>
                                    </div>
                                    <div className="text-center p-2 bg-muted/30 rounded">
                                        <div className="text-muted-foreground">USL</div>
                                        <div className="font-mono">{usl.toFixed(3)}</div>
                                    </div>
                                </div>
                            </div>

                            {/* Action Buttons */}
                            <div className="pt-4 border-t flex justify-end gap-2">
                                <Button variant="outline" onClick={() => setSelectedIMRPoint(null)}>
                                    Close
                                </Button>
                                <Button onClick={handleIMRInvestigate} className="gap-2">
                                    <FileWarning className="h-4 w-4" />
                                    Investigate (Create CAPA)
                                </Button>
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
