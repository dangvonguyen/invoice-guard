import { type LoaderFunctionArgs, redirect } from 'react-router'

import { getInvoice, type GetInvoiceResult } from '@/entities/invoice'
import { tokenStorage } from '@/entities/session'
import { paths } from '@/shared/config/paths'

export async function loader({ params }: LoaderFunctionArgs): Promise<GetInvoiceResult | Response> {
  if (!tokenStorage.isAuthenticated()) {
    return redirect(paths.login)
  }
  if (params.id === undefined) {
    return { kind: 'not_found' }
  }
  return getInvoice(params.id)
}
