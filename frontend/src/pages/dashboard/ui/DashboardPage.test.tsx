import { MemoryRouter, Route, Routes } from 'react-router';
import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { useAuthStore } from '@/shared/lib/authStore';

import { DashboardPage } from './DashboardPage';

describe('DashboardPage', () => {
  afterEach(() => useAuthStore.getState().setAccessToken(null));

  it('should invite unauthenticated users to log in', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/login" element={<p>Login</p>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login');
  });
});
