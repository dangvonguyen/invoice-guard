import { sessionStore, useSession } from '@/entities/session'
import { LoginForm } from '@/features/login'

export function LoginPage() {
  const { isAuthenticated } = useSession(sessionStore)

  if (isAuthenticated) {
    // Placeholder only — replaced once real Dashboard exists.
    return <p>Logged in</p>
  }

  return <LoginForm store={sessionStore} />
}
