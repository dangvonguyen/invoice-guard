import { describe, expect, it } from 'vitest'

import type { LoginErrorKind } from '@/entities/session'

import { loginErrorMessage } from './loginErrorMessage'

describe('loginErrorMessage', () => {
  it('should return invalid credentials copy for invalid credentials', () => {
    const kind: LoginErrorKind = 'invalid_credentials'

    expect(loginErrorMessage(kind)).toBe('Invalid email or password')
  })

  it('should return generic copy for network error', () => {
    const kind: LoginErrorKind = 'network_error'

    expect(loginErrorMessage(kind)).toBe('Something went wrong. Please try again.')
  })
})
