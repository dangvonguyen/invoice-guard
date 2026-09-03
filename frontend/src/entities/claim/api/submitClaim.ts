import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';
import { translateApiError } from '@/shared/api/errors';

import { toClaimSubmissionRequestDto, toSubmittedClaim } from '../model/mapper';
import type { SubmitClaimInput, SubmittedClaim } from '../model/types';

import type { ClaimSubmissionRequestDto } from './types';

interface ClaimMultipartBody {
  data: ClaimSubmissionRequestDto;
  file: File;
}

export async function submitClaim(input: SubmitClaimInput): Promise<SubmittedClaim> {
  const body: ClaimMultipartBody = {
    data: toClaimSubmissionRequestDto(input),
    file: input.file,
  };

  const {
    data: envelope,
    error,
    response,
  } = await apiClient.POST('/claims', {
    body: body as unknown as { data: string; file: string },
    bodySerializer: () => claimMultipartSerializer(body),
  });

  if (error) {
    throw translateApiError(response, error, 'Failed to submit claim');
  }

  const { data: dto } = unwrapEnvelope(envelope);
  return toSubmittedClaim(dto);
}

function claimMultipartSerializer({ data, file }: ClaimMultipartBody): FormData {
  const fd = new FormData();
  fd.append('data', JSON.stringify(data));
  fd.append('file', file);
  return fd;
}
