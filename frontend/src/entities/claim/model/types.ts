export type ClaimStatus =
  'submitted' | 'under_review' | 'returned_for_info' | 'approved' | 'rejected' | 'withdrawn';

export interface SubmittedClaim {
  id: string;
  status: ClaimStatus;
}

export type ClaimCategory =
  | 'software_hosting'
  | 'travel_transport'
  | 'travel_lodging'
  | 'meals_entertainment'
  | 'office_supplies'
  | 'other';

export interface ClaimLineItemInput {
  description: string;
  amount: string;
  quantity: string | null;
  unitPrice: string | null;
}

export interface SubmitClaimInput {
  expenseTitle: string;
  businessPurpose: string;
  category: ClaimCategory;
  costCenter: string | null;
  vendor: string;
  invoiceNumber: string | null;
  invoiceDate: Date;
  totalAmount: string;
  currency: string;
  taxAmount: string | null;
  lineItems: ClaimLineItemInput[];
  certified: true;
  file: File;
}
