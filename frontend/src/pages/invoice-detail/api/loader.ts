import { type LoaderFunctionArgs, redirect } from 'react-router'

import { getInvoice, type GetInvoiceResult } from '@/entities/invoice'
import { paths } from '@/shared/config/paths'
import { useAuthStore } from '@/shared/lib/authStore'

export async function loader({ params }: LoaderFunctionArgs): Promise<GetInvoiceResult | Response> {
  if (useAuthStore.getState().accessToken === null) {
    return redirect(paths.login)
  }
  if (params.id === undefined) {
    return { kind: 'not_found' }
  }
  return getInvoice(params.id)
}
