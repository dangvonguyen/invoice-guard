import { listInvoices } from '@/entities/invoice'

export async function loader() {
  return listInvoices()
}
