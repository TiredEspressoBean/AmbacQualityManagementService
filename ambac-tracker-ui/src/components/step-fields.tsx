import {
    FormField,
    FormItem,
    FormLabel,
    FormControl,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";
import { DurationInput } from "@/components/ui/duration-input";
import type { Control } from "react-hook-form";
import SamplingRulesEditor from "@/components/SamplingRulesEditor";
import MeasurementDefinitionsManager from "@/components/measurement-definitions-manager";

type StepFieldsProps = {
    name: string;
    index: number;
    control: Control<any>;
    existingStepId?: number;
    existingStepName?: string;
};

export default function StepFields({ name, index, control, existingStepId, existingStepName }: StepFieldsProps) {
    return (
        <div className="border rounded-md p-4 space-y-4">
            <h3 className="text-lg font-medium mb-2">Step {index + 1}</h3>

            <FormField
                control={control}
                name={`${name}.${index}.name`}
                render={({ field }) => (
                    <FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                            <Input placeholder="e.g. Assembly" {...field} />
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                )}
            />

            <FormField
                control={control}
                name={`${name}.${index}.description`}
                render={({ field }) => (
                    <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                            <Textarea placeholder="Optional description of this step" {...field} />
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                )}
            />

            <FormField
                control={control}
                name={`${name}.${index}.expected_duration`}
                render={({ field }) => (
                    <FormItem>
                        <FormLabel>Expected Duration</FormLabel>
                        <FormControl>
                            <DurationInput
                                value={field.value}
                                onChange={field.onChange}
                                placeholder="HH:MM:SS"
                            />
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                )}
            />

            <Accordion type="single" collapsible>
                <AccordionItem value={`sampling-rules-${index}`}>
                    <AccordionTrigger className="text-sm font-medium">Sampling Rules (Optional)</AccordionTrigger>
                    <AccordionContent className="space-y-4">
                        <SamplingRulesEditor name={`steps.${index}.sampling_rules`} />
                        <SamplingRulesEditor name={`steps.${index}.fallback_rules`} label="Fallback Rules" />
                        
                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={control}
                                name={`${name}.${index}.fallback_threshold`}
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Fallback Threshold</FormLabel>
                                        <FormControl>
                                            <Input
                                                type="number"
                                                placeholder="e.g. 5"
                                                {...field}
                                                value={field.value || ""}
                                                onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : null)}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={control}
                                name={`${name}.${index}.fallback_duration`}
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Fallback Duration</FormLabel>
                                        <FormControl>
                                            <Input
                                                type="number"
                                                placeholder="e.g. 10"
                                                {...field}
                                                value={field.value || ""}
                                                onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : null)}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>
                    </AccordionContent>
                </AccordionItem>
            </Accordion>

            {existingStepId && (
                <MeasurementDefinitionsManager
                    stepId={existingStepId}
                    stepName={existingStepName}
                />
            )}
        </div>
    );
}
