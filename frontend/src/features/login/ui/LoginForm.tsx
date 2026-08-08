import { type SubmitEvent, useState } from 'react'

import { type SessionStore, useSession } from '@/entities/session'

import { loginErrorMessage } from '../model/loginErrorMessage'

export interface LoginFormProps {
  store: SessionStore
}

export function LoginForm({ store }: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { lastLoginError } = useSession(store)

  function handleSubmit(event: SubmitEvent<HTMLFormElement>): void {
    event.preventDefault()
    void store.loginWithCredentials(email, password)
  }

  return (
    <form onSubmit={handleSubmit}>
      <label htmlFor="login-email">Email</label>
      <input
        id="login-email"
        type="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />

      <label htmlFor="login-password">Password</label>
      <input
        id="login-password"
        type="password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />

      <button type="submit">Log in</button>

      {lastLoginError !== null && <p role="alert">{loginErrorMessage(lastLoginError)}</p>}
    </form>
  )
}
