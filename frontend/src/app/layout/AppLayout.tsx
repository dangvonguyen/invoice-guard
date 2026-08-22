import { Outlet, useLoaderData } from 'react-router';

import { AppHeader } from '@/widgets/app-header';

import type { loader } from './api/loader';

export function AppLayout() {
  const currentUser = useLoaderData<typeof loader>();

  return (
    <div className="grid min-h-screen grid-rows-[auto_1fr] bg-muted">
      <AppHeader user={currentUser} />

      <main className="min-h-0 pb-16">
        <Outlet />
      </main>
    </div>
  );
}
