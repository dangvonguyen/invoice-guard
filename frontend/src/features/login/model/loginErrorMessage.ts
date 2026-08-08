import type { LoginErrorKind } from '@/entities/session'

const MESSAGES: Record<LoginErrorKind, string> = {
  invalid_credentials: 'Invalid email or password',
  network_error: 'Something went wrong. Please try again.',
}

export function loginErrorMessage(kind: LoginErrorKind): string {
  return MESSAGES[kind]
}
