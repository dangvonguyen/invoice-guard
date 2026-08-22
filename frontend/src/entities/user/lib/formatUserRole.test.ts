import { describe, expect, it } from 'vitest';

import type { UserRole } from '../model/types';

import { formatUserRole } from './formatUserRole';

describe('formatUserRole', () => {
  it.each([
    ['employee', 'Employee'],
    ['reviewer', 'Reviewer'],
  ] satisfies [UserRole, string][])('should formats %s as %s', (role, expected) => {
    expect(formatUserRole(role)).toBe(expected);
  });
});
