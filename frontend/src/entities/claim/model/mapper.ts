import { toCalendarDate } from '@/shared/lib/date';

import type { ClaimSubmissionRequestDto, ClaimSubmissionResponseDto } from '../api/types';

import type { SubmitClaimInput, SubmittedClaim } from './types';

export function toSubmittedClaim(dto: ClaimSubmissionResponseDto): SubmittedClaim {
  return {
    id: dto.id,
    status: dto.status,
  };
}

export function toClaimSubmissionRequestDto(input: SubmitClaimInput): ClaimSubmissionRequestDto {
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
