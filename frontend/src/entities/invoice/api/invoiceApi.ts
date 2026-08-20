import { apiClient } from '@/shared/api/client'

import type { InvoiceListItem, InvoiceUploadResponse } from '../model/types'

export type ListInvoicesResult = { kind: 'ok'; invoices: InvoiceListItem[] } | { kind: 'error' }

export async function listInvoices(): Promise<ListInvoicesResult> {
  try {
    const { data, error } = await apiClient.GET('/invoices')

    if (error !== undefined || data?.data === null || data?.data === undefined) {
      return { kind: 'error' }
    }
    return { kind: 'ok', invoices: data.data }
  } catch {
    return { kind: 'error' }
  }
}

export type UploadInvoiceResult = { kind: 'ok'; invoice: InvoiceUploadResponse } | { kind: 'error' }

export async function uploadInvoice(file: File): Promise<UploadInvoiceResult> {
  try {
    const formData = new FormData()
    formData.append('file', file)

    const { data, error } = await apiClient.POST('/invoices', {
      body: formData as unknown as { file: string },
    })

    if (error !== undefined || data?.data === null || data?.data === undefined) {
      return { kind: 'error' }
    }
    return { kind: 'ok', invoice: data.data }
  } catch {
    return { kind: 'error' }
  }
}
