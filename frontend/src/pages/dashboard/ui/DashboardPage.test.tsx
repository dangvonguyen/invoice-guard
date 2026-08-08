import { MemoryRouter, Route, Routes } from 'react-router'
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { sessionStore } from '@/entities/session'

import { DashboardPage } from './DashboardPage'

describe('DashboardPage', () => {
  afterEach(() => sessionStore.logout())

  it('should invite unauthenticated users to log in', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/login" element={<p>Login</p>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Log in to access your account.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login')
  })
})
