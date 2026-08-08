import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { API_BASE_URL } from '@/shared/config/env'

import { server } from '../../../../tests/mocks/server'

import { login } from './sessionApi'

const LOGIN_URL = `${API_BASE_URL}/auth/login`

describe('login', () => {
  it('should return ok result with access token when credentials are valid', async () => {
    server.use(
      http.post(LOGIN_URL, () =>
        HttpResponse.json(
          { access_token: 'signed.jwt.token', token_type: 'bearer' },
          { status: 200 },
        ),
      ),
    )

    const result = await login('user@example.com', 'secret123')

    expect(result).toEqual({ kind: 'ok', accessToken: 'signed.jwt.token' })
  })

  it('should return invalid credentials result on 401', async () => {
    server.use(
      http.post(LOGIN_URL, () =>
        HttpResponse.json({ detail: 'Invalid email or password' }, { status: 401 }),
      ),
    )

    const result = await login('user@example.com', 'wrong')

    expect(result).toEqual({ kind: 'invalid_credentials' })
  })

  it('should return network error result when request never reaches a server', async () => {
    server.use(http.post(LOGIN_URL, () => HttpResponse.error()))

    const result = await login('user@example.com', 'secret123')

    expect(result).toEqual({ kind: 'network_error' })
  })

  it('should return network error result on 5xx server error', async () => {
    server.use(
      http.post(LOGIN_URL, () => HttpResponse.json({ detail: 'internal error' }, { status: 500 })),
    )

    const result = await login('user@example.com', 'secret123')

    expect(result).toEqual({ kind: 'network_error' })
  })
})
