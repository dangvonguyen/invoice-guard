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

import { ErrorBoundary, HydrateFallback, InvoiceListPage } from './InvoiceListPage';

const INVOICES_URL = `${API_BASE_URL}/invoices`;
const CURRENT_USER_URL = `${API_BASE_URL}/users/me`;

interface InvoiceListItem {
  id: string;
  status: 'processing' | 'processing_error' | 'awaiting_review' | 'approved' | 'rejected';
  created_at: string;
}

function listEnvelope(data: InvoiceListItem[]) {
  return {
    success: true,
    data,
    error: null,
    meta: { total: data.length, offset: 0, limit: 10 },
  };
}

function uploadEnvelope(id: string, status: InvoiceListItem['status']) {
  return { success: true, data: { id, status }, error: null, meta: null };
}

function currentUserEnvelope(role: 'employee' | 'finance_reviewer') {
  return {
    success: true,
    data: { id: 'user-1', email: 'jamie@example.com', name: 'Jamie Lin', role },
    error: null,
    meta: null,
  };
}

function mockEmployee() {
  server.use(http.get(CURRENT_USER_URL, () => HttpResponse.json(currentUserEnvelope('employee'))));
}

function renderPage() {
  const Stub = createRoutesStub([
    {
      path: '/invoices',
      Component: InvoiceListPage,
      HydrateFallback,
      ErrorBoundary,
      loader,
      action,
    },
    { path: '/invoices/:id', Component: () => <p>Invoice detail placeholder</p> },
  ]);

  render(<Stub initialEntries={['/invoices']} />);
}

