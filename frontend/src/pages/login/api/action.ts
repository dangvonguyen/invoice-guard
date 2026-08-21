import { type ActionFunctionArgs, redirect } from 'react-router';

import { InvalidCredentialsError, login } from '@/entities/session';
import { paths } from '@/shared/config/paths';

export async function action({ request }: ActionFunctionArgs) {
  const formData = await request.formData();
  const email = formData.get('email');
  const password = formData.get('password');

  try {
    await login(
      typeof email === 'string' ? email : '',
      typeof password === 'string' ? password : '',
    );
  } catch (error) {
    if (error instanceof InvalidCredentialsError) return error;
    return new Error('Something went wrong. Please try again.');
  }

  return redirect(paths.invoices);
}
