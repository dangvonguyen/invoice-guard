import { redirect } from 'react-router';

import { landingPathForRole, resolveCurrentUser } from '@/entities/user';

export async function loader() {
  const user = await resolveCurrentUser();
  if (user === null) {
    return null;
  }
  return redirect(landingPathForRole(user.role));
}
