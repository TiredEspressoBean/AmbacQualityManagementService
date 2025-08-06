// src/pages/EditLandingPage.tsx
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Link } from "@tanstack/react-router";

const editors = [
    {
        name: "Orders",
        description: "Edit customer orders, their status, and linked parts.",
        path: "/editor/orders",
    },
    {
        name: "Parts",
        description: "Manage parts and production tracking.",
        path: "/editor/parts",
    },
    {
        name: "Parts Types",
        description: "Manage part types, and their information.",
        path: "/editor/partTypes",
    },
    {
        name: "Processes",
        description: "Configure manufacturing workflows.",
        path: "/editor/processes",
    },
    {
        name: "Steps",
        description: "Configure manufacturing workflow steps.",
        path: "/editor/steps",
    },
    {
        name: "Equipment",
        description: "Manage equipment.",
        path: "/editor/equipment",
    },
    {
        name: "Equipment Types",
        description: "Configure manufacturing workflow steps.",
        path: "/editor/equipmentTypes",
    },
    {
        name: "Error Types",
        description: "Manage equipment.",
        path: "/editor/errorTypes",
    },
    {
        name: "Sampling Rules",
        description: "Manage individual rules by which parts are sampled for quality inspections.",
        path: "/editor/samplingRules",
    },
    {
        name: "Sampling Rule Sets",
        description: "Manage the sets of rules as applied to different process steps.",
        path: "/editor/samplingRuleSets",
    },
    {
        name: "Work Orders",
        description: "Manage work orders and their status",
        path: "/editor/workOrders",
    },
    {
        name: "Companies",
        description: "Manage companies",
        path: "/editor/companies",
    },
    {
        name: "Users",
        description: "Manage users",
        path: "/editor/users",
    }
];

export default function EditLandingPage() {
    return (
        <div className="p-6">
            <h1 className="text-3xl font-bold mb-2">Manage System Data</h1>
            <p className="text-muted-foreground mb-6">
                Select a category below to view, edit, or update records.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {editors.map(({ name, description, path }) => (
                    <Card key={name} className="flex flex-col justify-between h-full">
                        <CardContent className="p-4 flex flex-col gap-4 h-full">
                            <div>
                                <h3 className="text-xl font-semibold">{name}</h3>
                                <p className="text-sm text-muted-foreground mt-1 line-clamp-3">
                                    {description}
                                </p>
                            </div>
                            <Link to={path}>
                                <Button className="mt-auto w-full">Manage {name}</Button>
                            </Link>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
}
