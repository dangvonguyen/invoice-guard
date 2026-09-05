import { apiClient } from '@/shared/api/client';
import { translateApiError } from '@/shared/api/errors';

export async function getClaimAttachmentBlob(claimId: string): Promise<Blob> {
  const { data, error, response } = await apiClient.GET('/claims/{claim_id}/attachment', {
    params: {
      path: { claim_id: claimId },
    },
    parseAs: 'blob',
  });

  if (error) {
    throw translateApiError(response, error, 'Failed to load the attachment');
  }

  return data;
}
