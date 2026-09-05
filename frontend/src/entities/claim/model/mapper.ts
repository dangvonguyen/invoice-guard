import { toCalendarDate } from '@/shared/lib/date';

import type {
  ClaimAttachmentDto,
  ClaimCreateRequestDto,
  ClaimCreateResponseDto,
  ClaimResponseDto,
  ClaimSummaryDto,
} from '../api/types';

import type {
  Claim,
  ClaimAttachment,
  ClaimSummary,
  SubmitClaimInput,
  SubmittedClaim,
} from './types';

export function toSubmittedClaim(dto: ClaimCreateResponseDto): SubmittedClaim {
  return {
    id: dto.id,
    status: dto.status,
  };
}

export function toClaimSummary(dto: ClaimSummaryDto): ClaimSummary {
  return {
    id: dto.id,
    status: dto.status,
    expenseTitle: dto.expense_title,
    category: dto.category,
    vendor: dto.vendor,
    totalAmount: dto.total_amount,
    currency: dto.currency,
    createdAt: new Date(dto.created_at),
  };
}

export function toClaimAttachment(dto: ClaimAttachmentDto): ClaimAttachment {
  return {
    filename: dto.filename,
    contentType: dto.content_type,
    url: dto.url,
  };
}

export function toClaim(dto: ClaimResponseDto): Claim {
  return {
    id: dto.id,
    status: dto.status,
    expenseTitle: dto.expense_title,
    businessPurpose: dto.business_purpose,
    category: dto.category,
    costCenter: dto.cost_center,
    vendor: dto.vendor,
    invoiceNumber: dto.invoice_number,
    invoiceDate: dto.invoice_date,
    totalAmount: dto.total_amount,
    currency: dto.currency,
    attachment: toClaimAttachment(dto.attachment),
    createdAt: new Date(dto.created_at),
  };
}

export function toClaimCreateRequestDto(input: SubmitClaimInput): ClaimCreateRequestDto {
  return {
    expense_title: input.expenseTitle,
    business_purpose: input.businessPurpose,
    category: input.category,
    cost_center: input.costCenter,
    vendor: input.vendor,
    invoice_number: input.invoiceNumber,
    invoice_date: toCalendarDate(input.invoiceDate),
    total_amount: input.totalAmount,
    currency: input.currency,
    certified: input.certified,
  };
}
