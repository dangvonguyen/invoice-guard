import { createRoutesStub } from 'react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { delay, http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { API_BASE_URL } from '@/shared/config/env';
import { paths } from '@/shared/config/paths';
import { useAuthStore } from '@/shared/lib/authStore';

import { server } from '../../../../tests/mocks/server';
import { action } from '../api/action';
import { loader } from '../api/loader';

import { ErrorBoundary, HydrateFallback, InvoiceDetailPage } from './InvoiceDetailPage';

const INVOICE_ID = 'inv-1';
const INVOICE_URL = `${API_BASE_URL}/invoices/${INVOICE_ID}`;
const CURRENT_USER_URL = `${API_BASE_URL}/users/me`;

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
  review_flags: {
    code: string;
    summary: string | null;
    evidence: Record<string, unknown>;
    explainable: boolean;
  }[];
  decision: DecisionView | null;
}

function detailEnvelope(data: InvoiceDetailResponse) {
  return { success: true, data, error: null, meta: null };
}

function reviewerDetailEnvelope(data: ReviewerInvoiceDetailResponse) {
  return { success: true, data, error: null, meta: null };
}

function currentUserEnvelope(role: 'employee' | 'finance_reviewer') {
  return {
    success: true,
    data: { id: 'user-1', email: 'jamie@example.com', name: 'Jamie Lin', role },
    error: null,
    meta: null,
  };
}

function mockCurrentUser(role: 'employee' | 'finance_reviewer' = 'employee') {
  server.use(http.get(CURRENT_USER_URL, () => HttpResponse.json(currentUserEnvelope(role))));
}

function renderPage() {
  const Stub = createRoutesStub([
    {
      path: '/invoices/:id',
      Component: InvoiceDetailPage,
      HydrateFallback,
      ErrorBoundary,
      loader,
      action,
    },
    { path: paths.login, Component: () => <p>Login</p> },
  ]);

  render(<Stub initialEntries={[`/invoices/${INVOICE_ID}`]} />);
}

