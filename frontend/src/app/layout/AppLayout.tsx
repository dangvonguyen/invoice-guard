import { Link, Outlet } from 'react-router'
import { ShieldCheck } from 'lucide-react'

import { paths } from '@/shared/shared/paths'

export function AppLayout() {
  return (
    <div className="grid min-h-screen grid-rows-[auto_1fr] bg-muted/50">
      <header className="px-5">
        <div className="flex h-16 items-center">
          <Link
            to={paths.home}
            className="flex items-center gap-2 font-semibold tracking-wide"
            aria-label="Home"
          >
            <ShieldCheck className="size-6" aria-hidden="true" />
            <span className="uppercase">Invoice Guard</span>
          </Link>
        </div>
      </header>

      <main className="min-h-0 pb-16">
        <Outlet />
      </main>
    </div>
  )
}
