import { Link } from 'react-router';
import { ShieldCheck } from 'lucide-react';

import { type CurrentUser, formatUserRole } from '@/entities/user';
import { LogoutButton } from '@/features/logout';
import { paths } from '@/shared/config/paths';

interface Props {
  user: CurrentUser | null;
}

export function AppHeader({ user }: Props) {
  return (
    <header className="sticky top-0 z-10 border-b border-border bg-muted px-5">
      <div className="flex h-16 items-center justify-between">
        <Link
          to={paths.home}
          className="flex items-center gap-2 font-semibold tracking-wide"
          aria-label="Home"
        >
          <ShieldCheck className="size-6" aria-hidden="true" />
          <span className="uppercase">Invoice Guard</span>
        </Link>

        {user !== null && (
          <div className="flex items-center gap-8">
            <span className="text-sm text-muted-foreground">
              {user.name} · {formatUserRole(user.role)}
            </span>
            <LogoutButton />
          </div>
        )}
      </div>
    </header>
  );
}
