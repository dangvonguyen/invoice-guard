import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { API_BASE_URL } from '@/shared/config/env'

import { server } from '../../../../tests/mocks/server'

import { SessionStore } from './sessionStore'

const LOGIN_URL = `${API_BASE_URL}/auth/login`

describe('SessionStore', () => {
  it('should hold token in memory after successful login', async () => {
    server.use(
      http.post(LOGIN_URL, () =>
        HttpResponse.json(
          { access_token: 'signed.jwt.token', token_type: 'bearer' },
          { status: 200 },
        ),
      ),
    )
    const store = new SessionStore()

    const result = await store.loginWithCredentials('user@example.com', 'secret123')

    expect(result.kind).toBe('ok')
    expect(store.isAuthenticated()).toBe(true)
    expect(store.getAccessToken()).toBe('signed.jwt.token')
    expect(store.getLastLoginError()).toBeNull()
  })

  it('should not write access token to local or session storage', async () => {
    const setLocalItem = vi.spyOn(Storage.prototype, 'setItem')
    server.use(
      http.post(LOGIN_URL, () =>
        HttpResponse.json(
          { access_token: 'signed.jwt.token', token_type: 'bearer' },
          { status: 200 },
        ),
      ),
    )
    const store = new SessionStore()

    await store.loginWithCredentials('user@example.com', 'secret123')

    expect(setLocalItem).not.toHaveBeenCalled()
    setLocalItem.mockRestore()
  })

  it('should remain unauthenticated and expose invalid credentials error on 401', async () => {
    server.use(
      http.post(LOGIN_URL, () => HttpResponse.json({ detail: 'Invalid' }, { status: 401 })),
    )
    const store = new SessionStore()

    const result = await store.loginWithCredentials('user@example.com', 'wrong')

    expect(result.kind).toBe('invalid_credentials')
    expect(store.isAuthenticated()).toBe(false)
    expect(store.getLastLoginError()).toBe('invalid_credentials')
  })

  it('should remain unauthenticated and expose network error when unreachable', async () => {
    server.use(http.post(LOGIN_URL, () => HttpResponse.error()))
    const store = new SessionStore()

    const result = await store.loginWithCredentials('user@example.com', 'secret123')

    expect(result.kind).toBe('network_error')
    expect(store.isAuthenticated()).toBe(false)
    expect(store.getLastLoginError()).toBe('network_error')
  })

  it('should notify subscribers on login and logout', async () => {
    server.use(
      http.post(LOGIN_URL, () =>
        HttpResponse.json(
          { access_token: 'signed.jwt.token', token_type: 'bearer' },
          { status: 200 },
        ),
      ),
    )
    const store = new SessionStore()
    const listener = vi.fn()
    store.subscribe(listener)

    await store.loginWithCredentials('user@example.com', 'secret123')
    store.logout()

    expect(listener).toHaveBeenCalledTimes(2)
  })
})
