import { redirect } from 'react-router';

import { listInvoices } from '@/entities/invoice';
import { landingPathForRole, requireCurrentUser } from '@/entities/user';

export async function loader() {
  return requireCurrentUser(async (user) => {
    if (user.role !== 'employee') {
      return redirect(landingPathForRole(user.role));
    }
    return listInvoices();
  });
}
