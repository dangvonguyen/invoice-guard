import type { components } from '@/shared/api/schema';

export type ClaimStatusDto = components['schemas']['ClaimStatus'];
export type ClaimSubmissionResponseDto = components['schemas']['ClaimSubmissionResponse'];

export type ClaimCategoryDto =
  | 'software_hosting'
  | 'travel_transport'
  | 'travel_lodging'
  | 'meals_entertainment'
  | 'office_supplies'
  | 'other';

export interface ClaimLineItemDto {
  description: string;
  amount: string;
  quantity: string | null;
  unit_price: string | null;
}

export interface ClaimSubmissionRequestDto {
  expense_title: string;
  business_purpose: string;
  category: ClaimCategoryDto;
  cost_center: string | null;
  vendor: string;
  invoice_number: string | null;
  invoice_date: string;
  total_amount: string;
  currency: string;
  tax_amount: string | null;
  line_items: ClaimLineItemDto[];
  certified: boolean;
}
