import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';

import type { ExtractionConfidence } from '../model/types';

import { ConfidenceBadge } from './ConfidenceBadge';

export interface ExtractedFieldsTableProps {
  fields: Record<string, unknown> | null;
  confidence: ExtractionConfidence | null;
  confidenceReason: string | null;
}

export function ExtractedFieldsTable({
  fields,
  confidence,
  confidenceReason,
}: ExtractedFieldsTableProps) {
  const entries = fields === null ? [] : Object.entries(fields);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex justify-between">
          <span>Extracted fields</span>
          {confidence && <ConfidenceBadge confidence={confidence} />}
        </CardTitle>
        {confidenceReason !== null && (
          <p className="text-sm text-muted-foreground">{confidenceReason}</p>
        )}
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">No extracted fields available.</p>
        ) : (
          <dl className="grid grid-cols-2 gap-3 text-sm">
            {entries.map(([key, value]) => (
              <div key={key}>
                <dt className="text-muted-foreground">{key}</dt>
                <dd className="font-medium">{String(value)}</dd>
              </div>
            ))}
          </dl>
        )}
      </CardContent>
    </Card>
  );
}
