import { apiClient } from '@/shared/api/client'
import { unwrap } from '@/shared/api/result'

import type { CheckState } from '../model/healthCheck'

type SystemHealthPath = '/health/live' | '/health/ready'

export async function checkHealth(path: SystemHealthPath): Promise<CheckState> {
  try {
    const result = await unwrap(apiClient.GET(path, { headers: { 'Cache-Control': 'no-cache' } }))
    return result.ok ? 'healthy' : 'unhealthy'
  } catch {
    return 'unhealthy'
  }
}
