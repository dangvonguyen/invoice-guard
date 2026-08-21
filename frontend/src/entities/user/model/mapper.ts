import type { CurrentUserDto, UserRoleDto } from '../api/types';

import type { CurrentUser, UserRole } from './types';

function toUserRole(dto: UserRoleDto): UserRole {
  switch (dto) {
    case 'employee':
      return 'employee';
    case 'finance_reviewer':
      return 'reviewer';
    default: {
      const unhandled: never = dto;
      throw new Error(`Unhandled user role: ${String(unhandled)}`);
    }
  }
}

export function toCurrentUser(dto: CurrentUserDto): CurrentUser {
  return {
    id: dto.id,
    email: dto.email,
    name: dto.name,
    role: toUserRole(dto.role),
  };
}
