import { useNavigate, useRevalidator } from 'react-router';

import { paths } from '@/shared/config/paths';
import { useAuthStore } from '@/shared/lib/authStore';

export function useLogout(): () => void {
  const navigate = useNavigate();
  const revalidator = useRevalidator();

  return () => {
    useAuthStore.getState().setAccessToken(null);

    // A plain client-side navigation doesn't revalidate the AppLayout
    // route's loader (only submissions do by default), so the header
    // would otherwise keep showing the previous user after logout.
    const navigation = navigate(paths.login);
    if (navigation instanceof Promise) {
      void navigation.then(() => revalidator.revalidate());
    } else {
      void revalidator.revalidate();
    }
  };
}
