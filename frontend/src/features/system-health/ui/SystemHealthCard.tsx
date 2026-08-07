import { useFetcher } from 'react-router'

import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/shared/ui/card'

import type { HealthCheckData } from '../api/checkHealth'
import { type CheckState, healthChecks, initialHealthCheckResults } from '../model/healthCheck'

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

const statusLabels: Record<CheckState, string> = {
  checking: 'Checking',
  healthy: 'Operational',
  unhealthy: 'Unavailable',
}

interface SystemHealthCardProps {
  health: HealthCheckData
}

export function SystemHealthCard({ health }: SystemHealthCardProps) {
  const fetcher = useFetcher<HealthCheckData>()
  const isChecking = fetcher.state !== 'idle'
  const currentHealth = fetcher.data ?? health
  const results = isChecking ? initialHealthCheckResults : currentHealth.results

  return (
    <Card className="w-full max-w-2xl gap-0 shadow-xl">
      <CardHeader className="px-5 pt-7 pb-5 sm:px-8">
        <div>
          <p className="text-xs font-bold tracking-widest text-gray-500 uppercase">Invoice Guard</p>
          <CardTitle className="text-2xl font-bold">System health</CardTitle>
        </div>
      </CardHeader>

      <CardContent className="divide-y divide-gray-200 border-y border-gray-200 px-0">
        {healthChecks.map(({ key, name, description }) => {
          const result = results[key]
          return (
            <div className="flex min-h-22 items-center gap-3.5 p-5 sm:px-8" key={key}>
              <Badge
                className={`grid size-7 shrink-0 place-items-center rounded-full p-0 font-extrabold text-white ${statusIconClasses[result]}`}
              >
                {result === 'healthy' ? '✓' : result === 'unhealthy' ? '!' : ''}
              </Badge>
              <div className="min-w-0 flex-1">
                <strong className="text-sm">{name}</strong>
                <p className="mt-1 text-[13px] text-gray-500 sm:block">{description}</p>
              </div>
              <div className="min-w-20 text-right">
                <span className={`block text-sm font-bold ${statusTextClasses[result]}`}>
                  {statusLabels[result]}
                </span>
              </div>
            </div>
          )
        })}
      </CardContent>

      <CardFooter className="flex flex-col items-start justify-between gap-4 border-t-0 bg-transparent px-5 py-5 sm:flex-row sm:items-center sm:px-8">
        <p className="text-xs text-gray-400">
          {isChecking
            ? 'Checking system health...'
            : `Last checked at ${new Date(currentHealth.lastChecked).toLocaleTimeString()}`}
        </p>
        <fetcher.Form method="post">
          <Button
            className="h-auto cursor-pointer border-gray-300 px-3 py-2 hover:border-gray-500 hover:bg-gray-50 disabled:cursor-wait"
            variant="outline"
            type="submit"
            disabled={isChecking}
          >
            <span aria-hidden="true">↻</span> Check again
          </Button>
        </fetcher.Form>
      </CardFooter>
    </Card>
  )
}
