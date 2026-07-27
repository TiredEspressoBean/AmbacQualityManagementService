import type { AuthUser } from "@/hooks/useAuthUser";
import { useHomePersona } from "@/hooks/useHomePersona";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

/**
 * Landing persona switcher. Renders nothing when the user has only one
 * candidate persona (the common case). Placed in the header of the block-stack
 * Home, QaHomePage, and OperatorHomePage so a user in multiple persona groups
 * can move between landings without a dev route.
 *
 * The choice persists in localStorage keyed by user pk (see useHomePersona) and
 * drives both the block stack AND the bespoke-page intercepts in Home.tsx.
 */
export function PersonaSwitcher({ user, className }: { user: AuthUser; className?: string }) {
    const { persona, candidates, choose, canSwitch } = useHomePersona(user);
    if (!canSwitch || !persona) return null;
    return (
        <Select value={persona} onValueChange={choose}>
            <SelectTrigger
                className={className ?? "h-8 w-[180px] text-xs"}
                aria-label="Switch landing"
            >
                <SelectValue />
            </SelectTrigger>
            <SelectContent>
                {candidates.map((p) => (
                    <SelectItem key={p} value={p} className="text-sm">{p}</SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}
