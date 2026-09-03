import { z } from 'zod';

import type { SubmitClaimInput } from '@/entities/claim';

export const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024;
export const ACCEPTED_ATTACHMENT_TYPES = ['application/pdf'] as const;

export const CLAIM_CATEGORIES = [
  'software_hosting',
  'travel_transport',
  'travel_lodging',
  'meals_entertainment',
  'office_supplies',
  'other',
] as const;

const money = z
  .string()
  .trim()
  .regex(/^\d{1,11}(\.\d{1,2})?$/, 'Enter an amount with up to 2 decimal places.');

// A blank optional text field arrives as '' and is normalized to null
const optionalText = z
  .string()
  .trim()
  .transform((value) => (value === '' ? null : value));

const calendarDate = z
  .string()
  .trim()
  .regex(/^\d{4}-\d{2}-\d{2}$/, 'Invoice date is required.')
  .transform((value, ctx) => {
    const parsed = new Date(`${value}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) {
      ctx.addIssue({ code: 'custom', message: 'Invoice date is not a valid date.' });
      return z.NEVER;
    }
    return parsed;
  });

const attachment = z
  .instanceof(File, { message: 'Attach the vendor document.' })
  .refine((file) => file.size > 0, 'Attach the vendor document.')
  .refine((file) => file.size <= MAX_ATTACHMENT_BYTES, 'Attachment must be 10MB or smaller.')
  .refine(
    (file) => (ACCEPTED_ATTACHMENT_TYPES as readonly string[]).includes(file.type),
    'Attachment must be a PDF.',
  );

export const claimSubmissionSchema = z
  .object({
    expenseTitle: z.string().trim().min(1, 'Expense title is required.').max(120),
    businessPurpose: z.string().trim().min(1, 'Business purpose is required.').max(2000),
    category: z.enum(CLAIM_CATEGORIES, 'Choose an expense category.'),
    costCenter: optionalText,
    vendor: z.string().trim().min(1, 'Vendor is required.'),
    invoiceNumber: optionalText,
    invoiceDate: calendarDate,
    totalAmount: money.refine((value) => Number(value) > 0, 'Total amount must be greater than 0.'),
    currency: z
      .string()
      .trim()
      .regex(/^[A-Za-z]{3}$/, 'Currency must be a 3-letter code.')
      .transform((value) => value.toUpperCase()),
    taxAmount: z
      .string()
      .trim()
      .transform((value) => (value === '' ? null : value))
      .pipe(z.union([z.null(), money])),
    certified: z
      .literal('on', 'You must certify the claim before submitting.')
      .transform(() => true as const),
    file: attachment,
  })
  .transform((value) => ({ ...value, lineItems: [] }));

export function parseClaimSubmissionForm(formData: FormData): SubmitClaimInput {
  return claimSubmissionSchema.parse(Object.fromEntries(formData));
}
