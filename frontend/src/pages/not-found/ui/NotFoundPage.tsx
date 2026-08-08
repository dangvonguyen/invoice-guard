import { Link } from 'react-router'

import { paths } from '@/shared/shared/paths'
import { buttonVariants } from '@/shared/ui/button'

export function NotFoundPage() {
  return (
    <div className="grid h-full grid-rows-[1fr_auto] px-5 py-8">
      <section
        className="grid place-content-center justify-items-center text-center"
        aria-labelledby="not-found-title"
      >
        <p className="text-9xl leading-[0.75] font-semibold" aria-hidden="true">
          404
        </p>
        <h1 id="not-found-title" className="mt-9 text-2xl font-semibold tracking-tight sm:text-3xl">
          Oops! Page not found.
        </h1>
        <p className="mt-4 max-w-lg text-sm leading-6 text-muted-foreground sm:text-base">
          The connection link may be broken, or the resource has moved.
        </p>
        <Link to={paths.home} className={buttonVariants({ size: 'lg', className: 'mt-7' })}>
          Return to Home Page
        </Link>
      </section>
    </div>
  )
}
