export const API_BASE_URL = import.meta.env.DEV ? '/api' : String(import.meta.env.VITE_API_URL)

if (!import.meta.env.DEV && !import.meta.env.VITE_API_URL) {
  throw new Error('VITE_API_URL is required in production builds')
}
