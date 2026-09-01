import type { UserRole } from '../model/types';

const roleLabels: Record<UserRole, string> = {
  employee: 'Employee',
  reviewer: 'Reviewer',
};

export function formatUserRole(role: UserRole): string {
  return roleLabels[role];
}
