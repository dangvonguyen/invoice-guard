export type CheckState = 'checking' | 'healthy' | 'unhealthy'

export const healthChecks = [
  {
    key: 'live',
    name: 'API service',
    description: 'The application server is responding.',
    endpoint: '/health/live',
  },
  {
    key: 'ready',
    name: 'Database',
    description: 'The database connection is ready.',
    endpoint: '/health/ready',
  },
] as const

export type HealthCheckKey = (typeof healthChecks)[number]['key']
export type HealthCheckResults = Record<HealthCheckKey, CheckState>

export const initialHealthCheckResults: HealthCheckResults = {
  live: 'checking',
  ready: 'checking',
}
