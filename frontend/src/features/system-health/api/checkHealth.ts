import { apiFetch } from '@/shared/api/httpClient'

import type { CheckState } from '../model/healthCheck'

export async function checkHealth(endpoint: string): Promise<CheckState> {
  try {
    const response = await apiFetch(endpoint, {
      headers: { 'Cache-Control': 'no-cache' },
    })
    return response.ok ? 'healthy' : 'unhealthy'
  } catch {
    return 'unhealthy'
  }
}
