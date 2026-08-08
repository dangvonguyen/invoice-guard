import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { server } from '../../../tests/mocks/server'
import { API_BASE_URL } from '../config/env'

import { apiClient } from './client'

describe('apiClient', () => {
  it('should return data on success', async () => {
    server.use(
      http.post(`${API_BASE_URL}/auth/login`, () =>
        HttpResponse.json(
          { access_token: 'signed.jwt.token', token_type: 'bearer' },
          { status: 200 },
        ),
      ),
    )

    const { data, error, response } = await apiClient.POST('/auth/login', {
      body: { email: 'user@example.com', password: 'secret123' },
    })

    expect(error).toBeUndefined()
    expect(data).toEqual({
      access_token: 'signed.jwt.token',
      token_type: 'bearer',
    })
    expect(response.status).toBe(200)
  })

  it('should return error without throwing on http error status', async () => {
    server.use(
      http.post(`${API_BASE_URL}/auth/login`, () =>
        HttpResponse.json({ detail: 'Invalid email or password' }, { status: 401 }),
      ),
    )

    const { data, error, response } = await apiClient.POST('/auth/login', {
      body: { email: 'user@example.com', password: 'wrong' },
    })

    expect(data).toBeUndefined()
    expect(error).toEqual({ detail: 'Invalid email or password' })
    expect(response.status).toBe(401)
  })

  it('should reject when the request never reaches a server', async () => {
    server.use(http.post(`${API_BASE_URL}/auth/login`, () => HttpResponse.error()))

    await expect(
      apiClient.POST('/auth/login', {
        body: { email: 'user@example.com', password: 'secret123' },
      }),
    ).rejects.toBeTruthy()
  })
})
