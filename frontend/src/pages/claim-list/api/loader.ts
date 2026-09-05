import type { LoaderFunctionArgs } from 'react-router';

import { listClaims } from '@/entities/claim';
import { requireRole } from '@/entities/user';

export const PAGE_SIZE = 20;

export async function loader({ request }: LoaderFunctionArgs) {
  const limit = Number(new URL(request.url).searchParams.get('limit')) || PAGE_SIZE;

  return requireRole('employee', async () => {
    const [needsAction, all] = await Promise.all([
      listClaims({ needsAction: true }),
      listClaims({ limit }),
    ]);

    return { needsAction: needsAction.claims, all };
  });
}
