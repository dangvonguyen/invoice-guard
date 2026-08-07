import { http, HttpResponse } from 'msw'

const BASE_URL = 'http://localhost:8000/api'

export const handlers = [
  http.post(`${BASE_URL}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { email?: string; password?: string }

    if (body.email === 'user@example.com' && body.password === 'secret123') {
      return HttpResponse.json(
        { access_token: 'signed.jwt.token', token_type: 'bearer' },
        { status: 200 },
      )
    }

    return HttpResponse.json({ detail: 'Invalid email or password' }, { status: 401 })
  }),
]
