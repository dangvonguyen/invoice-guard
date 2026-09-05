import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';
import { translateApiError } from '@/shared/api/errors';
import type { ApiMeta } from '@/shared/api/types';

import { toClaimSummary } from '../model/mapper';
import type { ClaimSummary } from '../model/types';

export interface ListClaimsParams {
  needsAction?: boolean;
  offset?: number;
  limit?: number;
}

export interface ClaimListPage {
  claims: ClaimSummary[];
  meta: ApiMeta | null;
}

export async function listClaims(params: ListClaimsParams = {}): Promise<ClaimListPage> {
  const {
    data: envelope,
    error,
    response,
  } = await apiClient.GET('/claims', {
    params: {
      query: {
        needs_action: params.needsAction,
        offset: params.offset,
        limit: params.limit,
      },
    },
  });

  if (error) {
    throw translateApiError(response, error, 'Failed to fetch claims');
  }

  const { data: dtos, meta } = unwrapEnvelope(envelope);
  return { claims: dtos.map(toClaimSummary), meta };
}
