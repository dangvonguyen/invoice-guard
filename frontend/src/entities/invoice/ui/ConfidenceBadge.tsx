import { Badge } from '@/shared/ui/badge';

import type { ExtractionConfidence } from '../model/types';

export interface ConfidenceBadgeProps {
  confidence: ExtractionConfidence;
}

const CONFIDENCE_LABELS: Record<ExtractionConfidence, string> = {
  high: 'High confidence',
  low: 'Low confidence',
};

const CONFIDENCE_VARIANTS: Record<ExtractionConfidence, 'secondary' | 'destructive'> = {
  high: 'secondary',
  low: 'destructive',
};

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  return <Badge variant={CONFIDENCE_VARIANTS[confidence]}>{CONFIDENCE_LABELS[confidence]}</Badge>;
}
