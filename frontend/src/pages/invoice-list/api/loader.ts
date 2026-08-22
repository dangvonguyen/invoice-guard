import { redirect } from 'react-router';

import { listInvoices } from '@/entities/invoice';
import { getCurrentUser, landingPathForRole, UnauthenticatedError } from '@/entities/user';
import { paths } from '@/shared/config/paths';
import { useAuthStore } from '@/shared/lib/authStore';

export async function loader() {
  if (useAuthStore.getState().accessToken === null) {
    return redirect(paths.login);
  }

  try {
    const user = await getCurrentUser();
    if (user.role !== 'employee') {
      return redirect(landingPathForRole(user.role));
    }
    return await listInvoices();
  } catch (error) {
    if (error instanceof UnauthenticatedError) {
      useAuthStore.getState().setAccessToken(null);
      return redirect(paths.login);
    }
    throw error;
  }
}
