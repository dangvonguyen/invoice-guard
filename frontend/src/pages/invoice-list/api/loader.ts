import { redirect } from 'react-router'

import { listInvoices } from '@/entities/invoice'
import { tokenStorage } from '@/entities/session'
import { paths } from '@/shared/config/paths'

export async function loader() {
  if (!tokenStorage.isAuthenticated()) {
    return redirect(paths.login)
  }
  return listInvoices()
}
