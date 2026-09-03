import { type ActionFunctionArgs, redirect } from 'react-router';
import { z } from 'zod';

import { submitClaim } from '@/entities/claim';
import { redirectOnSessionExpiry } from '@/entities/user';
import { parseSubmitClaimForm } from '@/features/submit-claim';
import { paths } from '@/shared/config/paths';

export async function action({ request }: ActionFunctionArgs): Promise<Error | Response> {
  const formData = await request.formData();

  try {
    await submitClaim(parseSubmitClaimForm(formData));
  } catch (error) {
    if (error instanceof z.ZodError) {
      return new Error(error.issues[0]?.message ?? 'Please correct the form and try again.');
    }
    return redirectOnSessionExpiry(error) ?? new Error('Something went wrong. Please try again.');
  }

  return redirect(paths.home);
}
