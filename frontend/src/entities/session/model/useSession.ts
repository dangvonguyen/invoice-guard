import { useSyncExternalStore } from 'react'

import type { LoginErrorKind, SessionStore } from './sessionStore'

export interface SessionSnapshot {
  isAuthenticated: boolean
  accessToken: string | null
  lastLoginError: LoginErrorKind | null
}

export function useSession(store: SessionStore): SessionSnapshot {
  return useSyncExternalStore(
    (onStoreChange) => store.subscribe(onStoreChange),
    () => getSnapshot(store),
  )
}

// getSnapshot must return a referentially stable value when nothing has
// changed, or useSyncExternalStore re-renders forever (a new object literal
// on every call is a new reference every time). Cache per store instance,
// invalidated only via the store's own subscribe/notify. Both accessToken
// and lastLoginError must be checked: a failed login leaves accessToken at
// null both before and after the attempt, so keying on accessToken alone
// would silently miss the transition to a login error.
const snapshotCache = new WeakMap<SessionStore, SessionSnapshot>()

function getSnapshot(store: SessionStore): SessionSnapshot {
  const cached = snapshotCache.get(store)
  const accessToken = store.getAccessToken()
  const lastLoginError = store.getLastLoginError()
  if (cached?.accessToken === accessToken && cached.lastLoginError === lastLoginError) {
    return cached
  }

  const snapshot: SessionSnapshot = {
    isAuthenticated: store.isAuthenticated(),
    accessToken,
    lastLoginError,
  }
  snapshotCache.set(store, snapshot)
  return snapshot
}
