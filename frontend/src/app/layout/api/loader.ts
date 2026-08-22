import { type CurrentUser, resolveCurrentUser } from '@/entities/user';

export async function loader(): Promise<CurrentUser | null> {
  return resolveCurrentUser();
}
