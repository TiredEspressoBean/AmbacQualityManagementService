import {
    Tabs,
    TabsList,
    TabsTrigger,
} from "@/components/ui/tabs";
import { useState } from "react";
import {QaPartsInProcessPage} from "@/pages/editors/QaPartsInProcessPage.tsx"
import {QaQuarantinePage} from "@/pages/editors/QaQuarantinePage.tsx";
import {AuditLogViewerPage} from "@/pages/editors/HistoryPage.tsx";

export default function QaPartsPage() {
    const [activeTab, setActiveTab] = useState("parts");

    return (
        <div className="space-y-4">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                    <TabsTrigger value="parts">Parts</TabsTrigger>
                    <TabsTrigger value="workorders">Quarantined</TabsTrigger>
                    <TabsTrigger value="history">History</TabsTrigger>
                </TabsList>
            </Tabs>

            {/* All tab contents are mounted and hidden via Tailwind */}
            <div className={activeTab === "parts" ? "" : "hidden"}>
                <QaPartsInProcessPage />
            </div>

            <div className={activeTab === "workorders" ? "" : "hidden"}>
                <QaQuarantinePage />
            </div>

            <div className={activeTab === "history" ? "" : "hidden"}>
                <AuditLogViewerPage/>
            </div>
        </div>
    );
}
