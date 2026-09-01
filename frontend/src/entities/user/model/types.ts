export interface CurrentUser {
  id: string;
  email: string;
  name: string;
  role: UserRole;
}

export type UserRole = 'employee' | 'reviewer';
