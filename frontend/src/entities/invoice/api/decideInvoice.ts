import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';

import { toDecision } from '../model/mapper';
import type { Decision } from '../model/types';

export class DecisionConflictError extends Error {
  constructor() {
    super('This invoice already has a final decision');
    this.name = 'DecisionConflictError';
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
    if (response.status === 409) throw new DecisionConflictError();
    throw new Error('Failed to record decision');
  }

  const { data: dto } = unwrapEnvelope(envelope);
  return toDecision(dto);
}
