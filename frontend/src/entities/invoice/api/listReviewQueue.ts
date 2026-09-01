import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';
import { translateApiError } from '@/shared/api/errors';

import { toReviewQueueItem } from '../model/mapper';
import type { ReviewQueueItem } from '../model/types';

export async function listReviewQueue(): Promise<ReviewQueueItem[]> {
  const { data: envelope, error, response } = await apiClient.GET('/review-queue');

  if (error) {
    throw translateApiError(response, error, 'Failed to fetch review queue');
  }

  const { data: dtos } = unwrapEnvelope(envelope);
  return dtos.map(toReviewQueueItem);
}
