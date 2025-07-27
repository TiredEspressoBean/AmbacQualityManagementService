import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useState } from "react";
import {z} from 'zod'
import {schemas} from '@/lib/api/generated.ts'
import {PassByStepForm} from "@/components/pass-by-step-form.tsx";
import {useUpdateOrder} from '@/hooks/useUpdateOrder.ts'

type OrderType = z.infer<typeof schemas.Orders>

interface OrderActionsCellProps {
    order: OrderType;
    onPass?: () => void;
    onError?: () => void;
    onArchive?: () => void;
}



export function QAOrderActionsCell({ order, onPass, onError }: OrderActionsCellProps) {
    const [dialog, setDialog] = useState<"pass" | "error" | "archive" | null>(null);
    const { mutate: UpdateOrder, isPending } = useUpdateOrder();
    return (
        <>
            <td className="relative">
                <div className="grid grid-cols-3 gap-6">
                    <Button variant="outline" size="sm" onClick={() => setDialog("pass")}>Pass</Button>
                    <Button variant="outline" size="sm" onClick={() => setDialog("error")}>Edit</Button>
                    <Button variant="outline" size="sm" onClick={() => setDialog("archive")}>Archive</Button>
                </div>

                {/* All Dialogs go here */}
                <Dialog open={dialog === "pass"} onOpenChange={(open) => !open && setDialog(null)}>
                    <DialogContent className="max-w-md">
                        <DialogHeader>
                            <DialogTitle>Pass Part by Step</DialogTitle>
                        </DialogHeader>
                        <PassByStepForm
                            order={order}
                            onSuccess={() => {
                                onPass?.();
                                setDialog(null);
                            }}
                        />
                    </DialogContent>
                </Dialog>

                <Dialog open={dialog === "error"} onOpenChange={(open) => !open && setDialog(null)}>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Edit Order</DialogTitle>
                        </DialogHeader>
                        <Button onClick={() => {
                            onError?.();
                            setDialog(null);
                        }}>Submit</Button>
                    </DialogContent>
                </Dialog>

                <Dialog open={dialog === "archive"} onOpenChange={(open) => !open && setDialog(null)}>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Archive Order</DialogTitle>
                        </DialogHeader>
                        <Button
                            disabled={isPending}
                            onClick={() => {
                                if (!order) return;

                                const newData = {
                                    ...order,
                                    archived: true,
                                };

                                UpdateOrder({ id: order.id, newData });
                                setDialog(null);
                            }}
                        >
                            {isPending ? "Archiving..." : "Submit"}
                        </Button>
                    </DialogContent>
                </Dialog>
            </td>
        </>
    );
}
