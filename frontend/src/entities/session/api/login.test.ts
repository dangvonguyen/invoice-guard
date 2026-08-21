import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it } from 'vitest';

import { API_BASE_URL } from '@/shared/config/env';
import { useAuthStore } from '@/shared/lib/authStore';

import { server } from '../../../../tests/mocks/server';

import { InvalidCredentialsError, login } from './login';

const LOGIN_URL = `${API_BASE_URL}/auth/login`;

describe('login', () => {
  afterEach(() => useAuthStore.getState().setAccessToken(null));

  it('should store the access token when credentials are valid', async () => {
    server.use(
      http.post(LOGIN_URL, () =>
        HttpResponse.json(
          { access_token: 'signed.jwt.token', token_type: 'bearer' },
          { status: 200 },
        ),
      ),
    );

    await login('user@example.com', 'secret123');

    expect(useAuthStore.getState().accessToken).toBe('signed.jwt.token');
  });

  it('should throw InvalidCredentialsError on 401 and clear the token', async () => {
    server.use(
      http.post(LOGIN_URL, () =>
        HttpResponse.json({ detail: 'Invalid email or password' }, { status: 401 }),
      ),
    );

    await expect(login('user@example.com', 'wrong')).rejects.toThrow(InvalidCredentialsError);
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it('should throw when the request never reaches a server', async () => {
    server.use(http.post(LOGIN_URL, () => HttpResponse.error()));

    await expect(login('user@example.com', 'secret123')).rejects.toThrow();
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it('should throw on 5xx server error', async () => {
    server.use(
      http.post(LOGIN_URL, () => HttpResponse.json({ detail: 'internal error' }, { status: 500 })),
    );

    await expect(login('user@example.com', 'secret123')).rejects.toThrow();
  });

  it('should apply only the most recently initiated attempt when an earlier attempt resolves later', async () => {
    // Simulates: user submits with a wrong password (attempt 1, slow), then
    // immediately retries with the correct password (attempt 2, fast) before
    // attempt 1's response arrives. Attempt 1's 401 must not overwrite
    // attempt 2's successful login when it finally resolves.
    let resolveFirstAttempt!: () => void;
    const firstAttemptGate = new Promise<void>((resolve) => {
      resolveFirstAttempt = resolve;
    });

    server.use(
      http.post(LOGIN_URL, async ({ request }) => {
        const body = (await request.json()) as { password?: string };
        if (body.password === 'wrong-password') {
          await firstAttemptGate; // held open until the test releases it
          return HttpResponse.json({ detail: 'Invalid' }, { status: 401 });
        }
        return HttpResponse.json(
          { access_token: 'correct.jwt.token', token_type: 'bearer' },
          { status: 200 },
        );
      }),
    );

    const firstAttempt = login('user@example.com', 'wrong-password');
    const secondAttempt = login('user@example.com', 'correct-password');

    await secondAttempt; // second attempt resolves first (nothing gates it)
    expect(useAuthStore.getState().accessToken).toBe('correct.jwt.token');

    resolveFirstAttempt(); // now let the stale first attempt finish
    await expect(firstAttempt).rejects.toThrow(InvalidCredentialsError);

    // The store must still reflect attempt 2, unaffected by attempt 1
    // resolving afterward.
    expect(useAuthStore.getState().accessToken).toBe('correct.jwt.token');
  });
});
