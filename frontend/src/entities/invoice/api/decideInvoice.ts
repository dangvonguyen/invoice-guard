import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';
import { translateApiError } from '@/shared/api/errors';

import { toDecision } from '../model/mapper';
import type { Decision } from '../model/types';

export class DecisionConflictError extends Error {
  constructor() {
    super('This invoice already has a final decision');
    this.name = 'DecisionConflictError';
  }
}

export class NotAwaitingReviewError extends Error {
  constructor() {
    super('This invoice is no longer awaiting review');
    this.name = 'NotAwaitingReviewError';
  }
}

// The 409 conflict response isn't declared in the generated OpenAPI schema
// (only 201/422 are), so its shape has to be narrowed from `unknown` by hand.
function conflictErrorCode(error: unknown): string | undefined {
  if (typeof error !== 'object' || error === null || !('error' in error)) return undefined;
  const info = error.error;
  if (typeof info !== 'object' || info === null || !('code' in info)) return undefined;
  return typeof info.code === 'string' ? info.code : undefined;
}

export async function decideInvoice(
  invoiceId: string,
  outcome: Decision['outcome'],
  reason: string,
): Promise<Decision> {
  const {
    data: envelope,
    error,
    response,
  } = await apiClient.POST('/invoices/{invoice_id}/decision', {
    params: { path: { invoice_id: invoiceId } },
    body: { outcome, reason },
  });

  if (error) {
    throw translateApiError(response, error, 'Failed to record decision', {
      409: (conflictError) =>
        conflictErrorCode(conflictError) === 'INVOICE_NOT_AWAITING_REVIEW'
          ? new NotAwaitingReviewError()
          : new DecisionConflictError(),
    });
  }

  const { data: dto } = unwrapEnvelope(envelope);
  return toDecision(dto);
}
