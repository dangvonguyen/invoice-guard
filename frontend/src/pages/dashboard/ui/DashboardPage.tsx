import { Link } from 'react-router'

import { paths } from '@/shared/config/paths'
import { useAuth } from '@/shared/lib/hooks/useAuth'
import { buttonVariants } from '@/shared/ui/button'

export function DashboardPage() {
  const { isAuthenticated } = useAuth()

  if (!isAuthenticated) {
    return (
      <div className="grid h-full place-items-center px-5 py-10">
        <Link to={paths.login} className={buttonVariants({ size: 'lg' })}>
          Log in
        </Link>
      </div>
    )
  }

  return (
    <div className="grid h-full place-items-center px-5 py-10">
      <span className="text-2xl font-semibold">Logged in</span>
    </div>
  )
}
