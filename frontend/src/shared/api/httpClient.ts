export function apiFetch(path: string, init?: RequestInit) {
  const apiPath = path.startsWith('/') ? path : `/${path}`

  return fetch(`/api${apiPath}`, init)
}
