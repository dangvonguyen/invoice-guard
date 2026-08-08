import { Link } from 'react-router'

import { sessionStore, useSession } from '@/entities/session'
import { paths } from '@/shared/shared/paths'
import { Button } from '@/shared/ui/button'

export function DashboardPage() {
  const { isAuthenticated } = useSession(sessionStore)

  if (!isAuthenticated) {
    return (
      <main className="grid min-h-screen place-items-center bg-green-50 px-5 py-8">
        <div className="text-center">
          <h1 className="text-3xl font-semibold text-green-950">Invoice Guard</h1>
          <p className="mt-3 text-green-800">Log in to access your account.</p>
          <Button className="mt-6" render={<Link to={paths.login} />}>
            Log in
          </Button>
        </div>
      </main>
    )
  }

  return (
    <main className="grid min-h-screen place-items-center bg-green-50 px-5 py-8">
      <h1 className="text-3xl font-semibold text-green-950">Invoice Guard</h1>
    </main>
  )
}
