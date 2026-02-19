"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Pencil, Trash2 } from "lucide-react";
import { ruleTypes } from "@/lib/RuleTypesEnum.ts";
import SamplingRuleForm from "./sampling-rule-form";

interface SamplingRule {
  id?: string;
  rule_type: string;
  value: number | null;
  order: number;
}

interface SamplingRuleCardProps {
  rule: SamplingRule;
  index: number;
  onUpdate?: (index: number, rule: SamplingRule) => void;
  onDelete?: () => void;
}

export default function SamplingRuleCard({
  rule,
  index,
  onUpdate,
  onDelete,
}: SamplingRuleCardProps) {
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);

  const handleEditSuccess = (updatedRule: any) => {
    setIsEditDialogOpen(false);
    onUpdate?.(index, updatedRule);
  };

  const handleDelete = () => {
    onDelete?.();
  };

  // Format rule as a readable description
  const formatRuleDescription = (): string => {
    const value = rule.value;
    switch (rule.rule_type) {
      case "EVERY_NTH":
        return `Every ${value ?? "N"}th part`;
      case "PERCENTAGE":
        return `${value ?? 0}% random sampling`;
      case "FIRST_N":
        return `First ${value ?? "N"} parts`;
      case "LAST_N":
        return `Last ${value ?? "N"} parts`;
      case "FIRST_AND_LAST":
        return "First and last parts";
      case "ALL":
        return "100% inspection";
      case "NONE":
        return "No sampling";
      default: {
        const ruleType = ruleTypes.find(type => type.value === rule.rule_type);
        return ruleType?.label || rule.rule_type;
      }
    }
  };

  return (
    <div className="group flex items-center gap-3 px-3 py-2 rounded-md border bg-card hover:bg-accent/50 transition-colors">
      {/* Order badge */}
      <Badge variant="secondary" className="h-6 w-6 p-0 flex items-center justify-center text-xs shrink-0">
        {index + 1}
      </Badge>

      {/* Rule description - full width, no truncation */}
      <span className="flex-1 text-sm font-medium">
        {formatRuleDescription()}
      </span>

      {/* Actions - always visible for better discoverability */}
      <div className="flex items-center gap-1 shrink-0">
        <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
          <DialogTrigger asChild>
            <Button type="button" variant="ghost" size="icon" className="h-7 w-7">
              <Pencil className="h-3.5 w-3.5" />
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-xl">
            <DialogHeader>
              <DialogTitle>Edit Sampling Rule</DialogTitle>
            </DialogHeader>
            <SamplingRuleForm
              existingRule={rule}
              onSuccess={handleEditSuccess}
              onCancel={() => setIsEditDialogOpen(false)}
            />
          </DialogContent>
        </Dialog>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button type="button" variant="ghost" size="icon" className="h-7 w-7 text-destructive hover:text-destructive">
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Sampling Rule</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete this sampling rule? This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDelete}
                className="bg-destructive text-destructive-foreground"
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}
