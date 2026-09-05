import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';
import { translateApiError } from '@/shared/api/errors';

import { toClaim } from '../model/mapper';
import type { Claim } from '../model/types';

export class NotFoundError extends Error {
  constructor() {
    super('Claim not found');
    this.name = 'NotFoundError';
  }
}

export async function getClaim(claimId: string): Promise<Claim> {
  const {
    data: envelope,
    error,
    response,
  } = await apiClient.GET('/claims/{claim_id}', {
    params: { path: { claim_id: claimId } },
  });

  if (error) {
    throw translateApiError(response, error, 'Failed to fetch claim', {
      404: () => new NotFoundError(),
    });
  }

  const { data: dto } = unwrapEnvelope(envelope);
  return toClaim(dto);
}
