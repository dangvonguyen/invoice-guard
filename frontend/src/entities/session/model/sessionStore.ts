import { login, type LoginResult } from '../api/sessionApi'

type Listener = () => void
export type LoginErrorKind = 'invalid_credentials' | 'network_error'

/**
 * In-memory-only session state. Deliberately not backed by localStorage or
 * sessionStorage.
 */
export class SessionStore {
  private accessToken: string | null = null
  private lastLoginError: LoginErrorKind | null = null
  private readonly listeners = new Set<Listener>()

  async loginWithCredentials(email: string, password: string): Promise<LoginResult> {
    const result = await login(email, password)

    if (result.kind === 'ok') {
      this.accessToken = result.accessToken
      this.lastLoginError = null
    } else {
      this.accessToken = null
      this.lastLoginError = result.kind
    }
    this.notify()
    return result
  }

  logout(): void {
    this.accessToken = null
    this.lastLoginError = null
    this.notify()
  }

  isAuthenticated(): boolean {
    return this.accessToken !== null
  }

  getAccessToken(): string | null {
    return this.accessToken
  }

  getLastLoginError(): LoginErrorKind | null {
    return this.lastLoginError
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private notify(): void {
    for (const listener of this.listeners) listener()
  }
}

/** Singleton used by the running application. */
export const sessionStore = new SessionStore()
