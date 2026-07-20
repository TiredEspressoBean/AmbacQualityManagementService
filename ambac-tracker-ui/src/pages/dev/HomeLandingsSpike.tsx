/**
 * Dev preview: role-based home landings (/dev/home-landings).
 *
 * Renders each employee role's REAL, ordered block stack — exactly what Home
 * would show that persona — without needing a login for that role. Uses the
 * current user's identity (so personal blocks like "my quality actions" still
 * resolve) but swaps the group used for block gating/ordering.
 *
 * This is the surface to judge how a role's landing actually looks: per role
 * the stack is tight (3–5 blocks), not the "sees-everything" admin dump.
 *
 * Not shown here: QA Inspector and Operator get bespoke full-page surfaces
 * (they're intercepted in Home) — preview those at /dev/qa-home and
 * /dev/operator-home.
 */
import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuthUser, type AuthUser } from "@/hooks/useAuthUser";
import { resolveHomeBlocks } from "@/components/home/home-blocks";

// The block-stack employee roles (QA Inspector + Operator are bespoke pages).
const ROLES = [
    "QA Manager",
    "Production Manager",
    "Shift Lead",
    "Document Controller",
    "Engineering",
    "Tenant Admin",
] as const;

export function HomeLandingsSpike() {
    const { data: realUser } = useAuthUser();
    const [role, setRole] = useState<(typeof ROLES)[number]>("QA Manager");

    if (!realUser) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center text-muted-foreground">
                Log in to preview role landings.
            </div>
        );
    }

    // Preview identity: real user (keeps pk for personal blocks) with the group
    // swapped to the selected role and is_staff cleared, so only the group drives
    // block gating/ordering (matches how Home resolves a real member of that role).
    const previewUser = {
        ...realUser,
        is_staff: false,
        groups: [{ name: role }],
    } as unknown as AuthUser;

    const blocks = resolveHomeBlocks(previewUser);

    return (
        <div className="mx-auto max-w-5xl p-4">
            {/* Dev toolbar */}
            <div className="sticky top-0 z-10 -mx-4 mb-4 border-b bg-background/95 px-4 py-3 backdrop-blur">
                <div className="flex items-center gap-2">
                    <Badge variant="outline" className="shrink-0">DEV</Badge>
                    <span className="text-sm font-medium">Role landing preview</span>
                    <Link to="/dev/qa-home" className="ml-auto">
                        <Button variant="ghost" size="sm">QA inbox <ArrowRight className="ml-1 h-3.5 w-3.5" /></Button>
                    </Link>
                    <Link to="/dev/operator-home">
                        <Button variant="ghost" size="sm">Operator <ArrowRight className="ml-1 h-3.5 w-3.5" /></Button>
                    </Link>
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                    {ROLES.map((r) => (
                        <button
                            key={r}
                            onClick={() => setRole(r)}
                            className={`rounded-full border px-3 py-1 text-sm transition-colors ${
                                r === role ? "border-primary bg-primary/10 font-medium" : "hover:bg-accent"
                            }`}
                        >
                            {r}
                        </button>
                    ))}
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                    Showing <b className="text-foreground">{role}</b> — {blocks.length} block
                    {blocks.length === 1 ? "" : "s"}: {blocks.map((b) => b.id).join(" · ")}. Live tenant data,
                    your identity for personal blocks.
                </p>
            </div>

            {/* The stack, rendered exactly as Home would for this persona. */}
            <div className="mx-auto max-w-3xl space-y-4">
                <div>
                    <h1 className="text-2xl font-semibold tracking-tight">
                        Welcome back{realUser.first_name ? `, ${realUser.first_name}` : ""}
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        <span className="font-medium text-foreground">{role}</span> · Here's what needs you right now.
                    </p>
                </div>
                {blocks.map((b) => (
                    <b.Component key={b.id} user={previewUser} />
                ))}
            </div>
        </div>
    );
}

export default HomeLandingsSpike;
