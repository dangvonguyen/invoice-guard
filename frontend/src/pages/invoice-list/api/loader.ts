import { redirect } from 'react-router';

import { listInvoices } from '@/entities/invoice';
import { paths } from '@/shared/config/paths';
import { useAuthStore } from '@/shared/lib/authStore';

export async function loader() {
  if (useAuthStore.getState().accessToken === null) {
    return redirect(paths.login);
  }
  return listInvoices();
}
