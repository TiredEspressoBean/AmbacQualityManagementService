import { useAuthUser } from "@/hooks/useAuthUser";
import Login from "@/components/auth/Login";
import { resolveHomeBlocks } from "@/components/home/home-blocks";
import { PersonaSwitcher } from "@/components/home/PersonaSwitcher";
import { useHomePersona } from "@/hooks/useHomePersona";
import { QaHomePage } from "@/pages/quality/QaHomePage";
import { OperatorHomePage } from "@/pages/operator/OperatorHomePage";

export default function Home() {
    const { data: user, isLoading } = useAuthUser();

    if (isLoading) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center">
                <div className="text-muted-foreground">Loading...</div>
            </div>
        );
    }

    // Logged-out: show login
    if (!user) {
        return <Login />;
    }

    return <HomeForUser user={user} />;
}

function HomeForUser({ user }: { user: NonNullable<ReturnType<typeof useAuthUser>["data"]> }) {
    const { persona } = useHomePersona(user);

    // QA Inspector lands on the inspection task inbox — a full surface, not a
    // block stack (design doc §6: the inspector landing is a task inbox). The
    // QA Manager is an OVERSIGHT role, not a doer — it gets the block stack
    // (triage + KPIs), NOT the inspector's queue.
    if (persona === "QA Inspector") {
        return <QaHomePage user={user} />;
    }

    // Operators land on the kiosk-tile operator home (design doc §6): a full
    // task surface, not the generic block stack. Currently a preview shell —
    // Scan + In progress are live, the rest is dimmed until its backend lands.
    if (persona === "Operator") {
        return <OperatorHomePage user={user} />;
    }

    const blocks = resolveHomeBlocks(user, persona);

    // No role-matched blocks (auditor, engineering, customer, …): keep the
    // simple welcome — those roles navigate by sidebar, not a task queue.
    if (blocks.length === 0) {
        return (
            <div className="flex min-h-[60vh] flex-col items-center justify-center px-4">
                <div className="text-center space-y-4">
                    <h1 className="text-3xl font-semibold">
                        Welcome back{user.first_name ? `, ${user.first_name}` : ""}
                    </h1>
                    <p className="text-muted-foreground">
                        Use the sidebar to navigate to your workflow.
                    </p>
                </div>
            </div>
        );
    }

    // Role-based landing: a composable 2-col grid on md+. Each BlockDef
    // declares `size: "full" | "half"` — full blocks span both columns, halves
    // pair up in a row. Order is preserved (each block owns its slot in the
    // persona.order sequence); halves that come after a full simply start a
    // new row. On narrow viewports the grid collapses to a single column and
    // all blocks render full-width.
    return (
        <div className="mx-auto max-w-5xl space-y-4 p-4">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-semibold tracking-tight">
                        Welcome back{user.first_name ? `, ${user.first_name}` : ""}
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        {persona ? <span className="font-medium text-foreground">{persona}</span> : null}
                        {persona ? " · " : ""}Here's what needs you right now.
                    </p>
                </div>
                <PersonaSwitcher user={user} />
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {blocks.map((b) => (
                    // `empty:hidden` collapses the wrapper when the block
                    // returns null (self-hiding at zero). Without it, the
                    // wrapper still occupies a grid cell and pushes the next
                    // half into a lone row.
                    <div
                        key={b.id}
                        className={`empty:hidden ${b.size === "half" ? "" : "md:col-span-2"}`}
                    >
                        <b.Component user={user} />
                    </div>
                ))}
            </div>
        </div>
    );
}
