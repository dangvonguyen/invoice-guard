import type { LoaderFunctionArgs } from 'react-router';

import { getClaim, NotFoundError } from '@/entities/claim';
import { requireRole } from '@/entities/user';

export async function loader({ params }: LoaderFunctionArgs) {
  return requireRole('employee', () => {
    if (params.id === undefined) {
      throw new NotFoundError();
    }
    return getClaim(params.id);
  });
}
