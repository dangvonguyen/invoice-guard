import type { LoaderFunctionArgs } from 'react-router';

import { getClaim, getClaimAttachmentUrl, NotFoundError } from '@/entities/claim';
import { requireRole } from '@/entities/user';

export async function loader({ params }: LoaderFunctionArgs) {
  return requireRole('employee', async () => {
    if (params.id === undefined) {
      throw new NotFoundError();
    }
    const claim = await getClaim(params.id);
    return { claim, attachmentUrl: getClaimAttachmentUrl(claim.id) };
  });
}
