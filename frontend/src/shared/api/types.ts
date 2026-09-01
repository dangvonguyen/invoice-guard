import type { components } from './schema';

export type ApiMeta = PaginationMeta;

export interface PaginationMeta {
  page: number;
  perPage: number;
  total: number;
}

export interface ApiEnvelopeDto<T> {
  data?: T | null;
  meta?: ApiMetaDto | null;
  error?: ApiErrorDto | null;
}

export type ApiMetaDto = PaginationMetaDto;
export type ApiErrorDto = components['schemas']['ErrorInfo'];
export type ApiErrorDetail = components['schemas']['ErrorDetail'];
export type PaginationMetaDto = components['schemas']['PaginationMeta'];
