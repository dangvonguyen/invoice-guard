import { useCallback, useEffect, useState } from 'react'

import { checkHealth } from '../api/checkHealth'
import { healthChecks, initialHealthCheckResults, type HealthCheckResults } from './healthCheck'

export function useSystemHealth() {
  const [results, setResults] = useState(initialHealthCheckResults)
  const [lastChecked, setLastChecked] = useState<Date | null>(null)

  const runChecks = useCallback(async () => {
    setResults(initialHealthCheckResults)

    const entries = await Promise.all(
      healthChecks.map(async ({ key, endpoint }) => [key, await checkHealth(endpoint)] as const),
    )

    setResults(Object.fromEntries(entries) as HealthCheckResults)
    setLastChecked(new Date())
  }, [])

  useEffect(() => {
    const timeout = window.setTimeout(() => void runChecks(), 0)
    return () => window.clearTimeout(timeout)
  }, [runChecks])

  return {
    results,
    lastChecked,
    isChecking: Object.values(results).some((state) => state === 'checking'),
    runChecks,
  }
}