describe('InvoiceListPage', () => {
  beforeEach(() => {
    useAuthStore.getState().setAccessToken('signed.jwt.token');
    mockEmployee();
  });

  afterEach(() => useAuthStore.getState().setAccessToken(null));

  it('should show a loading state while invoices are being fetched', async () => {
    server.use(
      http.get(INVOICES_URL, async () => {
        await delay(50);
        return HttpResponse.json(listEnvelope([]));
      }),
    );

    renderPage();

    expect(screen.getByRole('status')).toBeInTheDocument();
    await screen.findByRole('button', { name: /upload invoice/i });
  });

  it('should show an empty state when the employee has no invoices', async () => {
    server.use(http.get(INVOICES_URL, () => HttpResponse.json(listEnvelope([]))));

    renderPage();

    expect(await screen.findByText(/no invoices yet/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload invoice/i })).toBeEnabled();
  });

  it('should render fetched invoices newest first with their status', async () => {
    server.use(
      http.get(INVOICES_URL, () =>
        HttpResponse.json(
          listEnvelope([
            { id: 'inv-3', status: 'awaiting_review', created_at: '2026-08-18T09:55:00Z' },
            { id: 'inv-2', status: 'approved', created_at: '2026-08-15T10:00:00Z' },
            { id: 'inv-1', status: 'processing_error', created_at: '2026-08-10T16:20:00Z' },
          ]),
        ),
      ),
    );

    renderPage();

    const list = await screen.findByRole('list', { name: /invoices/i });
    const rows = within(list).getAllByRole('link');

    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent(/awaiting review/i);
    expect(rows[0]).toHaveAttribute('href', '/invoices/inv-3');
    expect(rows[1]).toHaveTextContent(/approved/i);
    expect(rows[2]).toHaveTextContent(/processing error/i);
  });

  it('should show a retry affordance when the list fails to load, and recover on retry', async () => {
    server.use(
      http.get(INVOICES_URL, () => HttpResponse.json({ detail: 'boom' }, { status: 500 })),
    );

    renderPage();

    const retryButton = await screen.findByRole('button', { name: /retry/i });
    expect(screen.getByText(/couldn.?t load/i)).toBeInTheDocument();

    server.use(
      http.get(INVOICES_URL, () =>
        HttpResponse.json(
          listEnvelope([{ id: 'inv-1', status: 'processing', created_at: '2026-08-19T10:02:00Z' }]),
        ),
      ),
    );
    await userEvent.setup().click(retryButton);

    expect(await screen.findByText(/processing/i)).toBeInTheDocument();
  });

  it('should let an employee upload an invoice and see it appear in the list', async () => {
    let invoices: InvoiceListItem[] = [];
    server.use(
      http.get(INVOICES_URL, () => HttpResponse.json(listEnvelope(invoices))),
      http.post(INVOICES_URL, () => {
        invoices = [{ id: 'new-id', status: 'processing', created_at: '2026-08-19T12:00:00Z' }];
        return HttpResponse.json(uploadEnvelope('new-id', 'processing'), { status: 201 });
      }),
    );
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/no invoices yet/i);

    await user.click(screen.getByRole('button', { name: /upload invoice/i }));
    const dialog = await screen.findByRole('dialog', { name: /upload invoice/i });
    const file = new File(['%PDF-1.4'], 'invoice.pdf', { type: 'application/pdf' });
    await user.upload(within(dialog).getByLabelText(/file/i), file);
    await user.click(within(dialog).getByRole('button', { name: /^upload$/i }));

    await screen.findByRole('list', { name: /invoices/i });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByText(/processing/i)).toBeInTheDocument();
  });

  it('should disable submit until a file is selected', async () => {
    server.use(http.get(INVOICES_URL, () => HttpResponse.json(listEnvelope([]))));
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/no invoices yet/i);

    await user.click(screen.getByRole('button', { name: /upload invoice/i }));
    const dialog = await screen.findByRole('dialog', { name: /upload invoice/i });

    expect(within(dialog).getByRole('button', { name: /^upload$/i })).toBeDisabled();

    const file = new File(['%PDF-1.4'], 'invoice.pdf', { type: 'application/pdf' });
    await user.upload(within(dialog).getByLabelText(/file/i), file);

    expect(within(dialog).getByRole('button', { name: /^upload$/i })).toBeEnabled();
  });

  it('should show an inline error and keep the dialog open when upload fails', async () => {
    server.use(
      http.get(INVOICES_URL, () => HttpResponse.json(listEnvelope([]))),
      http.post(INVOICES_URL, () => HttpResponse.json({ detail: 'boom' }, { status: 500 })),
    );
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/no invoices yet/i);

    await user.click(screen.getByRole('button', { name: /upload invoice/i }));
    const dialog = await screen.findByRole('dialog', { name: /upload invoice/i });
    const file = new File(['%PDF-1.4'], 'invoice.pdf', { type: 'application/pdf' });
    await user.upload(within(dialog).getByLabelText(/file/i), file);
    await user.click(within(dialog).getByRole('button', { name: /^upload$/i }));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(/something went wrong/i);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});

describe('InvoicesPage access control', () => {
  afterEach(() => useAuthStore.getState().setAccessToken(null));

  it('should redirect unauthenticated users to login', async () => {
    const Stub = createRoutesStub([
      { path: paths.invoices, Component: InvoiceListPage, HydrateFallback, loader, action },
      { path: paths.login, Component: () => <p>Login</p> },
    ]);

    render(<Stub initialEntries={[paths.invoices]} />);

    expect(await screen.findByText('Login')).toBeInTheDocument();
  });

  it('should redirect reviewers to the review queue, so they can never see their own invoices there', async () => {
    useAuthStore.getState().setAccessToken('signed.jwt.token');
    server.use(
      http.get(CURRENT_USER_URL, () => HttpResponse.json(currentUserEnvelope('finance_reviewer'))),
    );
    const Stub = createRoutesStub([
      { path: paths.invoices, Component: InvoiceListPage, HydrateFallback, loader, action },
      { path: paths.reviewQueue, Component: () => <p>Review queue</p> },
    ]);

    render(<Stub initialEntries={[paths.invoices]} />);

    expect(await screen.findByText('Review queue')).toBeInTheDocument();
  });
});
