import { MemoryRouter, Route, Routes } from 'react-router'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'

import { sessionStore } from '@/entities/session'
import { API_BASE_URL } from '@/shared/config/env'
import { paths } from '@/shared/config/paths'

import { server } from '../../../../tests/mocks/server'

import { LoginPage } from './LoginPage'

async function submitLogin(email: string, password: string): Promise<void> {
  const user = userEvent.setup()
  render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path={paths.login} element={<LoginPage />} />
        <Route path={paths.invoices} element={<p>Home</p>} />
      </Routes>
    </MemoryRouter>,
  )

  await user.type(screen.getByLabelText(/email/i), email)
  await user.type(screen.getByLabelText(/password/i), password)
  await user.click(screen.getByRole('button', { name: /log in/i }))
}

describe('LoginPage acceptance', () => {
  afterEach(() => {
    // Reset the session explicitly to avoid its state persisting across tests
    sessionStore.logout()
  })

  it('should navigate home when credentials are valid', async () => {
    await submitLogin('user@example.com', 'secret123')

    expect(await screen.findByText('Home')).toBeInTheDocument()
  })

  it('should show error and stay on login when credentials are invalid', async () => {
    await submitLogin('user@example.com', 'wrong-password')

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid email or password/i)
    expect(screen.queryByText('Home')).not.toBeInTheDocument()
  })

  it('should show generic error when backend is unreachable', async () => {
    server.use(http.post(`${API_BASE_URL}/auth/login`, () => HttpResponse.error()))

    await submitLogin('user@example.com', 'secret123')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/something went wrong/i)
    expect(alert).not.toHaveTextContent(/invalid email or password/i)
  })

  it('should show generic error when backend returns server error', async () => {
    server.use(
      http.post(`${API_BASE_URL}/auth/login`, () =>
        HttpResponse.json({ detail: 'internal error' }, { status: 500 }),
      ),
    )

    await submitLogin('user@example.com', 'secret123')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/something went wrong/i)
  })
})
