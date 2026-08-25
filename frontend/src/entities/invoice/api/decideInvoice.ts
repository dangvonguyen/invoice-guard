import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';
import { errorCode, translateApiError } from '@/shared/api/errors';

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
        errorCode(conflictError) === 'INVOICE_NOT_AWAITING_REVIEW'
          ? new NotAwaitingReviewError()
          : new DecisionConflictError(),
    });
  }

  const { data: dto } = unwrapEnvelope(envelope);
  return toDecision(dto);
}
