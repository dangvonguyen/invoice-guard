import { type LoaderFunctionArgs, redirect } from 'react-router';

import { getInvoice, NotFoundError } from '@/entities/invoice';
import { paths } from '@/shared/config/paths';
import { useAuthStore } from '@/shared/lib/authStore';

export async function loader({ params }: LoaderFunctionArgs) {
  if (useAuthStore.getState().accessToken === null) {
    return redirect(paths.login);
  }
  if (params.id === undefined) {
    throw new NotFoundError();
  }
  return getInvoice(params.id);
}
