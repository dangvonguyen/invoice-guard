import { type ActionFunctionArgs, redirect } from 'react-router';

import { login } from '@/entities/session';
import { paths } from '@/shared/config/paths';

export async function action({ request }: ActionFunctionArgs) {
  const formData = await request.formData();
  const email = formData.get('email');
  const password = formData.get('password');

  const result = await login(
    typeof email === 'string' ? email : '',
    typeof password === 'string' ? password : '',
  );

  if (result.kind === 'ok') {
    return redirect(paths.invoices);
  }
  return result;
}
