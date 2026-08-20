import { useCallback, useEffect, useState } from 'react'

import { type InvoiceListItem, listInvoices } from '@/entities/invoice'

export type InvoicesLoadState = 'idle' | 'loading' | 'error' | 'loaded'

export interface UseInvoicesResult {
  loadState: InvoicesLoadState
  invoices: InvoiceListItem[]
  refetch: () => void
}

export function useInvoices(): UseInvoicesResult {
  const [loadState, setLoadState] = useState<InvoicesLoadState>('idle')
  const [invoices, setInvoices] = useState<InvoiceListItem[]>([])

  const fetchInvoices = useCallback(async () => {
    setLoadState('loading')

    const result = await listInvoices()

    if (result.kind === 'error') {
      setLoadState('error')
      return
    }
    setInvoices(result.invoices)
    setLoadState('loaded')
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchInvoices()
  }, [fetchInvoices])

  function refetch(): void {
    void fetchInvoices()
  }

  return { loadState, invoices, refetch }
}
