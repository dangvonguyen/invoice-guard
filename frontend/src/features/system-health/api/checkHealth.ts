import { apiClient } from '@/shared/api/client'
import { unwrap } from '@/shared/api/result'

import {
  type CheckState,
  type HealthCheckResults,
  healthChecks,
} from '../model/healthCheck'

type SystemHealthPath = '/health/live' | '/health/ready'

export async function checkHealth(path: SystemHealthPath): Promise<CheckState> {
  try {
    const result = await unwrap(apiClient.GET(path, { headers: { 'Cache-Control': 'no-cache' } }))
    return result.ok ? 'healthy' : 'unhealthy'
  } catch {
    return 'unhealthy'
  }
}

export interface HealthCheckData {
  results: HealthCheckResults
  lastChecked: string
}

export async function getSystemHealth(): Promise<HealthCheckData> {
  const entries = await Promise.all(
    healthChecks.map(async ({ key, endpoint }) => [key, await checkHealth(endpoint)] as const),
  )

  return {
    results: Object.fromEntries(entries) as HealthCheckResults,
    lastChecked: new Date().toISOString(),
  }
}
