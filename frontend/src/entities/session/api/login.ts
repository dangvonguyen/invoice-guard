import { apiClient } from '@/shared/api/client';
import { useAuthStore } from '@/shared/lib/authStore';

export class InvalidCredentialsError extends Error {
  constructor() {
    super('Invalid email or password');
    this.name = 'InvalidCredentialsError';
  }
}

// Tracks which call is the most recently initiated login attempt, so a slow
// stale response (e.g. a mistyped password retried before its 401 arrives)
// can't overwrite the outcome of a newer attempt.
let latestAttempt = 0;

export async function login(email: string, password: string): Promise<void> {
  const attempt = ++latestAttempt;

  try {
    const accessToken = await requestLogin(email, password);
    if (attempt === latestAttempt) useAuthStore.getState().setAccessToken(accessToken);
  } catch (error) {
    if (attempt === latestAttempt) useAuthStore.getState().setAccessToken(null);
    throw error;
  }
}

async function requestLogin(email: string, password: string): Promise<string> {
  const { data, error, response } = await apiClient.POST('/auth/login', {
    body: { email, password },
  });

  if (error) {
    if (response.status === 401) throw new InvalidCredentialsError();
    throw new Error('Failed to log in');
  }
  return data.access_token;
}
