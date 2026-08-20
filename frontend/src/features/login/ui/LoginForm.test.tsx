import { type ActionFunctionArgs, createRoutesStub } from 'react-router'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { LoginForm } from './LoginForm'

function renderForm(action: (args: ActionFunctionArgs) => unknown) {
  const Stub = createRoutesStub([{ path: '/login', Component: LoginForm, action }])
  render(<Stub initialEntries={['/login']} />)
}

describe('LoginForm', () => {
  it('should submit the entered email and password as form data', async () => {
    let submittedFormData: FormData | undefined
    const action = vi.fn(async ({ request }: ActionFunctionArgs) => {
      submittedFormData = await request.formData()
      return null
    })
    const user = userEvent.setup()
    renderForm(action)

    await user.type(screen.getByLabelText(/email/i), 'user@example.com')
    await user.type(screen.getByLabelText(/password/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    await waitFor(() => expect(action).toHaveBeenCalledTimes(1))
    expect(submittedFormData?.get('email')).toBe('user@example.com')
    expect(submittedFormData?.get('password')).toBe('secret123')
  })

  it('should render invalid credentials message when the action reports invalid credentials', async () => {
    const user = userEvent.setup()
    renderForm(() => ({ kind: 'invalid_credentials' }))

    await user.type(screen.getByLabelText(/email/i), 'user@example.com')
    await user.type(screen.getByLabelText(/password/i), 'wrong-password')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid email or password/i)
  })

  it('should render generic message when the action reports a network error', async () => {
    const user = userEvent.setup()
    renderForm(() => ({ kind: 'network_error' }))

    await user.type(screen.getByLabelText(/email/i), 'user@example.com')
    await user.type(screen.getByLabelText(/password/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/something went wrong/i)
    expect(alert).not.toHaveTextContent(/invalid email or password/i)
  })
})