describe('InvoiceDetailPage', () => {
  beforeEach(() => {
    useAuthStore.getState().setAccessToken('signed.jwt.token');
    mockCurrentUser();
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
    mockCurrentUser('finance_reviewer');
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
              {
                code: 'duplicate_submission',
                summary: 'Possible duplicate',
                evidence: {},
                explainable: false,
              },
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

describe('DecisionForm submission', () => {
  beforeEach(() => {
    useAuthStore.getState().setAccessToken('signed.jwt.token');
    mockCurrentUser('finance_reviewer');
    server.use(
      http.get(INVOICE_URL, () =>
        HttpResponse.json(
          reviewerDetailEnvelope({
            id: INVOICE_ID,
            status: 'awaiting_review',
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
  });

  afterEach(() => useAuthStore.getState().setAccessToken(null));

  it('should show a distinct message when the invoice is no longer awaiting review', async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${INVOICE_URL}/decision`, () =>
        HttpResponse.json(
          {
            success: false,
            data: null,
            error: {
              code: 'INVOICE_NOT_AWAITING_REVIEW',
              message: 'Invoice is not awaiting review.',
            },
            meta: null,
          },
          { status: 409 },
        ),
      ),
    );

    renderPage();

    await user.click(await screen.findByRole('button', { name: /approve/i }));
    await user.type(screen.getByLabelText(/reason/i), 'Looks fine');
    await user.click(screen.getByRole('button', { name: /submit/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/no longer awaiting review/i);
  });

  it('should show the already-decided message when another reviewer wins the race', async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${INVOICE_URL}/decision`, () =>
        HttpResponse.json(
          {
            success: false,
            data: null,
            error: { code: 'INVOICE_ALREADY_DECIDED', message: 'Invoice already decided.' },
            meta: null,
          },
          { status: 409 },
        ),
      ),
    );

    renderPage();

    await user.click(await screen.findByRole('button', { name: /approve/i }));
    await user.type(screen.getByLabelText(/reason/i), 'Looks fine');
    await user.click(screen.getByRole('button', { name: /submit/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /already decided by another reviewer/i,
    );
  });

  it('should redirect to login when the session expires while submitting a decision', async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${INVOICE_URL}/decision`, () =>
        HttpResponse.json(
          {
            success: false,
            data: null,
            error: { code: 'UNAUTHORIZED', message: 'Expired' },
            meta: null,
          },
          { status: 401 },
        ),
      ),
    );

    renderPage();

    await user.click(await screen.findByRole('button', { name: /approve/i }));
    await user.type(screen.getByLabelText(/reason/i), 'Looks fine');
    await user.click(screen.getByRole('button', { name: /submit/i }));

    expect(await screen.findByText('Login')).toBeInTheDocument();
  });
});

describe('Explain review flag action', () => {
  beforeEach(() => {
    useAuthStore.getState().setAccessToken('signed.jwt.token');
    mockCurrentUser('finance_reviewer');
    server.use(
      http.get(INVOICE_URL, () =>
        HttpResponse.json(
          reviewerDetailEnvelope({
            id: INVOICE_ID,
            status: 'awaiting_review',
            employee: { id: 'emp-1', name: 'Priya Nair', email: 'priya@example.com' },
            extracted_fields: null,
            confidence: null,
            confidence_reason: null,
            review_flags: [
              {
                code: 'expense_within_amount_limit',
                summary: 'Invoice total exceeds the configured review limit',
                evidence: { limit: '500.00', total: '750.00' },
                explainable: true,
              },
              {
                code: 'line_item_total_consistency',
                summary: 'Line items do not sum to the stated total',
                evidence: {},
                explainable: false,
              },
            ],
            decision: null,
          }),
        ),
      ),
    );
  });

  afterEach(() => useAuthStore.getState().setAccessToken(null));

  it('shows the Explain action only for explainable flags', async () => {
    renderPage();

    const amountLimitFlag = (
      await screen.findByText(/exceeds the configured review limit/i)
    ).closest('details');
    const consistencyFlag = screen.getByText(/do not sum to the stated total/i).closest('details');

    expect(amountLimitFlag).not.toBeNull();
    expect(consistencyFlag).not.toBeNull();
    expect(within(amountLimitFlag!).getByRole('button', { name: /explain/i })).toBeInTheDocument();
    expect(
      within(consistencyFlag!).queryByRole('button', { name: /explain/i }),
    ).not.toBeInTheDocument();
  });

  it('renders the explanation and citations after a successful request', async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${INVOICE_URL}/flags/expense_within_amount_limit/explanation`, () =>
        HttpResponse.json({
          success: true,
          data: {
            explanation:
              'The invoice total of 750.00 exceeds the 500.00 policy limit for standard expenses.',
            citations: [
              {
                chunk_id: 'chunk-1',
                section_label: 'Section 3.2 Expense Limits',
                content: 'Standard expenses may not exceed $500.00 without VP approval.',
              },
            ],
            generated_by_model: 'gpt-5',
            generated_at: '2026-08-20T10:00:00Z',
          },
          error: null,
          meta: null,
        }),
      ),
    );

    renderPage();

    await user.click(await screen.findByRole('button', { name: /explain/i }));

    expect(await screen.findByText(/exceeds the 500\.00 policy limit/i)).toBeInTheDocument();
    expect(screen.getByText(/section 3\.2 expense limits/i)).toBeInTheDocument();
    expect(screen.getByText(/standard expenses may not exceed \$500\.00/i)).toBeInTheDocument();
  });
});

describe('InvoiceDetailPage access control', () => {
  afterEach(() => useAuthStore.getState().setAccessToken(null));

  it('should redirect unauthenticated users to login', async () => {
    const Stub = createRoutesStub([
      { path: paths.invoiceDetail, Component: InvoiceDetailPage, HydrateFallback, loader },
      { path: paths.login, Component: () => <p>Login</p> },
    ]);

    render(<Stub initialEntries={[`/invoices/${INVOICE_ID}`]} />);

    expect(await screen.findByText('Login')).toBeInTheDocument();
  });

  it('should redirect to login when the session expires while fetching the invoice', async () => {
    useAuthStore.getState().setAccessToken('signed.jwt.token');
    mockCurrentUser();
    server.use(
      http.get(INVOICE_URL, () =>
        HttpResponse.json(
          {
            success: false,
            data: null,
            error: { code: 'UNAUTHORIZED', message: 'Expired' },
            meta: null,
          },
          { status: 401 },
        ),
      ),
    );
    const Stub = createRoutesStub([
      { path: paths.invoiceDetail, Component: InvoiceDetailPage, HydrateFallback, loader },
      { path: paths.login, Component: () => <p>Login</p> },
    ]);

    render(<Stub initialEntries={[`/invoices/${INVOICE_ID}`]} />);

    expect(await screen.findByText('Login')).toBeInTheDocument();
  });
});
