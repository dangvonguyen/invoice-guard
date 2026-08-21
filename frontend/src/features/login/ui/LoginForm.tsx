import { Form, useActionData, useNavigation } from 'react-router';

import type { LoginErrorKind } from '@/entities/session';
import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card';
import { Field, FieldError, FieldGroup, FieldLabel } from '@/shared/ui/field';
import { Input } from '@/shared/ui/input';

import { loginErrorMessage } from '../model/loginErrorMessage';

export function LoginForm() {
  const actionData = useActionData<{ kind: LoginErrorKind }>();
  const navigation = useNavigation();
  const isSubmitting = navigation.state === 'submitting';

  return (
    <Card className="w-full max-w-sm shadow-sm py-8">
      <CardHeader className="gap-2 text-center">
        <CardTitle className="text-3xl font-semibold">Welcome back</CardTitle>
        <CardDescription>Please log in to your account to continue.</CardDescription>
      </CardHeader>
      <CardContent>
        <Form method="post">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="login-email">Email</FieldLabel>
              <Input
                id="login-email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="you@email.com"
                required
              />
            </Field>

            <Field>
              <FieldLabel htmlFor="login-password">Password</FieldLabel>
              <Input
                id="login-password"
                name="password"
                type="password"
                autoComplete="current-password"
                placeholder="Enter your password"
                required
              />
            </Field>

            <FieldError>
              {actionData !== undefined ? loginErrorMessage(actionData.kind) : null}
            </FieldError>

            <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
              Log in
            </Button>
          </FieldGroup>
        </Form>
      </CardContent>
    </Card>
  );
}
