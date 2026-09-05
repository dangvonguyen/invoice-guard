import { useFetcher } from 'react-router';

import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Field, FieldError, FieldGroup, FieldLabel } from '@/shared/ui/field';
import { Input } from '@/shared/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select';
import { Textarea } from '@/shared/ui/textarea';

import { ACCEPTED_ATTACHMENT_TYPES, type CLAIM_CATEGORIES } from '../model/schema';

interface CategoryItem {
  label: string;
  value: (typeof CLAIM_CATEGORIES)[number];
}

const category_items: CategoryItem[] = [
  { label: 'Software & hosting', value: 'software_hosting' },
  { label: 'Travel — transport', value: 'travel_transport' },
  { label: 'Travel — lodging', value: 'travel_lodging' },
  { label: 'Meals & entertainment', value: 'meals_entertainment' },
  { label: 'Office supplies', value: 'office_supplies' },
  { label: 'Other', value: 'other' },
];

const CURRENCY_OPTIONS = ['EUR', 'USD', 'GBP', 'VND'] as const;

export function SubmitClaimForm() {
  const fetcher = useFetcher<Error>();
  const isSubmitting = fetcher.state !== 'idle';
  const todayIso = new Date().toISOString().slice(0, 10);

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle className="text-lg font-semibold">New reimbursement request</CardTitle>
      </CardHeader>
      <CardContent>
        <fetcher.Form method="post" encType="multipart/form-data">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="claim-file">
                Attach receipt / invoice<span className="text-destructive">*</span>
              </FieldLabel>
              <Input
                id="claim-file"
                name="file"
                type="file"
                className="bg-muted"
                accept={ACCEPTED_ATTACHMENT_TYPES.join(',')}
                required
              />
            </Field>

            <Field>
              <FieldLabel htmlFor="claim-expense-title">
                What was this expense for?<span className="text-destructive">*</span>
              </FieldLabel>
              <Input
                id="claim-expense-title"
                name="expenseTitle"
                maxLength={120}
                placeholder="e.g. Cloud hosting for client demo"
                required
              />
            </Field>

            <div className="grid gap-4 @md/field-group:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="claim-vendor">
                  Vendor<span className="text-destructive">*</span>
                </FieldLabel>
                <Input id="claim-vendor" name="vendor" required />
              </Field>

              <Field>
                <FieldLabel htmlFor="claim-invoice-number">Invoice / receipt number</FieldLabel>
                <Input id="claim-invoice-number" name="invoiceNumber" />
              </Field>
            </div>

            <div className="grid gap-4 @md/field-group:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="claim-invoice-date">
                  Invoice date<span className="text-destructive">*</span>
                </FieldLabel>
                <Input
                  id="claim-invoice-date"
                  name="invoiceDate"
                  type="date"
                  defaultValue={todayIso}
                  required
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="claim-category">
                  Category<span className="text-destructive">*</span>
                </FieldLabel>
                <Select name="category" items={category_items} required>
                  <SelectTrigger id="claim-category" className="w-full">
                    <SelectValue placeholder="Select a category" />
                  </SelectTrigger>
                  <SelectContent>
                    {category_items.map((item) => (
                      <SelectItem key={item.value} value={item.value}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            </div>

            <div className="grid gap-4 @md/field-group:grid-cols-3">
              <Field>
                <FieldLabel htmlFor="claim-total-amount">
                  Amount<span className="text-destructive">*</span>
                </FieldLabel>
                <Input
                  id="claim-total-amount"
                  name="totalAmount"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  required
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="claim-currency">
                  Currency<span className="text-destructive">*</span>
                </FieldLabel>
                <Select name="currency" defaultValue="EUR">
                  <SelectTrigger id="claim-currency" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCY_OPTIONS.map((code) => (
                      <SelectItem key={code} value={code}>
                        {code}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>

              <Field>
                <FieldLabel htmlFor="claim-cost-center">Cost center</FieldLabel>
                <Input id="claim-cost-center" name="costCenter" placeholder="e.g. ENG-200" />
              </Field>
            </div>

            <Field>
              <FieldLabel htmlFor="claim-business-purpose">
                Business purpose<span className="text-destructive">*</span>
              </FieldLabel>
              <Textarea
                id="claim-business-purpose"
                name="businessPurpose"
                maxLength={2000}
                placeholder="Why was this necessary for the business?"
                required
              />
            </Field>

            <Field orientation="horizontal">
              <input
                id="claim-certified"
                name="certified"
                type="checkbox"
                className="size-4 rounded border-input"
              />
              <FieldLabel htmlFor="claim-certified" className="text-[13px] font-normal">
                I certify these expenses were incurred for business purposes, are accurate.
              </FieldLabel>
            </Field>

            <FieldError>{fetcher.data?.message ?? null}</FieldError>

            <div className="flex justify-end">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Submitting…' : 'Submit for review'}
              </Button>
            </div>
          </FieldGroup>
        </fetcher.Form>
      </CardContent>
    </Card>
  );
}
