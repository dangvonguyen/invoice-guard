import type { ActionFunctionArgs } from 'react-router';

import { decideInvoice, DecisionConflictError, NotAwaitingReviewError } from '@/entities/invoice';
import { redirectOnSessionExpiry } from '@/entities/user';

export async function action({
  request,
  params,
}: ActionFunctionArgs): Promise<Error | null | Response> {
  if (params.id === undefined) {
    return new Error('Something went wrong. Please try again.');
  }

  const formData = await request.formData();
  const outcome = formData.get('outcome');
  const reason = formData.get('reason');

  if ((outcome !== 'approved' && outcome !== 'rejected') || typeof reason !== 'string' || !reason) {
    return new Error('Something went wrong. Please try again.');
  }

  try {
    await decideInvoice(params.id, outcome, reason);
    return null;
  } catch (error) {
    if (error instanceof DecisionConflictError || error instanceof NotAwaitingReviewError) {
      return error;
    }
    return redirectOnSessionExpiry(error) ?? new Error('Something went wrong. Please try again.');
  }
}
