import { Link } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { ShiftsSettingsTab } from "@/components/scheduling/ShiftsSettingsTab";

/** Shifts as a Data Management table: the same editor the schedule's settings dialog
 *  opens as its "Work hours" tab. */
export function ShiftsEditorPage() {
    return (
        <div className="mx-auto max-w-4xl space-y-6 p-6">
            <div>
                <Link to="/Edit" className="mb-4 inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
                    <ArrowLeft className="mr-1 h-4 w-4" />
                    Data Management
                </Link>
                <h1 className="text-2xl font-bold">Shifts</h1>
                <p className="text-sm text-muted-foreground">
                    The plant's working hours and standing breaks. The scheduler plans work only
                    inside them.
                </p>
            </div>
            <ShiftsSettingsTab manage />
        </div>
    );
}
