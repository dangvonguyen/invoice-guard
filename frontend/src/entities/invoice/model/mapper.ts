import type { InvoiceListItemDto } from '../api/types';

import type { Invoice } from './types';

export function toInvoice(dto: InvoiceListItemDto): Invoice {
  return {
    id: dto.id,
    status: dto.status,
    createdAt: new Date(dto.created_at),
  };
}
