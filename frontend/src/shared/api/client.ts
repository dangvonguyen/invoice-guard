import createClient from 'openapi-fetch'

import { API_BASE_URL } from '../config/env'

import type { paths } from './schema'

export const apiClient = createClient<paths>({
  baseUrl: API_BASE_URL,
})
