export type ClaimStatus =
  'submitted' | 'under_review' | 'returned_for_info' | 'approved' | 'rejected' | 'withdrawn';

export type ClaimCategory =
  | 'software_hosting'
  | 'travel_transport'
  | 'travel_lodging'
  | 'meals_entertainment'
  | 'office_supplies'
  | 'other';

export interface SubmittedClaim {
  id: string;
  status: ClaimStatus;
}

export interface ClaimSummary {
  id: string;
  status: ClaimStatus;
  expenseTitle: string;
  category: ClaimCategory;
  vendor: string;
  totalAmount: string;
  currency: string;
  createdAt: Date;
}

export interface ClaimAttachment {
  filename: string;
  contentType: string;
  url: string;
}

export interface Claim {
  id: string;
  status: ClaimStatus;
  expenseTitle: string;
  businessPurpose: string;
  category: ClaimCategory;
  costCenter: string | null;
  vendor: string;
  invoiceNumber: string | null;
  invoiceDate: string;
  totalAmount: string;
  currency: string;
  attachment: ClaimAttachment;
  createdAt: Date;
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
  certified: true;
  file: File;
}
