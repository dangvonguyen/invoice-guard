import type { ActionFunctionArgs } from 'react-router';

import {
  CannotExplainOwnInvoiceError,
  decideInvoice,
  DecisionConflictError,
  explainReviewFlag,
  type Explanation,
  NoActivePolicyDocumentError,
  NotAwaitingReviewError,
} from '@/entities/invoice';
import { redirectOnSessionExpiry } from '@/entities/user';

export async function action({
  request,
  params,
}: ActionFunctionArgs): Promise<Error | Explanation | null | Response> {
  if (params.id === undefined) {
    return new Error('Something went wrong. Please try again.');
  }

  const formData = await request.formData();

  switch (formData.get('intent')) {
    case 'explain':
      return explainAction(params.id, formData);
    case 'decide':
      return decideAction(params.id, formData);
    default:
      return new Error('Something went wrong. Please try again.');
  }
}

async function decideAction(
  invoiceId: string,
  formData: FormData,
): Promise<Error | null | Response> {
  const outcome = formData.get('outcome');
  const reason = formData.get('reason');

  if ((outcome !== 'approved' && outcome !== 'rejected') || typeof reason !== 'string' || !reason) {
    return new Error('Something went wrong. Please try again.');
  }

  try {
    await decideInvoice(invoiceId, outcome, reason);
    return null;
  } catch (error) {
    if (error instanceof DecisionConflictError || error instanceof NotAwaitingReviewError) {
      return error;
    }
    return redirectOnSessionExpiry(error) ?? new Error('Something went wrong. Please try again.');
  }
}

async function explainAction(
  invoiceId: string,
  formData: FormData,
): Promise<Error | Explanation | Response> {
  const ruleCode = formData.get('ruleCode');

  if (typeof ruleCode !== 'string' || !ruleCode) {
    return new Error('Something went wrong. Please try again.');
  }

  try {
    return await explainReviewFlag(invoiceId, ruleCode);
  } catch (error) {
    if (
      error instanceof NoActivePolicyDocumentError ||
      error instanceof CannotExplainOwnInvoiceError
    ) {
      return error;
    }
    return redirectOnSessionExpiry(error) ?? new Error('Failed to fetch explanation');
  }
}
