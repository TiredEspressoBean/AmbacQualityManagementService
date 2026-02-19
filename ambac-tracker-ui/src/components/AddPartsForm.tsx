import { useForm } from "@tanstack/react-form";
import { useStore } from "@tanstack/react-store";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Command, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { schemas } from "@/lib/api/generated.ts";
import { z } from "zod";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes.ts";
import { useRetrieveProcesses } from "@/hooks/useRetrieveProcesses.ts";

// Zod schema and types
type AddPartsData = z.infer<typeof schemas.BulkAddPartsInputRequest>;
const AddPartsSchema = schemas.BulkAddPartsInputRequest;
const PartStatusEnum = schemas.PartsStatusEnum.options;
const PartStatusValues = schemas.PartsStatusEnum.options;
type PartStatus = (typeof PartStatusValues)[number];

const defaults = {} as z.infer<typeof AddPartsSchema>;

export interface AddPartsFormProps {
  onSubmit: (data: AddPartsData) => void;
}

export function AddPartsForm({ onSubmit }: AddPartsFormProps) {
  const form = useForm({
        defaultValues: defaults,
        onSubmit: ({ value }) => onSubmit(value),
        validators: { onSubmit: AddPartsSchema },
    });

  // Extract Field, Subscribe, and store
const { Field, Subscribe, store } = form;

    // subscribe to values
  const partTypeId = useStore(store, (s) => s.values.part_type);
  const processId = useStore(store, (s) => s.values.process_id);
  const stepId = useStore(store, (s) => s.values.step);

    const partTypesQuery = useRetrievePartTypes();
    const processQuery = useRetrieveProcesses({ part_type: partTypeId || undefined });

    const selectedPartType = partTypesQuery.data?.results?.find((pt) => pt.id === partTypeId);
    const selectedProcess = processQuery.data?.results?.find((p) => p.id === processId);
    // Process steps are accessed via process_steps junction table
    const processSteps = (selectedProcess as unknown as { process_steps?: Array<{ step: { id: string; name: string; description?: string } }> })?.process_steps || [];
    const steps = processSteps.map((ps) => ps.step);

    const [openPartType, setOpenPartType] = useState(false);
    const [openProcess, setOpenProcess] = useState(false);
    const [openStep, setOpenStep] = useState(false);

    return (
        <form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
                void form.handleSubmit();
            }}
            className="space-y-4 p-4"
        >
            {/* Part Type */}
            <Field name="part_type">
                {(field) => (
                    <>
                        <Label>Part Type</Label>
                        <Popover open={openPartType} onOpenChange={setOpenPartType}>
                            <PopoverTrigger asChild>
                                <Button
                                    variant="outline"
                                    className="w-full justify-start"
                                    onClick={() => setOpenPartType(true)}
                                >
                                    {selectedPartType?.name || "Select part type"}
                                </Button>
                            </PopoverTrigger>
                            <PopoverContent className="p-0 w-full">
                                <Command>
                                    <CommandInput placeholder="Search part type..." />
                                    <CommandList>
                                        {partTypesQuery.data?.results?.map((pt) => (
                                            <CommandItem
                                                key={pt.id}
                                                onSelect={() => {
                                                    field.setValue(pt.id);
                                                    setOpenPartType(false);
                                                }}
                                            >
                                                {pt.name}
                                            </CommandItem>
                                        ))}
                                    </CommandList>
                                </Command>
                            </PopoverContent>
                        </Popover>
                        {!field.state.meta.isValid && (
                            <p className="text-sm text-red-600">
                                {field.state.meta.errors.join(', ')}
                            </p>
                        )}
                    </>
                )}
            </Field>

            {/* Process */}
            <Field name="process_id"
                   listeners={{
                       onChange: ({ fieldApi, value }) => {
                           // default step to first step of the selected process
                           const proc = processQuery.data?.results?.find((p) => p.id === value);
                           const procSteps = (proc as unknown as { process_steps?: Array<{ step: { id: string } }> })?.process_steps || [];
                           const firstStepId = procSteps[0]?.step?.id;
                           if (firstStepId !== undefined) {
                               fieldApi.form.setFieldValue("step", firstStepId);
                           }
                       },
                   }}
            >
                {(field) => (
                    <>
                        <Label>Process</Label>
                        <Popover open={openProcess} onOpenChange={setOpenProcess}>
                            <PopoverTrigger asChild>
                                <Button
                                    variant="outline"
                                    className={cn(
                                        "w-full justify-start",
                                        !partTypeId && "opacity-50 cursor-not-allowed"
                                    )}
                                    disabled={!partTypeId}
                                    onClick={() => setOpenProcess(true)}
                                >
                                    {selectedProcess?.name || "Select process"}
                                </Button>
                            </PopoverTrigger>
                            <PopoverContent className="p-0 w-full">
                                <Command>
                                    <CommandInput placeholder="Search process..." />
                                    <CommandList>
                                        {processQuery.isLoading ? (
                                            <CommandItem disabled>
                                                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading...
                                            </CommandItem>
                                        ) : (
                                            processQuery.data?.results?.map((proc) => (
                                                <CommandItem
                                                    key={proc.id}
                                                    onSelect={() => {
                                                        field.setValue(proc.id);
                                                        setOpenProcess(false);
                                                    }}
                                                >
                                                    {proc.name}
                                                </CommandItem>
                                            ))
                                        )}
                                    </CommandList>
                                </Command>
                            </PopoverContent>
                        </Popover>
                        {!field.state.meta.isValid && (
                            <p className="text-sm text-red-600">
                                {field.state.meta.errors.join(', ')}
                            </p>
                        )}
                    </>
                )}
            </Field>

            {/* Step */}
            <Field name="step">
                {(field) => (
                    <>
                        <Label>Step</Label>
                        <Popover open={openStep} onOpenChange={setOpenStep}>
                            <PopoverTrigger asChild>
                                <Button
                                    variant="outline"
                                    className={cn(
                                        "w-full justify-start",
                                        steps.length === 0 && "opacity-50 cursor-not-allowed"
                                    )}
                                    disabled={!steps.length}
                                    onClick={() => setOpenStep(true)}
                                >
                                    {steps.find((s: { id: string; name: string; description?: string }) => s.id === stepId)?.name || "Select step"}
                                </Button>
                            </PopoverTrigger>
                            <PopoverContent className="p-0 w-full">
                                <Command>
                                    <CommandInput placeholder="Search step..." />
                                    <CommandList>
                                        {steps.map((step: { id: string; name: string; description?: string }) => (
                                            <CommandItem
                                                key={step.id}
                                                onSelect={() => {
                                                    field.setValue(step.id);
                                                    setOpenStep(false);
                                                }}
                                            >
                                                {step.description}
                                            </CommandItem>
                                        ))}
                                    </CommandList>
                                </Command>
                            </PopoverContent>
                        </Popover>
                        {!field.state.meta.isValid && (
                            <p className="text-sm text-red-600">
                                {field.state.meta.errors.join(', ')}
                            </p>
                        )}
                    </>
                )}
            </Field>

            {/* Quantity */}
            <Field name="quantity">
                {(field) => (
                    <>
                        <Label>Quantity</Label>
                        <Input
                            type="number"
                            value={field.state.value ?? ''}
                            onChange={(e) => field.setValue(Number(e.target.value))}
                        />
                        {!field.state.meta.isValid && (
                            <p className="text-sm text-red-600">
                                {field.state.meta.errors.join(', ')}
                            </p>
                        )}
                    </>
                )}
            </Field>

            {/* ERP ID */}
            <Field name="ERP_id">
                {(field) => (
                    <>
                        <Label>ERP ID</Label>
                        <span className="text-sm font-medium text-muted-foreground">
              {selectedPartType?.ID_prefix || ''}
            </span>
                        <Input
                            type="text"
                            value={field.state.value ?? ''}
                            onChange={(e) => field.setValue(e.target.value)}
                        />
                        {!field.state.meta.isValid && (
                            <p className="text-sm text-red-600">
                                {field.state.meta.errors.join(', ')}
                            </p>
                        )}
                    </>
                )}
            </Field>

      {/* Status Field */}
            <Field name="part_status">
                {(field) => (
                    <>
                        <Label>Status</Label>
                        <Select
                            value={field.state.value}
                            onValueChange={(val) => field.setValue(val as PartStatus)}
                        >
                            <SelectTrigger className="w-full">
                                <SelectValue placeholder="Select status" />
                            </SelectTrigger>
                            <SelectContent>
                                {PartStatusEnum.map((s) => (
                                    <SelectItem key={s} value={s}>
                    {s.replace(/_/g, " ")}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {!field.state.meta.isValid && (
                            <p className="text-sm text-red-600">
                {field.state.meta.errors.join(", ")}
                            </p>
                        )}
                    </>
                )}
            </Field>

            <Subscribe selector={(s) => s.canSubmit}>
                {(canSubmit) => (
                    <Button type="submit" disabled={!canSubmit}>
                        Add Parts
                    </Button>
                )}
            </Subscribe>
        </form>
    );
}
