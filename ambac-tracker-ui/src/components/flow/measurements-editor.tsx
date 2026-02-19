import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Plus, Pencil, Trash2, Ruler } from 'lucide-react';
import { useRetrieveMeasurementDefinitions } from '@/hooks/useRetrieveMeasurementDefinitions';
import { useDeleteMeasurementDefinition } from '@/hooks/useDeleteMeasurementDefinition';
import MeasurementDefinitionForm from '@/components/measurement-definition-form';
import { toast } from 'sonner';

interface MeasurementDefinition {
  id: string;
  label: string;
  type: 'NUMERIC' | 'PASS_FAIL';
  unit?: string;
  nominal?: string | null;
  upper_tol?: string | null;
  lower_tol?: string | null;
  required?: boolean;
}

export interface MeasurementsEditorProps {
  stepId: string;
  stepName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  readOnly?: boolean;
}

export function MeasurementsEditor({ stepId, stepName, open, onOpenChange, readOnly = false }: MeasurementsEditorProps) {
  const [mode, setMode] = useState<'list' | 'add' | 'edit'>('list');
  const [editingMeasurement, setEditingMeasurement] = useState<MeasurementDefinition | null>(null);

  const { data: measurementsResponse, refetch } = useRetrieveMeasurementDefinitions(
    { queries: { step: stepId } },
    { enabled: open }
  );
  const deleteMutation = useDeleteMeasurementDefinition();

  const measurements = measurementsResponse?.results ?? [];

  const handleAdd = () => {
    setEditingMeasurement(null);
    setMode('add');
  };

  const handleEdit = (measurement: MeasurementDefinition) => {
    setEditingMeasurement(measurement);
    setMode('edit');
  };

  const handleDelete = (measurementId: string) => {
    if (!confirm('Are you sure you want to delete this measurement?')) return;

    deleteMutation.mutate(
      { params: { id: measurementId } },
      {
        onSuccess: () => {
          toast.success('Measurement deleted');
          refetch();
        },
        onError: () => {
          toast.error('Failed to delete measurement');
        },
      }
    );
  };

  const handleFormSuccess = () => {
    setMode('list');
    setEditingMeasurement(null);
    refetch();
  };

  const handleFormCancel = () => {
    setMode('list');
    setEditingMeasurement(null);
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setMode('list');
      setEditingMeasurement(null);
    }
    onOpenChange(newOpen);
  };

  const formatTolerance = (measurement: MeasurementDefinition) => {
    if (measurement.type === 'PASS_FAIL') return 'Pass/Fail';
    const parts: string[] = [];
    if (measurement.nominal) {
      parts.push(measurement.nominal);
      if (measurement.unit) parts[0] += ` ${measurement.unit}`;
    }
    if (measurement.lower_tol && measurement.upper_tol) {
      parts.push(`(${measurement.lower_tol} / +${measurement.upper_tol})`);
    }
    return parts.join(' ') || measurement.unit || '-';
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Ruler className="h-5 w-5" />
            {mode === 'list' && `Measurements for "${stepName}"`}
            {mode === 'add' && 'Add Measurement'}
            {mode === 'edit' && 'Edit Measurement'}
          </DialogTitle>
          {mode === 'list' && (
            <DialogDescription>
              Define what measurements are taken at this step
            </DialogDescription>
          )}
        </DialogHeader>

        {mode === 'list' && (
          <div className="space-y-4">
            {measurements.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Ruler className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p>No measurements defined for this step.</p>
                <p className="text-sm">Add measurements to enable quality tracking.</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {measurements.map((measurement) => (
                  <Card key={measurement.id} className="group">
                    <CardContent className="p-3 flex items-center justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{measurement.label}</span>
                          <Badge variant="secondary" className="text-xs">
                            {measurement.type === 'NUMERIC' ? 'Numeric' : 'Pass/Fail'}
                          </Badge>
                          {measurement.required && (
                            <Badge variant="outline" className="text-xs">Required</Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {formatTolerance(measurement)}
                        </p>
                      </div>
                      {!readOnly && (
                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => handleEdit(measurement)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive"
                            onClick={() => handleDelete(measurement.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {!readOnly && (
              <Button onClick={handleAdd} className="w-full">
                <Plus className="h-4 w-4 mr-2" />
                Add Measurement
              </Button>
            )}
          </div>
        )}

        {(mode === 'add' || mode === 'edit') && (
          <MeasurementDefinitionForm
            stepId={stepId}
            existingDefinition={editingMeasurement ?? undefined}
            onSuccess={handleFormSuccess}
            onCancel={handleFormCancel}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
