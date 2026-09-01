import { listInvoices } from '@/entities/invoice';
import { requireRole } from '@/entities/user';

export async function loader() {
  return requireRole('employee', () => listInvoices());
}
