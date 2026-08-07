import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { server } from '../../../../tests/mocks/server'

const BASE_URL = 'http://localhost:8000/api'

async function submitLogin(email: string, password: string): Promise<void> {
  const user = userEvent.setup()
  render(<LoginPage />)

  await user.type(screen.getByLabelText(/email/i), email)
  await user.type(screen.getByLabelText(/password/i), password)
  await user.click(screen.getByRole('button', { name: /log in/i }))
}

describe('LoginPage acceptance', () => {
  it('should show authenticated state when credentials are valid', async () => {
    await submitLogin('user@example.com', 'secret123')

    expect(await screen.findByText(/logged in/i)).toBeInTheDocument()
  })

  it('should show error and stay on login when credentials are invalid', async () => {
    await submitLogin('user@example.com', 'wrong-password')

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid email or password/i)
    expect(screen.queryByText(/logged in/i)).not.toBeInTheDocument()
  })

  it('should show generic error when backend is unreachable', async () => {
    server.use(http.post(`${BASE_URL}/auth/login`, () => HttpResponse.error()))

    await submitLogin('user@example.com', 'secret123')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/something went wrong/i)
    expect(alert).not.toHaveTextContent(/invalid email or password/i)
  })

  it('should show generic error when backend returns server error', async () => {
    server.use(
      http.post(`${BASE_URL}/auth/login`, () =>
        HttpResponse.json({ detail: 'internal error' }, { status: 500 }),
      ),
    )

    await submitLogin('user@example.com', 'secret123')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/something went wrong/i)
  })
})
