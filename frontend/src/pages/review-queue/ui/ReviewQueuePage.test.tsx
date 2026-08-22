import { createRoutesStub } from 'react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { delay, http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { API_BASE_URL } from '@/shared/config/env';
import { paths } from '@/shared/config/paths';
import { useAuthStore } from '@/shared/lib/authStore';

import { server } from '../../../../tests/mocks/server';
import { loader } from '../api/loader';

import { ErrorBoundary, HydrateFallback, ReviewQueuePage } from './ReviewQueuePage';

const REVIEW_QUEUE_URL = `${API_BASE_URL}/review-queue`;
const CURRENT_USER_URL = `${API_BASE_URL}/users/me`;

interface ReviewQueueItemResponse {
  id: string;
  status: 'processing_error' | 'awaiting_review';
  submitted_at: string;
  invoice_summary: {
    vendor_name: string;
    invoice_date: string;
    total_amount: string;
    currency: string;
  } | null;
  flag_count: number;
}

function queueEnvelope(data: ReviewQueueItemResponse[]) {
  return {
    success: true,
    data,
    error: null,
    meta: { total: data.length, offset: 0, limit: 10 },
  };
}

function currentUserEnvelope(role: 'employee' | 'finance_reviewer') {
  return {
    success: true,
    data: { id: 'user-1', email: 'morgan@example.com', name: 'Morgan Reyes', role },
    error: null,
    meta: null,
  };
}

function mockReviewer() {
  server.use(
    http.get(CURRENT_USER_URL, () => HttpResponse.json(currentUserEnvelope('finance_reviewer'))),
  );
}

function renderPage() {
  const Stub = createRoutesStub([
    {
      path: paths.reviewQueue,
      Component: ReviewQueuePage,
      HydrateFallback,
      ErrorBoundary,
      loader,
    },
    { path: paths.invoices, Component: () => <p>Invoices</p> },
    { path: paths.login, Component: () => <p>Login</p> },
    { path: paths.invoiceDetail, Component: () => <p>Invoice detail placeholder</p> },
  ]);

  render(<Stub initialEntries={[paths.reviewQueue]} />);
}

describe('ReviewQueuePage', () => {
  beforeEach(() => {
    useAuthStore.getState().setAccessToken('signed.jwt.token');
    mockReviewer();
  });

  afterEach(() => useAuthStore.getState().setAccessToken(null));

  it('should show a loading state while the queue is being fetched', () => {
    server.use(
      http.get(REVIEW_QUEUE_URL, async () => {
        await delay(50);
        return HttpResponse.json(queueEnvelope([]));
      }),
    );

    renderPage();

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('should show an empty state when nothing is awaiting review', async () => {
    server.use(http.get(REVIEW_QUEUE_URL, () => HttpResponse.json(queueEnvelope([]))));

    renderPage();

    expect(await screen.findByText(/nothing waiting for review/i)).toBeInTheDocument();
  });

  it('should render queued invoices oldest first, with vendor, amount, and flag count', async () => {
    server.use(
      http.get(REVIEW_QUEUE_URL, () =>
        HttpResponse.json(
          queueEnvelope([
            {
              id: 'rq-1',
              status: 'awaiting_review',
              submitted_at: '2026-08-09T08:41:00Z',
              invoice_summary: {
                vendor_name: 'Northwind Travel',
                invoice_date: '2026-08-09',
                total_amount: '1860.00',
                currency: 'USD',
              },
              flag_count: 2,
            },
            {
              id: 'rq-2',
              status: 'awaiting_review',
              submitted_at: '2026-08-10T13:02:00Z',
              invoice_summary: {
                vendor_name: 'Staples Inc.',
                invoice_date: '2026-08-10',
                total_amount: '58.20',
                currency: 'USD',
              },
              flag_count: 0,
            },
          ]),
        ),
      ),
    );

    renderPage();

    const list = await screen.findByRole('list', { name: /review queue/i });
    const rows = within(list).getAllByRole('link');

    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent(/Northwind Travel/);
    expect(rows[0]).toHaveTextContent(/2 flags/i);
    expect(rows[0]).toHaveAttribute('href', '/invoices/rq-1');
    expect(rows[1]).toHaveTextContent(/Staples Inc\./);
    expect(rows[1]).toHaveTextContent(/no flags/i);
  });

  it('should fall back to the invoice id when extraction produced no summary', async () => {
    server.use(
      http.get(REVIEW_QUEUE_URL, () =>
        HttpResponse.json(
          queueEnvelope([
            {
              id: 'rq-abcdefgh-1234',
              status: 'processing_error',
              submitted_at: '2026-08-10T16:20:00Z',
              invoice_summary: null,
              flag_count: 1,
            },
          ]),
        ),
      ),
    );

    renderPage();

    expect(await screen.findByText(/Invoice #rq-abcde/)).toBeInTheDocument();
  });

  it('should show a retry affordance when the queue fails to load, and recover on retry', async () => {
    server.use(
      http.get(REVIEW_QUEUE_URL, () => HttpResponse.json({ detail: 'boom' }, { status: 500 })),
    );

    renderPage();

    const retryButton = await screen.findByRole('button', { name: /retry/i });
    expect(screen.getByText(/couldn.?t load/i)).toBeInTheDocument();

    server.use(http.get(REVIEW_QUEUE_URL, () => HttpResponse.json(queueEnvelope([]))));
    await userEvent.setup().click(retryButton);

    expect(await screen.findByText(/nothing waiting for review/i)).toBeInTheDocument();
  });
});

describe('ReviewQueuePage access control', () => {
  afterEach(() => useAuthStore.getState().setAccessToken(null));

  it('should redirect unauthenticated users to login', async () => {
    renderPage();

    expect(await screen.findByText('Login')).toBeInTheDocument();
  });

  it('should redirect employees to their invoice list', async () => {
    useAuthStore.getState().setAccessToken('signed.jwt.token');
    server.use(
      http.get(CURRENT_USER_URL, () => HttpResponse.json(currentUserEnvelope('employee'))),
    );

    renderPage();

    expect(await screen.findByText('Invoices')).toBeInTheDocument();
  });
});
