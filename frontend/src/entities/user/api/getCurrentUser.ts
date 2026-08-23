import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';
import { translateApiError, UnauthenticatedError } from '@/shared/api/errors';

import { toCurrentUser } from '../model/mapper';
import type { CurrentUser } from '../model/types';

export { UnauthenticatedError };

export async function getCurrentUser(): Promise<CurrentUser> {
  const { data: envelope, error, response } = await apiClient.GET('/users/me');

  if (error) {
    throw translateApiError(
      response,
      error,
      `Failed to fetch current user: ${error.error?.message}`,
    );
  }

  const { data: dto } = unwrapEnvelope(envelope);
  return toCurrentUser(dto);
}
