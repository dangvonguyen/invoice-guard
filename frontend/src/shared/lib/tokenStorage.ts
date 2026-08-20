type Listener = () => void

/**
 * In-memory-only access token store. Deliberately not backed by localStorage
 * or sessionStorage.
 */
export class TokenStorage {
  private accessToken: string | null = null
  private readonly listeners = new Set<Listener>()

  setAccessToken(token: string): void {
    this.accessToken = token
    this.notify()
  }

  getAccessToken(): string | null {
    return this.accessToken
  }

  clear(): void {
    this.accessToken = null
    this.notify()
  }

  isAuthenticated(): boolean {
    return this.accessToken !== null
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
export const tokenStorage = new TokenStorage()
