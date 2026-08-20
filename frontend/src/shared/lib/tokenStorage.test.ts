import { describe, expect, it, vi } from 'vitest'

import { TokenStorage } from './tokenStorage'

describe('TokenStorage', () => {
  it('should report unauthenticated with no token initially', () => {
    const storage = new TokenStorage()

    expect(storage.isAuthenticated()).toBe(false)
    expect(storage.getAccessToken()).toBeNull()
  })

  it('should hold the token in memory after setToken', () => {
    const storage = new TokenStorage()

    storage.setAccessToken('signed.jwt.token')

    expect(storage.isAuthenticated()).toBe(true)
    expect(storage.getAccessToken()).toBe('signed.jwt.token')
  })

  it('should not write the token to local or session storage', () => {
    const setLocalItem = vi.spyOn(Storage.prototype, 'setItem')
    const storage = new TokenStorage()

    storage.setAccessToken('signed.jwt.token')

    expect(setLocalItem).not.toHaveBeenCalled()
    setLocalItem.mockRestore()
  })

  it('should clear the token', () => {
    const storage = new TokenStorage()
    storage.setAccessToken('signed.jwt.token')

    storage.clear()

    expect(storage.isAuthenticated()).toBe(false)
    expect(storage.getAccessToken()).toBeNull()
  })

  it('should notify subscribers on setToken and clear', () => {
    const storage = new TokenStorage()
    const listener = vi.fn()
    storage.subscribe(listener)

    storage.setAccessToken('signed.jwt.token')
    storage.clear()

    expect(listener).toHaveBeenCalledTimes(2)
  })

  it('should stop notifying a listener once unsubscribed', () => {
    const storage = new TokenStorage()
    const listener = vi.fn()
    const unsubscribe = storage.subscribe(listener)

    unsubscribe()
    storage.setAccessToken('signed.jwt.token')

    expect(listener).not.toHaveBeenCalled()
  })
})
