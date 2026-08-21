import createClient from 'openapi-fetch';

import { API_BASE_URL } from '../config/env';
import { useAuthStore } from '../lib/authStore';

import type { paths } from './schema';

// openapi-fetch resolves `fetch: globalThis.fetch` once, at createClient()
// call time. Since MSW's setupServer() patches globalThis.fetch inside
// beforeAll (after this module has already been imported), a direct
// createClient() call here would capture the real, unpatched fetch and
// silently bypass every mock. Passing a lambda forces fetch to be resolved
// per-call instead, after MSW's patch is in place.
export const apiClient = createClient<paths>({
  baseUrl: API_BASE_URL,
  fetch: (...args) => globalThis.fetch(...args),
});

apiClient.use({
  onRequest({ request }) {
    const accessToken = useAuthStore.getState().accessToken;
    if (accessToken === null) return;

    request.headers.set('Authorization', `Bearer ${accessToken}`);
    return request;
  },
});
