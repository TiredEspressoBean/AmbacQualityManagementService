import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { useCreateProcessWithSteps } from "@/hooks/useCreateProcessWithSteps";

/**
 * Two-field wizard that collects the minimum a Process needs at
 * creation time — Name + Part Type — then drops the user straight
 * into the React Flow editor for the freshly-created process.
 *
 * The remaining metadata (remanufacturing flag, batch flag,
 * description, etc.) is edited inline in the React Flow side panel.
 * Steps and edges are added on the canvas. Keeping the wizard
 * minimal avoids a second form-style screen between the user and
 * the canvas.
 */
type Props = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
};

export function NewProcessWizard({ open, onOpenChange }: Props) {
    const navigate = useNavigate();
    const [name, setName] = useState("");
    const [partTypeId, setPartTypeId] = useState<string>("");
    const [isRemanufactured, setIsRemanufactured] = useState(false);

    const { data: partTypesResp } = useRetrievePartTypes();
    const partTypes = (partTypesResp?.results ?? []) as Array<{
        id: string;
        name: string;
    }>;

    const createProcess = useCreateProcessWithSteps();

    const resetAndClose = () => {
        setName("");
        setPartTypeId("");
        setIsRemanufactured(false);
        onOpenChange(false);
    };

    const canSubmit = name.trim().length > 0 && partTypeId !== "";

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!canSubmit || createProcess.isPending) return;
        try {
            const created = await createProcess.mutateAsync({
                name: name.trim(),
                part_type: partTypeId,
                is_remanufactured: isRemanufactured,
                nodes: [],
                edges: [],
            } as Parameters<typeof createProcess.mutateAsync>[0]);
            const newId = (created as { id?: string })?.id;
            if (!newId) {
                toast.error("Process created but no id returned.");
                return;
            }
            toast.success(`Created ${name.trim()}`);
            resetAndClose();
            navigate({ to: "/process-flow", search: { id: newId } });
        } catch (err) {
            console.error("Create process failed", err);
            toast.error("Failed to create process.");
        }
    };

    return (
        <Dialog open={open} onOpenChange={(o) => (o ? onOpenChange(o) : resetAndClose())}>
            <DialogContent className="sm:max-w-md">
                <form onSubmit={handleSubmit}>
                    <DialogHeader>
                        <DialogTitle>New Process</DialogTitle>
                        <DialogDescription>
                            Start with a name and a part type. Add steps and edges
                            on the flow canvas after creating.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="process-name">
                                Name <span className="text-destructive">*</span>
                            </Label>
                            <Input
                                id="process-name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g. Injector Reman"
                                autoFocus
                                maxLength={50}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="process-part-type">
                                Part Type <span className="text-destructive">*</span>
                            </Label>
                            <Select value={partTypeId} onValueChange={setPartTypeId}>
                                <SelectTrigger id="process-part-type">
                                    <SelectValue placeholder="Select a part type" />
                                </SelectTrigger>
                                <SelectContent>
                                    {partTypes.map((pt) => (
                                        <SelectItem key={pt.id} value={pt.id}>
                                            {pt.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <div className="flex items-start gap-2">
                                <Checkbox
                                    id="process-reman"
                                    checked={isRemanufactured}
                                    onCheckedChange={(v) => setIsRemanufactured(v === true)}
                                />
                                <div className="grid gap-0.5 leading-none">
                                    <Label htmlFor="process-reman" className="font-normal cursor-pointer">
                                        Remanufacturing
                                    </Label>
                                    <p className="text-xs text-muted-foreground">
                                        Process handles used or core parts.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={resetAndClose}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={!canSubmit || createProcess.isPending}>
                            {createProcess.isPending ? "Creating…" : "Create & open"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
