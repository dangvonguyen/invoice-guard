import { redirect } from 'react-router';

import { paths } from '@/shared/config/paths';
import { useAuthStore } from '@/shared/lib/authStore';

export function loader() {
  if (useAuthStore.getState().accessToken !== null) {
    return redirect(paths.invoices);
  }
  return null;
}
