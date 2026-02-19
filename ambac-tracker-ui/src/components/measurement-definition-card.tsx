"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Edit, Trash2 } from "lucide-react";
import { useDeleteMeasurementDefinition } from "@/hooks/useDeleteMeasurementDefinition";
import { toast } from "sonner";
import MeasurementDefinitionForm from "./measurement-definition-form";

interface MeasurementDefinition {
  id: string;
  label: string;
  type: "NUMERIC" | "PASS_FAIL";
  unit?: string;
  nominal?: string | null;
  upper_tol?: string | null;
  lower_tol?: string | null;
  required?: boolean;
  step: string;
}

interface MeasurementDefinitionCardProps {
  definition: MeasurementDefinition;
  onUpdate?: () => void;
}

export default function MeasurementDefinitionCard({
  definition,
  onUpdate,
}: MeasurementDefinitionCardProps) {
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const deleteMutation = useDeleteMeasurementDefinition();

  const handleDelete = () => {
    deleteMutation.mutate(definition.id, {
      onSuccess: () => {
        toast.success("Measurement definition deleted successfully!");
        onUpdate?.();
      },
      onError: (error) => {
        console.error("Failed to delete measurement definition:", error);
        toast.error("Failed to delete measurement definition.");
      },
    });
  };

  const handleEditSuccess = () => {
    setIsEditDialogOpen(false);
    onUpdate?.();
  };

  const formatValue = (value: string | null | undefined): string => {
    if (!value) return "—";
    return value;
  };

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-medium">{definition.label}</CardTitle>
        <div className="flex items-center space-x-2">
          <Badge variant={definition.type === "NUMERIC" ? "default" : "outline"}>
            {definition.type}
          </Badge>
          <div className="flex items-center space-x-1">
            <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <Edit className="h-4 w-4" />
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Edit Measurement Definition</DialogTitle>
                </DialogHeader>
                <MeasurementDefinitionForm
                  stepId={definition.step}
                  existingDefinition={definition}
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
                  <AlertDialogTitle>Delete Measurement Definition</AlertDialogTitle>
                  <AlertDialogDescription>
                    Are you sure you want to delete "{definition.label}"? This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={handleDelete}
                    disabled={deleteMutation.isPending}
                    className="bg-destructive text-destructive-foreground"
                  >
                    {deleteMutation.isPending ? "Deleting..." : "Delete"}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {definition.type === "NUMERIC" && (
          <div className="space-y-2">
            {definition.unit && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Unit:</span>
                <span className="font-mono">{definition.unit}</span>
              </div>
            )}
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="text-center">
                <div className="text-muted-foreground">Lower</div>
                <div className="font-mono">{formatValue(definition.lower_tol)}</div>
              </div>
              <div className="text-center">
                <div className="text-muted-foreground">Nominal</div>
                <div className="font-mono font-medium">{formatValue(definition.nominal)}</div>
              </div>
              <div className="text-center">
                <div className="text-muted-foreground">Upper</div>
                <div className="font-mono">{formatValue(definition.upper_tol)}</div>
              </div>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          {definition.required && (
            <Badge variant="default" className="text-xs">
              Required
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}