/**
 * Row actions for a step in the Steps list. A step row is shared by a process, its
 * later versions and its duplicates, so it is edited in a process — the editor
 * versions it for that process and leaves the others as they were. A step used by
 * several processes offers each; one used by none opens the step form directly.
 */
import { Link } from "@tanstack/react-router";
import { Eye, Pencil, Workflow } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { components } from "@/lib/api/generated-types";

type ProcessRef = components["schemas"]["StepProcessRef"];

const label = (p: ProcessRef) =>
    `${p.name} · v${p.version}${p.is_current_version ? "" : " (superseded)"}`;

export function StepInProcessActions({ stepId, processes }: { stepId: string; processes: ProcessRef[] }) {
    return (
        <div className="flex items-center gap-1">
            {processes.length === 0 ? (
                <Button asChild variant="ghost" size="icon" title="Edit step">
                    <Link to="/StepForm/edit/$id" params={{ id: stepId }}><Pencil className="h-4 w-4" /></Link>
                </Button>
            ) : processes.length === 1 ? (
                <Button asChild variant="ghost" size="icon" title={`Edit in ${label(processes[0])}`}>
                    <Link to="/process-flow" search={{ id: processes[0].id, step: stepId }}>
                        <Workflow className="h-4 w-4" />
                    </Link>
                </Button>
            ) : (
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" title="Edit in a process">
                            <Workflow className="h-4 w-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuLabel>Edit in</DropdownMenuLabel>
                        {processes.map((p) => (
                            <DropdownMenuItem key={p.id} asChild>
                                <Link to="/process-flow" search={{ id: p.id, step: stepId }}>{label(p)}</Link>
                            </DropdownMenuItem>
                        ))}
                    </DropdownMenuContent>
                </DropdownMenu>
            )}
            {processes.length > 0 && (
                <Button asChild variant="ghost" size="icon" title="Step details, timing and machines">
                    <Link to="/StepForm/edit/$id" params={{ id: stepId }}><Eye className="h-4 w-4" /></Link>
                </Button>
            )}
        </div>
    );
}
