import type { ClaimCategory } from './types';

const CATEGORY_LABELS: Record<ClaimCategory, string> = {
  software_hosting: 'Software & Hosting',
  travel_transport: 'Travel — Transport',
  travel_lodging: 'Travel — Lodging',
  meals_entertainment: 'Meals & Entertainment',
  office_supplies: 'Office Supplies',
  other: 'Other',
};

export function claimCategoryLabel(category: ClaimCategory): string {
  return CATEGORY_LABELS[category];
}
