function trimTrailingSlashes(value: string) {
  return value.replace(/\/+$/, '')
}

function normalizePath(value: string) {
  const path = value.replace(/^\/+|\/+$/g, '')
  return path ? `/${path}` : ''
}

export const env = {
  apiUrl: trimTrailingSlashes(import.meta.env.VITE_API_URL ?? 'http://localhost:8000'),
  apiRoot: normalizePath(import.meta.env.VITE_API_ROOT ?? '/api'),
} as const
