import {
    Tabs,
    TabsList,
    TabsTrigger,
} from "@/components/ui/tabs";
import { useState } from "react";
import {QaPartsInProcessPage} from "@/pages/editors/QaPartsInProcessPage.tsx"
import {QaWorkOrdersPage} from "@/pages/editors/QaWorkOrdersPage.tsx"
import {QaQuarantinePage} from "@/pages/editors/QaQuarantinePage.tsx";
import {AuditLogViewerPage} from "@/pages/editors/HistoryPage.tsx";

export default function QaPartsPage() {
    const [activeTab, setActiveTab] = useState("workorders");

    return (
        <div className="space-y-4">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                    <TabsTrigger value="workorders">Work Orders</TabsTrigger>
                    {/*<TabsTrigger value="parts">Parts</TabsTrigger>*/}
                    <TabsTrigger value="quarantine">Quarantined</TabsTrigger>
                    <TabsTrigger value="history">History</TabsTrigger>
                </TabsList>
            </Tabs>

            {/* All tab contents are mounted and hidden via Tailwind */}
            <div className={activeTab === "workorders" ? "" : "hidden"}>
                <QaWorkOrdersPage />
            </div>
            
            <div className={activeTab === "parts" ? "" : "hidden"}>
                <QaPartsInProcessPage />
            </div>

            <div className={activeTab === "quarantine" ? "" : "hidden"}>
                <QaQuarantinePage />
            </div>

            <div className={activeTab === "history" ? "" : "hidden"}>
                <AuditLogViewerPage/>
            </div>
        </div>
    );
}
