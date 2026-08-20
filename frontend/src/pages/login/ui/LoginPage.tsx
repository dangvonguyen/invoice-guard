import { Navigate } from 'react-router'

import { sessionStore, useSession } from '@/entities/session'
import { LoginForm } from '@/features/login'
import { paths } from '@/shared/config/paths'

export function LoginPage() {
  const { isAuthenticated } = useSession(sessionStore)

  if (isAuthenticated) {
    return <Navigate to={paths.invoices} replace />
  }

  return (
    <div className="grid h-full place-items-center p-5">
      <LoginForm store={sessionStore} />
    </div>
  )
}
