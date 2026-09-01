import { redirect } from 'react-router';

import { paths } from '@/shared/config/paths';
import { useAuthStore } from '@/shared/lib/authStore';

import { landingPathForRole } from '../lib/landingPathForRole';
import type { CurrentUser, UserRole } from '../model/types';

import { getCurrentUser, UnauthenticatedError } from './getCurrentUser';

function clearAccessToken(): void {
  useAuthStore.getState().setAccessToken(null);
}

/**
 * Clears the session and returns a redirect to `/login` for a caught
 * `UnauthenticatedError`, or `undefined` for any other error so the caller
 * can keep handling it. For loaders/actions that call entity `api/`
 * functions directly (outside `requireCurrentUser`) and still need to react
 * to a session expiring mid-request, e.g. a follow-up mutation.
 */
export function redirectOnSessionExpiry(error: unknown): ReturnType<typeof redirect> | undefined {
  if (!(error instanceof UnauthenticatedError)) {
    return undefined;
  }
  clearAccessToken();
  return redirect(paths.login);
}

/**
 * Resolves the current user, treating a missing or expired session as `null`
 * instead of redirecting. For loaders that render differently for a signed-out
 * visitor rather than sending them away (the app shell, the login page).
 */
export async function resolveCurrentUser(): Promise<CurrentUser | null> {
  if (useAuthStore.getState().accessToken === null) {
    return null;
  }

  try {
    return await getCurrentUser();
  } catch (error) {
    if (error instanceof UnauthenticatedError) {
      clearAccessToken();
      return null;
    }
    throw error;
  }
}

/**
 * Resolves the current user and hands it to `run`, redirecting to `/login`
 * when there is no session or it expires — including mid-`run`, e.g. a 401
 * from a follow-up request `run` makes.
 */
export async function requireCurrentUser<T>(
  run: (user: CurrentUser) => Promise<T> | T,
): Promise<T | ReturnType<typeof redirect>> {
  if (useAuthStore.getState().accessToken === null) {
    return redirect(paths.login);
  }

  try {
    const user = await getCurrentUser();
    return await run(user);
  } catch (error) {
    if (error instanceof UnauthenticatedError) {
      clearAccessToken();
      return redirect(paths.login);
    }
    throw error;
  }
}

/**
 * Redirect to the current user's own landing page when their role doesn't
 * match `role`.
 */
export async function requireRole<T>(
  role: UserRole,
  run: (user: CurrentUser) => Promise<T> | T,
): Promise<T | ReturnType<typeof redirect>> {
  return requireCurrentUser((user) =>
    user.role !== role ? redirect(landingPathForRole(user.role)) : run(user),
  );
}
