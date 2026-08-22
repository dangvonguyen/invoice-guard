import { Badge } from '@/shared/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';

import type { ReviewFlag } from '../model/types';

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
          <details key={flag.code} className="rounded-lg bg-muted/50 p-3 text-sm">
            <summary className="flex cursor-pointer items-center justify-between gap-3 font-medium">
              <span>{flag.summary ?? flag.code}</span>
              <Badge variant="outline">{flag.code}</Badge>
            </summary>
            <pre className="mt-2 overflow-x-auto text-xs text-muted-foreground">
              {JSON.stringify(flag.evidence, null, 2)}
            </pre>
          </details>
        ))}
      </CardContent>
    </Card>
  );
}
