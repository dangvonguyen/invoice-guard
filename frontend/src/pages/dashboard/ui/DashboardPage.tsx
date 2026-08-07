import { useLoaderData } from 'react-router'

import { type HealthCheckData, SystemHealthCard } from '@/features/system-health'

export function DashboardPage() {
  const health = useLoaderData<HealthCheckData>()

  return (
    <main className="grid min-h-screen place-items-center bg-green-50 px-5 py-8">
      <SystemHealthCard health={health} />
    </main>
  )
}
