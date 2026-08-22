import { redirect } from 'react-router';

import { listReviewQueue } from '@/entities/invoice';
import { landingPathForRole, requireCurrentUser } from '@/entities/user';

export async function loader() {
  return requireCurrentUser(async (user) => {
    if (user.role !== 'reviewer') {
      return redirect(landingPathForRole(user.role));
    }
    return listReviewQueue();
  });
}
