import { env } from '@/shared/config/env'

export function apiFetch(path: string, init?: RequestInit) {
  return fetch(`${env.apiUrl}${env.apiRoot}${path}`, init)
}
