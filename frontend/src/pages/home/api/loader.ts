import { redirect } from 'react-router';

import { landingPathForRole, requireCurrentUser } from '@/entities/user';

export async function loader() {
  return requireCurrentUser((user) => redirect(landingPathForRole(user.role)));
}
