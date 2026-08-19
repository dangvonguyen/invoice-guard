import type { Middleware } from 'openapi-fetch'

import { sessionStore } from '@/entities/session'
import { apiClient } from '@/shared/api/client'

const authMiddleware: Middleware = {
  onRequest({ request }) {
    const accessToken = sessionStore.getAccessToken()
    if (accessToken === null) return

    request.headers.set('Authorization', `Bearer ${accessToken}`)
    return request
  },
}

apiClient.use(authMiddleware)
