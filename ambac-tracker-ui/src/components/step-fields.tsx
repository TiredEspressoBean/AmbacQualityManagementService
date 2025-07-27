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
import type { Control } from "react-hook-form";
import SamplingRulesEditor from "@/components/SamplingRulesEditor"; // ✅ adjust path as needed

type StepFieldsProps = {
    name: string;
    index: number;
    control: Control<any>;
};

export default function StepFields({ name, index, control }: StepFieldsProps) {
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
                        <FormLabel>Expected Duration (minutes)</FormLabel>
                        <FormControl>
                            <Input type="number" placeholder="e.g. 30" {...field} />
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                )}
            />

            <Accordion type="single" collapsible>
                <AccordionItem value={`sampling-rules-${index}`}>
                    <AccordionTrigger className="text-sm font-medium">Sampling Rules (Optional)</AccordionTrigger>
                    <AccordionContent>
                        <SamplingRulesEditor name={`steps.${index}.sampling_rules`} />
                    </AccordionContent>
                </AccordionItem>
            </Accordion>
        </div>
    );
}
