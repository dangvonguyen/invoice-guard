import type { LoaderFunctionArgs } from 'react-router';

import { getInvoice, NotFoundError } from '@/entities/invoice';
import { requireCurrentUser } from '@/entities/user';

export async function loader({ params }: LoaderFunctionArgs) {
  return requireCurrentUser(() => {
    if (params.id === undefined) {
      throw new NotFoundError();
    }
    return getInvoice(params.id);
  });
}
