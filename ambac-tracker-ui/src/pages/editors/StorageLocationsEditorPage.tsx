import { Link } from "@tanstack/react-router";
import { LocationTree } from "@/components/locations/LocationTree";

/**
 * Setting up locations: the tree, with each one's kind, label code and controls
 * (held stock only, receiving dock, in use). Lots, units and machines point at a
 * location, so renaming one renames it everywhere and one in use can't be removed —
 * make it inactive instead.
 */
export function StorageLocationsEditorPage() {
    return (
        <div className="mx-auto max-w-6xl space-y-4 p-6">
            <div>
                <h1 className="text-2xl font-semibold tracking-tight">Storage locations</h1>
                <p className="text-sm text-muted-foreground">
                    The places things are kept, nested the way the building is: a warehouse, its areas and racks,
                    their bins. Receiving, moves and machine records pick from these.
                    {" "}<Link to="/production/locations" className="hover:underline">See what's in each →</Link>
                </p>
            </div>
            <LocationTree manage />
        </div>
    );
}
