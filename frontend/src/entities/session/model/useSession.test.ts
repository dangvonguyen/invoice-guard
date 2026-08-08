import { act, renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { API_BASE_URL } from '@/shared/config/env'

import { server } from '../../../../tests/mocks/server'

import { SessionStore } from './sessionStore'
import { useSession } from './useSession'

const LOGIN_URL = `${API_BASE_URL}/auth/login`

describe('useSession', () => {
  it('should report unauthenticated initially', () => {
    const store = new SessionStore()

    const { result } = renderHook(() => useSession(store))

    expect(result.current.isAuthenticated).toBe(false)
  })

  it('should rerender as authenticated after successful login', async () => {
    server.use(
      http.post(LOGIN_URL, () =>
        HttpResponse.json(
          { access_token: 'signed.jwt.token', token_type: 'bearer' },
          { status: 200 },
        ),
      ),
    )
    const store = new SessionStore()
    const { result } = renderHook(() => useSession(store))

    await act(async () => {
      await store.loginWithCredentials('user@example.com', 'secret123')
    })

    await waitFor(() => expect(result.current.isAuthenticated).toBe(true))
  })

  it('should rerender with login error after failed login', async () => {
    server.use(
      http.post(LOGIN_URL, () => HttpResponse.json({ detail: 'Invalid' }, { status: 401 })),
    )
    const store = new SessionStore()
    const { result } = renderHook(() => useSession(store))

    await act(async () => {
      await store.loginWithCredentials('user@example.com', 'wrong')
    })

    await waitFor(() => expect(result.current.lastLoginError).toBe('invalid_credentials'))
    expect(result.current.isAuthenticated).toBe(false)
  })
})
