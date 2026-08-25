import { useFetcher } from 'react-router';
import { Loader2 } from 'lucide-react';

import {
  CannotExplainOwnInvoiceError,
  type Explanation,
  NoActivePolicyDocumentError,
  type ReviewFlag,
} from '@/entities/invoice';
import { mapErrorMessage } from '@/shared/lib/errorMessage';
import { Badge } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';

export interface ReviewFlagListProps {
  flags: ReviewFlag[];
}

export function ReviewFlagList({ flags }: ReviewFlagListProps) {
  if (flags.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Review flags</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {flags.map((flag) => (
          <ReviewFlagItem key={flag.code} flag={flag} />
        ))}
      </CardContent>
    </Card>
  );
}

function explainErrorMessage(error: Error): string {
  return mapErrorMessage(error, [
    [
      NoActivePolicyDocumentError,
      "No policy handbook has been ingested yet, so this flag can't be explained.",
    ],
    [CannotExplainOwnInvoiceError, "You can't request an explanation for your own submission."],
  ]);
}

function ReviewFlagItem({ flag }: { flag: ReviewFlag }) {
  const fetcher = useFetcher<Error | Explanation>();
  const isLoading = fetcher.state !== 'idle';
  const result = fetcher.data;
  const explanation =
    result !== undefined && result !== null && !(result instanceof Error) ? result : null;
  const errorMessage = result instanceof Error ? explainErrorMessage(result) : null;

  return (
    <details className="rounded-lg bg-muted/50 p-3 text-sm">
      <summary className="flex cursor-pointer items-center justify-between gap-3 font-medium">
        <span>{flag.summary ?? flag.code}</span>
        <Badge variant="outline">{flag.code}</Badge>
      </summary>
      <pre className="mt-2 overflow-x-auto text-xs text-muted-foreground">
        {JSON.stringify(flag.evidence, null, 2)}
      </pre>
      {flag.explainable && explanation === null && (
        <div className="mt-3 flex flex-col gap-2">
          <fetcher.Form method="post">
            <input type="hidden" name="intent" value="explain" />
            <input type="hidden" name="ruleCode" value={flag.code} />
            <Button type="submit" size="sm" variant="outline" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="animate-spin" aria-hidden="true" />
                  Explaining…
                </>
              ) : (
                'Explain'
              )}
            </Button>
          </fetcher.Form>
          {errorMessage !== null && (
            <p role="alert" className="text-destructive">
              {errorMessage}
            </p>
          )}
        </div>
      )}
      {explanation !== null && <ExplanationBlock explanation={explanation} />}
    </details>
  );
}

function ExplanationBlock({ explanation }: { explanation: Explanation }) {
  return (
    <div className="mt-3 flex flex-col gap-2 rounded-md bg-background p-3">
      <p>{explanation.explanation}</p>
      {explanation.citations.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium text-muted-foreground">Citations</p>
          <ul className="flex flex-col gap-1 text-xs text-muted-foreground">
            {explanation.citations.map((citation) => (
              <li key={citation.chunkId}>
                {citation.sectionLabel !== null && (
                  <span className="font-medium">{citation.sectionLabel}: </span>
                )}
                {citation.content}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
