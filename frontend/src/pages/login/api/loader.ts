import { redirect } from 'react-router'

import { sessionStore } from '@/entities/session'
import { paths } from '@/shared/config/paths'

export function loader() {
  if (sessionStore.isAuthenticated()) {
    return redirect(paths.invoices)
  }
  return null
}
