"use client"

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, Settings } from "lucide-react";
import { useFieldArray, useFormContext } from "react-hook-form";
import { useEffect } from "react";
import SamplingRuleCard from "./sampling-rule-card";
import SamplingRuleForm from "./sampling-rule-form";

type SamplingRulesEditorProps = {
    name: string;   // e.g. "rules" or "fallback_rules"
    label?: string; // e.g. "Sampling Rules" or "Fallback Rules"
};

export default function SamplingRulesEditor({ name, label = "Sampling Rules" }: SamplingRulesEditorProps) {
    const { control, getValues, setValue } = useFormContext();
    const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

    const { fields, append, remove, update } = useFieldArray({ control, name });

    // Ensure initialized on mount
    useEffect(() => {
        const current = getValues(name);
        if (!Array.isArray(current)) {
            setValue(name, []);
        }
    }, [getValues, name, setValue]);

    const handleCreateSuccess = (newRule: any) => {
        // Use the order from the form, or default to the next available order
        const order = newRule.order || (fields.length + 1);
        append({
            ...newRule,
            order: order,
        });
        setIsCreateDialogOpen(false);
    };

    const handleUpdateRule = (index: number, updatedRule: any) => {
        update(index, {
            ...updatedRule,
            // Preserve the user-defined order from the form
        });
    };

    const handleDeleteRule = (index: number) => {
        remove(index);
    };

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <div className="flex items-center space-x-2">
                    <Settings className="h-4 w-4" />
                    <span className="font-medium">
                        {label} ({fields.length})
                    </span>
                </div>
                <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
                    <DialogTrigger asChild>
                        <Button size="sm">
                            <Plus className="h-4 w-4 mr-2" />
                            Add Rule
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-md">
                        <DialogHeader>
                            <DialogTitle>Create Sampling Rule</DialogTitle>
                        </DialogHeader>
                        <SamplingRuleForm
                            onSuccess={handleCreateSuccess}
                            onCancel={() => setIsCreateDialogOpen(false)}
                        />
                    </DialogContent>
                </Dialog>
            </div>

            {fields.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground border rounded-md">
                    <Settings className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No sampling rules defined.</p>
                    <p className="text-sm">Click "Add Rule" to get started.</p>
                </div>
            ) : (
                <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
                    {fields.map((field, index) => (
                        <SamplingRuleCard
                            key={field.id}
                            rule={field as any}
                            index={index}
                            onUpdate={handleUpdateRule}
                            onDelete={() => handleDeleteRule(index)}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
