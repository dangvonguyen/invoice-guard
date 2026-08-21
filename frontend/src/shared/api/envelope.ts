import type { ApiEnvelopeDto, ApiErrorDetail, ApiMeta, ApiMetaDto } from './types';

export class ApiBusinessError extends Error {
  readonly code: string;
  readonly details?: ApiErrorDetail[] | null;

  constructor(code: string, message: string, details?: ApiErrorDetail[] | null) {
    super(message);
    this.name = 'ApiBusinessError';
    this.code = code;
    this.details = details;
  }
}

// Unwraps the envelope. Throws on envelope-level error even though
// the HTTP status was 2xx — this is distinct from fetch {error} field,
// which only fires on non-2xx.
export function unwrapEnvelope<T>(envelope: ApiEnvelopeDto<T>): { data: T; meta: ApiMeta | null } {
  if (envelope.error) {
    throw new ApiBusinessError(envelope.error.code, envelope.error.message, envelope.error.details);
  }
  if (envelope.data === null || envelope.data === undefined) {
    throw new Error('Malformed response: no error but data is null');
  }
  return { data: envelope.data, meta: toApiMeta(envelope.meta ?? null) };
}

function toApiMeta(dto: ApiMetaDto | null): ApiMeta | null {
  if (dto === null) {
    return null;
  }
  return {
    page: dto.limit > 0 ? Math.floor(dto.offset / dto.limit) + 1 : 1,
    perPage: dto.limit,
    total: dto.total,
  };
}
