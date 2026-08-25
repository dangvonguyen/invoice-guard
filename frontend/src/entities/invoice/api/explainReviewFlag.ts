import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';
import { errorCode, translateApiError } from '@/shared/api/errors';

import { toExplanation } from '../model/mapper';
import type { Explanation } from '../model/types';

import type { RuleCodeDto } from './types';

export class NoActivePolicyDocumentError extends Error {
  constructor() {
    super('No policy document has been ingested yet');
    this.name = 'NoActivePolicyDocumentError';
  }
}

export class CannotExplainOwnInvoiceError extends Error {
  constructor() {
    super('You cannot request an explanation for your own submission');
    this.name = 'CannotExplainOwnInvoiceError';
  }
}

export async function explainReviewFlag(
  invoiceId: string,
  ruleCode: RuleCodeDto,
): Promise<Explanation> {
  const {
    data: envelope,
    error,
    response,
  } = await apiClient.POST('/invoices/{invoice_id}/flags/{rule_code}/explanation', {
    params: { path: { invoice_id: invoiceId, rule_code: ruleCode } },
  });

  if (error) {
    throw translateApiError(response, error, 'Failed to fetch explanation', {
      403: (forbiddenError) =>
        errorCode(forbiddenError) === 'CANNOT_EXPLAIN_OWN_INVOICE'
          ? new CannotExplainOwnInvoiceError()
          : new Error('Failed to fetch explanation'),
      404: (notFoundError) =>
        errorCode(notFoundError) === 'NO_ACTIVE_POLICY_DOCUMENT'
          ? new NoActivePolicyDocumentError()
          : new Error('Failed to fetch explanation'),
    });
  }

  const { data: dto } = unwrapEnvelope(envelope);
  return toExplanation(dto);
}
