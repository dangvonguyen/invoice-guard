import { type CurrentUser, getCurrentUser, UnauthenticatedError } from '@/entities/user';
import { useAuthStore } from '@/shared/lib/authStore';

export async function loader(): Promise<CurrentUser | null> {
  if (useAuthStore.getState().accessToken === null) {
    return null;
  }

  try {
    return await getCurrentUser();
  } catch (error) {
    if (error instanceof UnauthenticatedError) {
      useAuthStore.getState().setAccessToken(null);
      return null;
    }
    throw error;
  }
}
