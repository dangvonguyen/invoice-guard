import { paths } from '@/shared/config/paths';

import type { UserRole } from '../model/types';

const landingPaths: Record<UserRole, string> = {
  employee: paths.invoices,
  reviewer: paths.reviewQueue,
};

export function landingPathForRole(role: UserRole): string {
  return landingPaths[role];
}
