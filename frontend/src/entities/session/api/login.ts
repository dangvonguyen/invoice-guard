import { apiClient } from '@/shared/api/client';
import { useAuthStore } from '@/shared/lib/authStore';

export type LoginErrorKind = 'invalid_credentials' | 'network_error';
export type LoginResult = { kind: 'ok' } | { kind: LoginErrorKind };

type RawLoginResult = { kind: 'ok'; accessToken: string } | { kind: LoginErrorKind };

// Tracks which call is the most recently initiated login attempt, so a slow
// stale response (e.g. a mistyped password retried before its 401 arrives)
// can't overwrite the outcome of a newer attempt.
let latestAttempt = 0;

export async function login(email: string, password: string): Promise<LoginResult> {
  const attempt = ++latestAttempt;
  const result = await requestLogin(email, password);

  if (result.kind === 'ok') {
    if (attempt === latestAttempt) useAuthStore.getState().setAccessToken(result.accessToken);
    return { kind: 'ok' };
  }

  if (attempt === latestAttempt) useAuthStore.getState().setAccessToken(null);
  return result;
}

async function requestLogin(email: string, password: string): Promise<RawLoginResult> {
  try {
    const { data, error, response } = await apiClient.POST('/auth/login', {
      body: { email, password },
    });

    if (error !== undefined || data === undefined) {
      // Revisit if the schema grows more error variants that a caller needs
      // to distinguish (e.g. 422 vs 401).
      if (response.status === 401) {
        return { kind: 'invalid_credentials' };
      }
      return { kind: 'network_error' };
    }
    return { kind: 'ok', accessToken: data.access_token };
  } catch {
    return { kind: 'network_error' };
  }
}
