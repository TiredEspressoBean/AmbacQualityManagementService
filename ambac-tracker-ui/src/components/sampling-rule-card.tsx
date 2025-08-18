"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Edit, Trash2 } from "lucide-react";
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

  const getRuleTypeLabel = (value: string) => {
    const ruleType = ruleTypes.find(type => type.value === value);
    return ruleType?.label || value;
  };

  const formatValue = (value: number | null): string => {
    if (value === null || value === undefined) return "—";
    return value.toString();
  };

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-medium">
          Rule #{index + 1}
        </CardTitle>
        <div className="flex items-center space-x-2">
          <Badge variant="outline">
            {getRuleTypeLabel(rule.rule_type)}
          </Badge>
          <div className="flex items-center space-x-1">
            <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <Edit className="h-4 w-4" />
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
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
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-destructive">
                  <Trash2 className="h-4 w-4" />
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
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Type:</span>
          <span className="font-medium">{getRuleTypeLabel(rule.rule_type)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Value:</span>
          <span className="font-mono">{formatValue(rule.value)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Order:</span>
          <span className="font-mono">{rule.order}</span>
        </div>
      </CardContent>
    </Card>
  );
}