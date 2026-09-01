import type { components } from '@/shared/api/schema';

export type InvoiceListItemDto = components['schemas']['InvoiceListItem'];
export type InvoiceDetailDto = components['schemas']['InvoiceDetailResponse'];
export type InvoiceSummaryDto = components['schemas']['InvoiceSummary'];
export type DecisionDto = components['schemas']['DecisionView'];
export type InvoiceUploadResponseDto = components['schemas']['InvoiceUploadResponse'];
export type ReviewQueueItemDto = components['schemas']['ReviewQueueItem'];
export type EmployeeIdentityDto = components['schemas']['EmployeeIdentity'];
export type ReviewFlagDto = components['schemas']['ReviewFlagView'];
export type ReviewerInvoiceDetailDto = components['schemas']['ReviewerInvoiceDetailResponse'];
export type CitationDto = components['schemas']['CitationView'];
export type ExplanationDto = components['schemas']['ExplanationView'];
export type RuleCodeDto = components['schemas']['RuleCode'];

const RULE_CODES: Record<RuleCodeDto, true> = {
  expense_within_amount_limit: true,
  expense_within_submission_window: true,
  invoice_date_not_in_future: true,
  line_item_total_consistency: true,
  currency_allowed: true,
};

export function isRuleCode(value: string): value is RuleCodeDto {
  return value in RULE_CODES;
}
