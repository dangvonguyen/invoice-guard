import { apiClient } from '@/shared/api/client'

export type LoginResult =
  { kind: 'ok'; accessToken: string } | { kind: 'invalid_credentials' } | { kind: 'network_error' }

export async function login(email: string, password: string): Promise<LoginResult> {
  try {
    const { data, error, response } = await apiClient.POST('/auth/login', {
      body: { email, password },
    })

    if (error !== undefined || data === undefined) {
      // Only 401 is a defined failure response for this endpoint in the
      // current schema; anything else unexpected still resolves here as
      // invalid_credentials rather than throwing, since the whole point of
      // this result type is that callers never need a try/catch for the
      // HTTP-error path. Revisit if the schema grows more error variants
      // that a caller needs to distinguish (e.g. 422 vs 401).
      void response
      return { kind: 'invalid_credentials' }
    }
    return { kind: 'ok', accessToken: data.access_token }
  } catch {
    return { kind: 'network_error' }
  }
}
