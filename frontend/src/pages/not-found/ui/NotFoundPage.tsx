import { Link } from 'react-router'

import { paths } from '@/app/router/paths'
import { Button } from '@/shared/ui/button'

export function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-green-50 px-5 py-8">
      <div className="text-center">
        <p className="text-sm font-medium text-green-700">404</p>
        <h1 className="mt-2 text-3xl font-semibold text-green-950">Page not found</h1>
        <p className="mt-3 text-green-800">The page you requested does not exist.</p>
        <Button className="mt-6" render={<Link to={paths.home} />}>
          Return to dashboard
        </Button>
      </div>
    </main>
  )
}
