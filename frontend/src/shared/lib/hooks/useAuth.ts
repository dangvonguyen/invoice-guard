import { useAuthStore } from '../authStore'

export function useAuth() {
  const accessToken = useAuthStore((s) => s.accessToken)
  return { isAuthenticated: !!accessToken }
}
