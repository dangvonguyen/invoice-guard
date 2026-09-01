interface RuntimeEnv {
  readonly DEV: boolean;
  readonly MODE: string;
  readonly PROD: boolean;
  readonly VITE_API_URL?: string;
}

const env = import.meta.env as RuntimeEnv;
const apiUrl = env.VITE_API_URL;

if (env.PROD && !apiUrl) {
  throw new Error('VITE_API_URL is required in production builds');
}

const apiBaseUrl = env.MODE === 'test' ? 'http://localhost:8000/api' : env.DEV ? '/api' : apiUrl;

export const API_BASE_URL = apiBaseUrl!.replace(/\/+$/, '');
