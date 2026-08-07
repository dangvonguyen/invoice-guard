import { SystemHealthCard } from '@/features/system-health'

export function DashboardPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-green-50 px-5 py-8">
      <SystemHealthCard />
    </main>
  )
}
