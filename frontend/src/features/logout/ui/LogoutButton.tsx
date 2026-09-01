import { Button } from '@/shared/ui/button';

import { useLogout } from '../model/useLogout';

export function LogoutButton() {
  const logout = useLogout();

  return (
    <Button
      type="button"
      variant="link"
      size="sm"
      className="px-0 text-foreground"
      onClick={logout}
    >
      Log out
    </Button>
  );
}
