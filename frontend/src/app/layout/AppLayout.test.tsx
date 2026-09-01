import { createRoutesStub } from 'react-router';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { API_BASE_URL } from '@/shared/config/env';
import { paths } from '@/shared/config/paths';
import { useAuthStore } from '@/shared/lib/authStore';

import { server } from '../../../tests/mocks/server';

import { loader } from './api/loader';
import { AppLayout } from './AppLayout';

const CURRENT_USER_URL = `${API_BASE_URL}/users/me`;

function currentUserEnvelope() {
  return {
    success: true,
    data: { id: 'user-1', email: 'jamie@example.com', name: 'Jamie Lin', role: 'employee' },
    error: null,
    meta: null,
  };
}

function renderLayout(initialEntry: string = paths.home) {
  const Stub = createRoutesStub([
    {
      Component: AppLayout,
      loader,
      children: [
        { path: paths.home, Component: () => <p>Home</p> },
        { path: paths.login, Component: () => <p>Login</p> },
      ],
    },
  ]);

  render(<Stub initialEntries={[initialEntry]} />);
}

describe('AppLayout', () => {
  afterEach(() => useAuthStore.getState().setAccessToken(null));

  it('should always show the app name', async () => {
    renderLayout();

    expect(await screen.findByText('Invoice Guard')).toBeInTheDocument();
  });

  it('should not show user info or a log out control when unauthenticated', async () => {
    renderLayout();

    await screen.findByText('Invoice Guard');
    expect(screen.queryByRole('button', { name: /log out/i })).not.toBeInTheDocument();
  });

  describe('when authenticated', () => {
    beforeEach(() => {
      useAuthStore.getState().setAccessToken('signed.jwt.token');
      server.use(http.get(CURRENT_USER_URL, () => HttpResponse.json(currentUserEnvelope())));
    });

    it("should show the current user's name, role, and a log out control", async () => {
      renderLayout();

      expect(await screen.findByText(/Jamie Lin/)).toBeInTheDocument();
      expect(screen.getByText(/Employee/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /log out/i })).toBeInTheDocument();
    });

    it('should clear the session, redirect to login, and stop showing the previous user in the header', async () => {
      const user = userEvent.setup();
      renderLayout();

      await user.click(await screen.findByRole('button', { name: /log out/i }));

      expect(await screen.findByText('Login')).toBeInTheDocument();
      expect(useAuthStore.getState().accessToken).toBeNull();
      expect(screen.queryByText(/Jamie Lin/)).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /log out/i })).not.toBeInTheDocument();
    });
  });
});
