import { apiClient } from '@/shared/api/client'

export type LoginResult =
  { kind: 'ok'; accessToken: string } | { kind: 'invalid_credentials' } | { kind: 'network_error' }

export async function login(email: string, password: string): Promise<LoginResult> {
  try {
    const { data, error, response } = await apiClient.POST('/auth/login', {
      body: { email, password },
    })

    if (error !== undefined || data === undefined) {
      // Revisit if the schema grows more error variants that a caller needs
      // to distinguish (e.g. 422 vs 401).
      if (response.status === 401) {
        return { kind: 'invalid_credentials' }
      }
      return { kind: 'network_error' }
    }
    return { kind: 'ok', accessToken: data.access_token }
  } catch {
    return { kind: 'network_error' }
  }
}
