import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';

import { toCurrentUser } from '../model/mapper';
import type { CurrentUser } from '../model/types';

export class UnauthenticatedError extends Error {
  constructor() {
    super('No authenticated user');
    this.name = 'UnauthenticatedError';
  }
}

export async function getCurrentUser(): Promise<CurrentUser> {
  const { data: envelope, error, response } = await apiClient.GET('/users/me');

  if (error) {
    if (response.status === 401) throw new UnauthenticatedError();
    throw new Error(`Failed to fetch current user: ${error.error?.message}`);
  }

  const { data: dto } = unwrapEnvelope(envelope);
  return toCurrentUser(dto);
}
