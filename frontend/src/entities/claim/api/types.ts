import type { components } from '@/shared/api/schema';

export type ClaimStatusDto = components['schemas']['ClaimStatus'];
export type ClaimCreateResponseDto = components['schemas']['ClaimCreateResponse'];

export type ClaimCategoryDto =
  | 'software_hosting'
  | 'travel_transport'
  | 'travel_lodging'
  | 'meals_entertainment'
  | 'office_supplies'
  | 'other';

export interface ClaimCreateRequestDto {
  expense_title: string;
  business_purpose: string;
  category: ClaimCategoryDto;
  cost_center: string | null;
  vendor: string;
  invoice_number: string | null;
  invoice_date: string;
  total_amount: string;
  currency: string;
  certified: boolean;
}
