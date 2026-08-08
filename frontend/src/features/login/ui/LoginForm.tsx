import { type SubmitEvent, useState } from 'react'

import { type SessionStore, useSession } from '@/entities/session'
import { Button } from '@/shared/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/shared/ui/field'
import { Input } from '@/shared/ui/input'

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
    <Card className="w-full max-w-sm shadow-sm py-8">
      <CardHeader className="gap-2 text-center">
        <CardTitle className="text-3xl font-semibold">Welcome back</CardTitle>
        <CardDescription>Please log in to your account to continue.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit}>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="login-email">Email</FieldLabel>
              <Input
                id="login-email"
                type="email"
                autoComplete="email"
                placeholder="you@email.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </Field>

            <Field>
              <FieldLabel htmlFor="login-password">Password</FieldLabel>
              <Input
                id="login-password"
                type="password"
                autoComplete="current-password"
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </Field>

            <FieldError>
              {lastLoginError !== null ? loginErrorMessage(lastLoginError) : null}
            </FieldError>

            <Button type="submit" size="lg" className="w-full">
              Log in
            </Button>
          </FieldGroup>
        </form>
      </CardContent>
    </Card>
  )
}
