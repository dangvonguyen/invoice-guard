export class UnauthenticatedError extends Error {
  constructor() {
    super('No authenticated user');
    this.name = 'UnauthenticatedError';
  }
}

// The single seam every invoice/user API call funnels transport failures
// through, so a status code is translated into a typed domain error exactly
// once rather than re-checked ad hoc in each call site. `statusOverrides`
// lets a call site translate its own status codes (e.g. 404, 409) before
// falling back to the shared default (401 -> session expiry) and finally
// `fallbackMessage`.
export function translateApiError(
  response: Response,
  error: unknown,
  fallbackMessage: string,
  statusOverrides?: Record<number, (error: unknown) => Error>,
): Error {
  const override = statusOverrides?.[response.status];
  if (override) return override(error);
  if (response.status === 401) return new UnauthenticatedError();
  return new Error(fallbackMessage);
}
