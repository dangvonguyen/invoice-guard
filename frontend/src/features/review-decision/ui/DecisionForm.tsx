import { useState } from 'react';
import { useFetcher } from 'react-router';

import { DecisionConflictError } from '@/entities/invoice';
import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Field, FieldError, FieldGroup, FieldLabel } from '@/shared/ui/field';
import { Textarea } from '@/shared/ui/textarea';
import { ToggleGroup, ToggleGroupItem } from '@/shared/ui/toggle-group';

type Outcome = 'approved' | 'rejected';

export function DecisionForm() {
  const fetcher = useFetcher<Error>();
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const isSubmitting = fetcher.state !== 'idle';
  const errorMessage =
    fetcher.data instanceof DecisionConflictError
      ? 'Already decided by another reviewer.'
      : (fetcher.data?.message ?? null);

  function handleOutcomeChange(values: string[]): void {
    const [value] = values;
    setOutcome(value === 'approved' || value === 'rejected' ? value : null);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Record</CardTitle>
      </CardHeader>
      <CardContent>
        <fetcher.Form method="post">
          <FieldGroup>
            <Field>
              <FieldLabel>Decision</FieldLabel>
              <ToggleGroup
                variant="outline"
                value={outcome ? [outcome] : []}
                onValueChange={handleOutcomeChange}
              >
                <ToggleGroupItem value="approved">Approve</ToggleGroupItem>
                <ToggleGroupItem value="rejected">Reject</ToggleGroupItem>
              </ToggleGroup>
              <input type="hidden" name="outcome" value={outcome ?? ''} />
            </Field>

            <Field>
              <FieldLabel htmlFor="decision-reason">Reason</FieldLabel>
              <Textarea
                id="decision-reason"
                name="reason"
                required
                minLength={1}
                placeholder="Explain the decision"
              />
            </Field>

            <FieldError>{errorMessage}</FieldError>

            <div className="flex justify-end">
              <Button type="submit" disabled={isSubmitting || outcome === null}>
                Submit
              </Button>
            </div>
          </FieldGroup>
        </fetcher.Form>
      </CardContent>
    </Card>
  );
}
