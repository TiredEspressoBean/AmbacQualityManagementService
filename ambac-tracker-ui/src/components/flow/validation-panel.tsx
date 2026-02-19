"use client";

import { useState } from 'react';
import { AlertCircle, AlertTriangle, ChevronDown, ChevronRight, CheckCircle2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { ValidationResult, ValidationIssue } from '@/lib/process-validation';

interface ValidationPanelProps {
  validation: ValidationResult;
  onSelectNode?: (nodeId: string) => void;
  className?: string;
}

function ValidationItem({
  issue,
  onSelect,
}: {
  issue: ValidationIssue;
  onSelect?: () => void;
}) {
  const isError = issue.type === 'error';

  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={!issue.nodeId}
      className={cn(
        'w-full text-left p-2 rounded-md text-sm flex items-start gap-2 transition-colors',
        issue.nodeId && 'hover:bg-accent cursor-pointer',
        !issue.nodeId && 'cursor-default',
        isError ? 'text-destructive' : 'text-amber-600 dark:text-amber-500'
      )}
    >
      {isError ? (
        <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
      ) : (
        <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
      )}
      <span>{issue.message}</span>
    </button>
  );
}

export function ValidationPanel({
  validation,
  onSelectNode,
  className,
}: ValidationPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const { errors, warnings, isValid } = validation;
  const totalIssues = errors.length + warnings.length;

  // No issues - show success state
  if (totalIssues === 0) {
    return (
      <Card className={cn('border-green-500/50 bg-green-50/50 dark:bg-green-950/20', className)}>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm font-medium flex items-center gap-2 text-green-700 dark:text-green-400">
            <CheckCircle2 className="h-4 w-4" />
            Process Valid
          </CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card
      className={cn(
        errors.length > 0
          ? 'border-destructive/50 bg-destructive/5'
          : 'border-amber-500/50 bg-amber-50/50 dark:bg-amber-950/20',
        className
      )}
    >
      <CardHeader className="py-3 px-4">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-between p-0 h-auto hover:bg-transparent"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <CardTitle
            className={cn(
              'text-sm font-medium flex items-center gap-2',
              errors.length > 0 ? 'text-destructive' : 'text-amber-600 dark:text-amber-500'
            )}
          >
            {errors.length > 0 ? (
              <AlertCircle className="h-4 w-4" />
            ) : (
              <AlertTriangle className="h-4 w-4" />
            )}
            Validation Issues
            <Badge
              variant={errors.length > 0 ? 'destructive' : 'secondary'}
              className="ml-1"
            >
              {totalIssues}
            </Badge>
          </CardTitle>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
      </CardHeader>

      {isExpanded && (
        <CardContent className="pt-0 px-2 pb-2">
          <div className="space-y-1">
            {/* Errors first */}
            {errors.map((issue, idx) => (
              <ValidationItem
                key={`error-${idx}`}
                issue={issue}
                onSelect={issue.nodeId ? () => onSelectNode?.(issue.nodeId!) : undefined}
              />
            ))}

            {/* Then warnings */}
            {warnings.map((issue, idx) => (
              <ValidationItem
                key={`warning-${idx}`}
                issue={issue}
                onSelect={issue.nodeId ? () => onSelectNode?.(issue.nodeId!) : undefined}
              />
            ))}
          </div>

          {!isValid && (
            <p className="text-xs text-muted-foreground mt-3 px-2">
              Fix errors before saving or approving
            </p>
          )}
        </CardContent>
      )}
    </Card>
  );
}
