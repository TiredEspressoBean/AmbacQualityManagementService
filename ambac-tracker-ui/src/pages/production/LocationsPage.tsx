import { useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LocationTree } from "@/components/locations/LocationTree";
import { resolveScan } from "@/lib/scan";

/**
 * Where things are. The tenant's locations as a tree, with what's in each (rolled up:
 * a rack counts its bins). Scan a location's label, or type its name or code, to open
 * it; print labels for the ones that don't have one yet. Setting locations up in bulk
 * (kinds, codes, held-only cages) is in Data Management.
 */
export function LocationsPage() {
    const navigate = useNavigate();
    const [code, setCode] = useState("");

    const open = async () => {
        const q = code.trim();
        if (!q) return;
        const hit = await resolveScan(q).catch(() => null);
        setCode("");
        if (hit?.kind === "LOCATION") { void navigate({ to: "/production/locations/$locationId", params: { locationId: hit.id } }); return; }
        if (hit?.path) { void navigate({ to: hit.path as never }); return; }
        toast.error(`Nothing called “${q}”.`);
    };

    return (
        <div className="mx-auto max-w-6xl space-y-4 p-6">
            <div className="flex flex-wrap items-end justify-between gap-2">
                <div>
                    <h1 className="text-2xl font-semibold tracking-tight">Locations</h1>
                    <p className="text-sm text-muted-foreground">
                        Where lots, units and machines are. Moves are recorded — open a location to see what came and went.
                    </p>
                </div>
                <div className="flex gap-3 text-sm">
                    <Link to="/production/cycle-counts" className="hover:underline">Cycle counts</Link>
                    <Link to="/editor/storage-locations" className="hover:underline">Set up locations</Link>
                </div>
            </div>

            <div className="flex items-center gap-2 rounded-lg border bg-card p-3">
                <MapPin className="h-5 w-5 shrink-0 text-muted-foreground" />
                <Input value={code} onChange={(e) => setCode(e.target.value)} autoFocus
                    onKeyDown={(e) => { if (e.key === "Enter") void open(); }}
                    placeholder="Scan a location label, or type its name or code…"
                    className="border-0 text-base shadow-none focus-visible:ring-0" />
                <Button onClick={() => void open()} disabled={!code.trim()}>Open</Button>
            </div>

            <LocationTree />
        </div>
    );
}
