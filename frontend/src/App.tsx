import { useCallback, useEffect, useState } from 'react'

const apiUrl = ((import.meta.env.VITE_API_URL as string) ?? '').replace(/\/+$/, '')
const configuredApiRoot = ((import.meta.env.VITE_API_ROOT as string) ?? '/api').replace(
  /^\/+|\/+$/g,
  '',
)
const apiRoot = configuredApiRoot ? `/${configuredApiRoot}` : ''

type CheckState = 'checking' | 'healthy' | 'unhealthy'

const checks = [
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

const initialResults: Record<(typeof checks)[number]['key'], CheckState> = {
  live: 'checking',
  ready: 'checking',
}

const statusIconClasses: Record<CheckState, string> = {
  checking: 'animate-spin border-2 border-gray-300 border-t-green-600',
  healthy: 'bg-green-600',
  unhealthy: 'bg-red-600',
}

const statusTextClasses: Record<CheckState, string> = {
  checking: 'text-gray-500',
  healthy: 'text-green-700',
  unhealthy: 'text-red-700',
}

export function App() {
  const [results, setResults] = useState(initialResults)
  const [lastChecked, setLastChecked] = useState<Date | null>(null)

  const runChecks = useCallback(async () => {
    setResults({ live: 'checking', ready: 'checking' })

    const entries = await Promise.all(
      checks.map(async ({ key, endpoint }) => {
        try {
          const response = await fetch(`${apiUrl}${apiRoot}${endpoint}`, { cache: 'no-store' })
          return [key, response.ok ? 'healthy' : 'unhealthy']
        } catch {
          return [key, 'unhealthy']
        }
      }),
    )

    setResults(Object.fromEntries(entries) as typeof initialResults)
    setLastChecked(new Date())
  }, [])

  useEffect(() => {
    const timeout = window.setTimeout(() => void runChecks(), 0)
    return () => window.clearTimeout(timeout)
  }, [runChecks])

  const isChecking = Object.values(results).some((state) => state === 'checking')

  return (
    <main className="grid min-h-screen place-items-center bg-green-50 px-5 py-8">
      <section
        className="w-full max-w-2xl overflow-hidden rounded-xl border border-gray-100 bg-white shadow-xl"
        aria-live="polite"
      >
        <header className="px-5 pt-7 pb-5 sm:px-8">
          <div>
            <p className="text-xs font-bold tracking-widest text-gray-500 uppercase">
              Invoice Guard
            </p>
            <h1 className="text-2xl font-bold">System health</h1>
          </div>
        </header>

        <div className="divide-y divide-gray-200 border-y border-gray-200">
          {checks.map(({ key, name, description }) => {
            const result = results[key]
            return (
              <div className="flex min-h-22 items-center gap-3.5 p-5 sm:px-8" key={key}>
                <span
                  className={`grid size-7 shrink-0 place-items-center rounded-full font-extrabold text-white ${statusIconClasses[result]}`}
                >
                  {result === 'healthy' ? '✓' : result === 'unhealthy' ? '!' : ''}
                </span>
                <div className="min-w-0 flex-1">
                  <strong className="text-sm">{name}</strong>
                  <p className="mt-1 text-[13px] text-gray-500 sm:block">{description}</p>
                </div>
                <div className="min-w-20 text-right">
                  <span className={`block text-sm font-bold ${statusTextClasses[result]}`}>
                    {result === 'checking'
                      ? 'Checking'
                      : result === 'healthy'
                        ? 'Operational'
                        : 'Unavailable'}
                  </span>
                </div>
              </div>
            )
          })}
        </div>

        <footer className="flex flex-col items-start justify-between gap-4 px-5 py-5 sm:flex-row sm:items-center sm:px-8">
          <p className="text-xs text-gray-400">
            {lastChecked
              ? `Last checked at ${lastChecked.toLocaleTimeString()}`
              : 'Preparing health check...'}
          </p>
          <button
            className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 hover:border-gray-500 hover:bg-gray-50 disabled:cursor-wait disabled:opacity-55"
            type="button"
            onClick={() => void runChecks()}
            disabled={isChecking}
          >
            <span aria-hidden="true">↻</span> Check again
          </button>
        </footer>
      </section>
    </main>
  )
}
