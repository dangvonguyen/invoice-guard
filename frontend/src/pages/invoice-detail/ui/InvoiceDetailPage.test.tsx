import { createRoutesStub } from 'react-router';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { delay, http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { API_BASE_URL } from '@/shared/config/env';
import { paths } from '@/shared/config/paths';
import { useAuthStore } from '@/shared/lib/authStore';

import { server } from '../../../../tests/mocks/server';
import { loader } from '../api/loader';

import { ErrorBoundary, HydrateFallback, InvoiceDetailPage } from './InvoiceDetailPage';

const INVOICE_ID = 'inv-1';
const INVOICE_URL = `${API_BASE_URL}/invoices/${INVOICE_ID}`;

interface InvoiceSummary {
  vendor_name: string;
  invoice_date: string;
  total_amount: string;
  currency: string;
}

interface DecisionView {
  outcome: 'approved' | 'rejected';
  reason: string;
  decided_by: string;
  decided_at: string;
}

interface InvoiceDetailResponse {
  id: string;
  status: 'processing' | 'processing_error' | 'awaiting_review' | 'approved' | 'rejected';
  invoice_summary: InvoiceSummary | null;
  decision: DecisionView | null;
}

interface ReviewerInvoiceDetailResponse {
  id: string;
  status: 'processing_error' | 'awaiting_review' | 'approved' | 'rejected';
  employee: { id: string; name: string; email: string };
  extracted_fields: Record<string, unknown> | null;
  confidence: 'high' | 'low' | null;
  confidence_reason: string | null;
  review_flags: { code: string; summary: string | null; evidence: Record<string, unknown> }[];
  decision: DecisionView | null;
}

function detailEnvelope(data: InvoiceDetailResponse) {
  return { success: true, data, error: null, meta: null };
}

function reviewerDetailEnvelope(data: ReviewerInvoiceDetailResponse) {
  return { success: true, data, error: null, meta: null };
}

function renderPage() {
  const Stub = createRoutesStub([
    {
      path: '/invoices/:id',
      Component: InvoiceDetailPage,
      HydrateFallback,
      ErrorBoundary,
      loader,
    },
    { path: paths.login, Component: () => <p>Login</p> },
  ]);

  render(<Stub initialEntries={[`/invoices/${INVOICE_ID}`]} />);
}

describe('InvoiceDetailPage', () => {
  beforeEach(() => {
    useAuthStore.getState().setAccessToken('signed.jwt.token');
  });

  afterEach(() => useAuthStore.getState().setAccessToken(null));

  it('should show a loading state while the invoice is being fetched', async () => {
    server.use(
      http.get(INVOICE_URL, async () => {
        await delay(50);
        return HttpResponse.json(
          detailEnvelope({
            id: INVOICE_ID,
            status: 'processing',
            invoice_summary: null,
            decision: null,
          }),
        );
      }),
    );

    renderPage();

    expect(screen.getByRole('status')).toBeInTheDocument();
    await screen.findByText(/still processing/i);
  });

  it('should show a not found state for a 404', async () => {
    server.use(
      http.get(INVOICE_URL, () => HttpResponse.json({ detail: 'not found' }, { status: 404 })),
    );

    renderPage();

    expect(await screen.findByText(/invoice not found/i)).toBeInTheDocument();
  });

  it('should show a retry affordance when the invoice fails to load, and recover on retry', async () => {
    server.use(http.get(INVOICE_URL, () => HttpResponse.json({ detail: 'boom' }, { status: 500 })));

    renderPage();

    const retryButton = await screen.findByRole('button', { name: /retry/i });
    expect(screen.getByText(/couldn.?t load/i)).toBeInTheDocument();

    server.use(
      http.get(INVOICE_URL, () =>
        HttpResponse.json(
          detailEnvelope({
            id: INVOICE_ID,
            status: 'processing',
            invoice_summary: null,
            decision: null,
          }),
        ),
      ),
    );
    await userEvent.setup().click(retryButton);

    expect(await screen.findByText(/still processing/i)).toBeInTheDocument();
  });

  it('should show a processing message while extraction is in progress', async () => {
    server.use(
      http.get(INVOICE_URL, () =>
        HttpResponse.json(
          detailEnvelope({
            id: INVOICE_ID,
            status: 'processing',
            invoice_summary: null,
            decision: null,
          }),
        ),
      ),
    );

    renderPage();

    expect(await screen.findByText(/still processing your invoice/i)).toBeInTheDocument();
  });

  it('should show a processing error message when extraction failed', async () => {
    server.use(
      http.get(INVOICE_URL, () =>
        HttpResponse.json(
          detailEnvelope({
            id: INVOICE_ID,
            status: 'processing_error',
            invoice_summary: null,
            decision: null,
          }),
        ),
      ),
    );

    renderPage();

    expect(await screen.findByText(/couldn.?t process this invoice/i)).toBeInTheDocument();
  });

  it('should show the summary and an awaiting-review notice once queued for review', async () => {
    server.use(
      http.get(INVOICE_URL, () =>
        HttpResponse.json(
          detailEnvelope({
            id: INVOICE_ID,
            status: 'awaiting_review',
            invoice_summary: {
              vendor_name: 'Acme Supplies',
              invoice_date: '2026-08-01',
              total_amount: '500.00',
              currency: 'USD',
            },
            decision: null,
          }),
        ),
      ),
    );

    renderPage();

    expect(await screen.findByText('Acme Supplies')).toBeInTheDocument();
    expect(screen.getByText(/Awaiting review\./)).toBeInTheDocument();
  });

  it('should show the summary and decision once approved', async () => {
    server.use(
      http.get(INVOICE_URL, () =>
        HttpResponse.json(
          detailEnvelope({
            id: INVOICE_ID,
            status: 'approved',
            invoice_summary: {
              vendor_name: 'Acme Supplies',
              invoice_date: '2026-08-01',
              total_amount: '500.00',
              currency: 'USD',
            },
            decision: {
              outcome: 'approved',
              reason: 'Within policy',
              decided_by: 'Jane Reviewer',
              decided_at: '2026-08-02T10:00:00Z',
            },
          }),
        ),
      ),
    );

    renderPage();

    expect(await screen.findByText('Acme Supplies')).toBeInTheDocument();
    expect(screen.getByText(/decision/i)).toBeInTheDocument();
    // "Approved" appears in both the status badge and the decision badge.
    expect(screen.getAllByText('Approved')).toHaveLength(2);
    expect(screen.getByText(/within policy/i)).toBeInTheDocument();
    expect(screen.getByText(/decided by jane reviewer/i)).toBeInTheDocument();
  });

  it('should show the decision once rejected', async () => {
    server.use(
      http.get(INVOICE_URL, () =>
        HttpResponse.json(
          detailEnvelope({
            id: INVOICE_ID,
            status: 'rejected',
            invoice_summary: {
              vendor_name: 'Acme Supplies',
              invoice_date: '2026-08-01',
              total_amount: '500.00',
              currency: 'USD',
            },
            decision: {
              outcome: 'rejected',
              reason: 'Missing receipt',
              decided_by: 'Jane Reviewer',
              decided_at: '2026-08-02T10:00:00Z',
            },
          }),
        ),
      ),
    );

    renderPage();

    await screen.findByText(/decision/i);
    // "Rejected" appears in both the status badge and the decision badge.
    expect(screen.getAllByText('Rejected')).toHaveLength(2);
    expect(screen.getByText(/missing receipt/i)).toBeInTheDocument();
  });
});

describe('InvoiceDetailPage reviewer view', () => {
  beforeEach(() => {
    useAuthStore.getState().setAccessToken('signed.jwt.token');
  });

  afterEach(() => useAuthStore.getState().setAccessToken(null));

  it("should show the submitter, extracted fields, confidence, and review flags for a reviewer's invoice", async () => {
    server.use(
      http.get(INVOICE_URL, () =>
        HttpResponse.json(
          reviewerDetailEnvelope({
            id: INVOICE_ID,
            status: 'awaiting_review',
            employee: { id: 'emp-1', name: 'Priya Nair', email: 'priya@example.com' },
            extracted_fields: { vendor: 'Acme Cloud Services', total: '482.10' },
            confidence: 'low',
            confidence_reason: 'Total amount was not clearly legible',
            review_flags: [
              { code: 'duplicate_submission', summary: 'Possible duplicate', evidence: {} },
            ],
            decision: null,
          }),
        ),
      ),
    );

    renderPage();

    expect(await screen.findByText('Priya Nair')).toBeInTheDocument();
    expect(screen.getByText('priya@example.com')).toBeInTheDocument();
    expect(screen.getByText('Acme Cloud Services')).toBeInTheDocument();
    expect(screen.getByText(/low confidence/i)).toBeInTheDocument();
    expect(screen.getByText(/total amount was not clearly legible/i)).toBeInTheDocument();
    expect(screen.getByText(/possible duplicate/i)).toBeInTheDocument();
  });

  it('should show no extracted fields note when extraction produced nothing', async () => {
    server.use(
      http.get(INVOICE_URL, () =>
        HttpResponse.json(
          reviewerDetailEnvelope({
            id: INVOICE_ID,
            status: 'processing_error',
            employee: { id: 'emp-1', name: 'Priya Nair', email: 'priya@example.com' },
            extracted_fields: null,
            confidence: null,
            confidence_reason: null,
            review_flags: [],
            decision: null,
          }),
        ),
      ),
    );

    renderPage();

    expect(await screen.findByText('Priya Nair')).toBeInTheDocument();
    expect(screen.getByText(/no extracted fields available/i)).toBeInTheDocument();
  });

  it("should show the recorded decision for a reviewer's invoice", async () => {
    server.use(
      http.get(INVOICE_URL, () =>
        HttpResponse.json(
          reviewerDetailEnvelope({
            id: INVOICE_ID,
            status: 'approved',
            employee: { id: 'emp-1', name: 'Priya Nair', email: 'priya@example.com' },
            extracted_fields: { vendor: 'Acme Cloud Services' },
            confidence: 'high',
            confidence_reason: null,
            review_flags: [],
            decision: {
              outcome: 'approved',
              reason: 'Within policy',
              decided_by: 'Morgan Reyes',
              decided_at: '2026-08-19T10:00:00Z',
            },
          }),
        ),
      ),
    );

    renderPage();

    expect(await screen.findByText(/decision/i)).toBeInTheDocument();
    expect(screen.getByText(/within policy/i)).toBeInTheDocument();
    expect(screen.getByText(/decided by morgan reyes/i)).toBeInTheDocument();
  });
});

describe('InvoiceDetailPage access control', () => {
  it('should redirect unauthenticated users to login', async () => {
    const Stub = createRoutesStub([
      { path: paths.invoiceDetail, Component: InvoiceDetailPage, HydrateFallback, loader },
      { path: paths.login, Component: () => <p>Login</p> },
    ]);

    render(<Stub initialEntries={[`/invoices/${INVOICE_ID}`]} />);

    expect(await screen.findByText('Login')).toBeInTheDocument();
  });
});
