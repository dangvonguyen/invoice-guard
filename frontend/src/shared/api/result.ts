export type ApiResult<T> =
  { ok: true; data: T } | { ok: false; error: { status: number; message: string } }

export async function unwrap<T>(
  promise: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<ApiResult<T>> {
  const { data, error, response } = await promise
  if (error || !response.ok) {
    return {
      ok: false,
      error: { status: response.status, message: extractMessage(error) },
    }
  }
  return { ok: true, data: data as T }
}

function extractMessage(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return String(error.message)
  }
  return 'Unknown error'
}
