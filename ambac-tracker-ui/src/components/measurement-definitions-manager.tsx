"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, Plus, Ruler } from "lucide-react";
import { useRetrieveMeasurementDefinitions } from "@/hooks/useRetrieveMeasurementDefinitions";
import MeasurementDefinitionCard from "./measurement-definition-card";
import MeasurementDefinitionForm from "./measurement-definition-form";

interface MeasurementDefinitionsManagerProps {
  stepId: string;
  stepName?: string;
}

export default function MeasurementDefinitionsManager({
  stepId,
  stepName,
}: MeasurementDefinitionsManagerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  const { data: measurementDefinitions, refetch } = useRetrieveMeasurementDefinitions({
    queries: { step: stepId },
  });

  const definitions = measurementDefinitions?.results || [];

  const handleCreateSuccess = () => {
    setIsCreateDialogOpen(false);
    refetch();
  };

  const handleUpdate = () => {
    refetch();
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full">
      <CollapsibleTrigger asChild>
        <Button
          variant="outline"
          className="w-full justify-between p-4 h-auto"
          type="button"
        >
          <div className="flex items-center space-x-2">
            <Ruler className="h-4 w-4" />
            <span>
              Measurements ({definitions.length})
              {stepName && (
                <span className="text-muted-foreground ml-2">— {stepName}</span>
              )}
            </span>
          </div>
          <ChevronDown
            className={`h-4 w-4 transition-transform ${
              isOpen ? "rotate-180" : ""
            }`}
          />
        </Button>
      </CollapsibleTrigger>

      <CollapsibleContent className="space-y-4 pt-4">
        <div className="flex justify-between items-center">
          <p className="text-sm text-muted-foreground">
            Define what measurements need to be taken for this step.
          </p>
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Measurement
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Create Measurement Definition</DialogTitle>
              </DialogHeader>
              <MeasurementDefinitionForm
                stepId={stepId}
                onSuccess={handleCreateSuccess}
                onCancel={() => setIsCreateDialogOpen(false)}
              />
            </DialogContent>
          </Dialog>
        </div>

        {definitions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Ruler className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No measurements defined for this step.</p>
            <p className="text-sm">Click "Add Measurement" to get started.</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
            {definitions.map((definition) => (
              <MeasurementDefinitionCard
                key={definition.id}
                definition={definition}
                onUpdate={handleUpdate}
              />
            ))}
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}