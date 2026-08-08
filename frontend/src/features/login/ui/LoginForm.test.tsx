import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { SessionStore } from '@/entities/session'
import { API_BASE_URL } from '@/shared/config/env'

import { server } from '../../../../tests/mocks/server'

import { LoginForm } from './LoginForm'

const LOGIN_URL = `${API_BASE_URL}/auth/login`

describe('LoginForm', () => {
  it('should call loginWithCredentials with typed values on submit', async () => {
    server.use(
      http.post(LOGIN_URL, () =>
        HttpResponse.json(
          { access_token: 'signed.jwt.token', token_type: 'bearer' },
          { status: 200 },
        ),
      ),
    )
    const store = new SessionStore()
    const loginSpy = vi.spyOn(store, 'loginWithCredentials')
    const user = userEvent.setup()
    render(<LoginForm store={store} />)

    await user.type(screen.getByLabelText(/email/i), 'user@example.com')
    await user.type(screen.getByLabelText(/password/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    expect(loginSpy).toHaveBeenCalledWith('user@example.com', 'secret123')
  })

  it('should render invalid credentials message on 401', async () => {
    server.use(
      http.post(LOGIN_URL, () => HttpResponse.json({ detail: 'Invalid' }, { status: 401 })),
    )
    const store = new SessionStore()
    const user = userEvent.setup()
    render(<LoginForm store={store} />)

    await user.type(screen.getByLabelText(/email/i), 'user@example.com')
    await user.type(screen.getByLabelText(/password/i), 'wrong-password')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid email or password/i)
  })

  it('should render generic message on network error', async () => {
    server.use(http.post(LOGIN_URL, () => HttpResponse.error()))
    const store = new SessionStore()
    const user = userEvent.setup()
    render(<LoginForm store={store} />)

    await user.type(screen.getByLabelText(/email/i), 'user@example.com')
    await user.type(screen.getByLabelText(/password/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/something went wrong/i)
    expect(alert).not.toHaveTextContent(/invalid email or password/i)
  })
})
