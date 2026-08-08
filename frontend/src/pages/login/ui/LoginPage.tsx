import { Navigate } from 'react-router'

import { sessionStore, useSession } from '@/entities/session'
import { LoginForm } from '@/features/login'
import { paths } from '@/shared/shared/paths'

export function LoginPage() {
  const { isAuthenticated } = useSession(sessionStore)

  if (isAuthenticated) {
    return <Navigate to={paths.home} replace />
  }

  return <LoginForm store={sessionStore} />
}
