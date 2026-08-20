import { act, renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'

import { API_BASE_URL } from '@/shared/config/env'
import { TokenStorage, tokenStorage } from '@/shared/lib/tokenStorage'

import { server } from '../../../../tests/mocks/server'
import { login } from '../api/login'

import { useSession } from './useSession'

const LOGIN_URL = `${API_BASE_URL}/auth/login`

describe('useSession', () => {
  afterEach(() => tokenStorage.clear())

  it('should report unauthenticated initially', () => {
    const store = new TokenStorage()

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
    const { result } = renderHook(() => useSession(tokenStorage))

    await act(async () => {
      await login('user@example.com', 'secret123')
    })

    await waitFor(() => expect(result.current.isAuthenticated).toBe(true))
  })

  it('should remain unauthenticated after failed login', async () => {
    server.use(
      http.post(LOGIN_URL, () => HttpResponse.json({ detail: 'Invalid' }, { status: 401 })),
    )
    const { result } = renderHook(() => useSession(tokenStorage))

    await act(async () => {
      await login('user@example.com', 'wrong')
    })

    expect(result.current.isAuthenticated).toBe(false)
  })
})
