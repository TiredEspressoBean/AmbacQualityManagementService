import { z } from "zod";
import { useForm } from "@tanstack/react-form";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";
import { useGetStepDistribution } from "@/hooks/useGetStepDistribution";
import { usePartsIncrementMutation } from "@/hooks/useIncrementDealsPartsSubset";
import { schemas } from "@/lib/api/generated";

type OrderType = z.infer<typeof schemas.Orders>;

interface PassByStepFormProps {
    order: OrderType;
    onSuccess?: () => void;
}

export function PassByStepForm({ order, onSuccess }: PassByStepFormProps) {
    const { data, isLoading } = useGetStepDistribution(order.id);
    const mutation = usePartsIncrementMutation();

    const steps = data?.pages?.flatMap((page) => page.results) ?? [];

    const form = useForm({
        defaultValues: {
            stepId: "",
        },
        onSubmit: async ({ value }) => {
            await mutation.mutateAsync(
                { orderId: order.id, stepId: Number(value.stepId) },
                {
                    onSuccess: () => {
                        toast.success("Part passed to next step.");
                        onSuccess?.();
                    },
                    onError: () => {
                        toast.error("Failed to pass part.");
                    },
                }
            );
        },
    });

    return (
        <form
            onSubmit={(e) => {
                e.preventDefault();
                form.handleSubmit(); // explicitly trigger your async submit logic
            }}
            className="space-y-4"
        >
            <form.Field
                name="stepId"
                children={(field) => (
                    <div className="space-y-2">
                        <Label className="text-sm font-medium">Select Step</Label>
                        <ScrollArea className="h-64 rounded-md border px-2 py-1">
                            <RadioGroup
                                value={field.state.value}
                                onValueChange={(val) => field.handleChange(val)}
                            >
                                {isLoading ? (
                                    <p className="text-sm text-muted-foreground">Loading steps...</p>
                                ) : steps.length === 0 ? (
                                    <p className="text-sm text-muted-foreground">No steps available.</p>
                                ) : (
                                    steps.map((step) => (
                                        <div
                                            key={step.id}
                                            className="flex items-center justify-between py-1"
                                        >
                                            <div className="flex items-center space-x-2">
                                                <RadioGroupItem
                                                    value={String(step.id)}
                                                    id={`step-${step.id}`}
                                                />
                                                <Label
                                                    htmlFor={`step-${step.id}`}
                                                    className="cursor-pointer text-sm font-normal"
                                                >
                                                    {step.name}
                                                </Label>
                                            </div>
                                            <span className="text-xs text-muted-foreground">
                        {step.count} parts
                      </span>
                                        </div>
                                    ))
                                )}
                            </RadioGroup>
                        </ScrollArea>
                        {field.state.meta.errors?.[0] && (
                            <p className="text-sm text-destructive mt-1">
                                {field.state.meta.errors[0]}
                            </p>
                        )}
                    </div>
                )}
            />

            <Button type="submit" disabled={mutation.isPending} className="w-full">
                {mutation.isPending ? "Passing..." : "Submit"}
            </Button>
        </form>
    );
}
