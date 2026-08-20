import { redirect } from 'react-router'

import { tokenStorage } from '@/entities/session'
import { paths } from '@/shared/config/paths'

export function loader() {
  if (tokenStorage.isAuthenticated()) {
    return redirect(paths.invoices)
  }
  return null
}
