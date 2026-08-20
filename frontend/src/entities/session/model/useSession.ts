import { useSyncExternalStore } from 'react'

import type { TokenStorage } from '@/shared/lib/tokenStorage'

export interface SessionSnapshot {
  isAuthenticated: boolean
}

export function useSession(store: TokenStorage): SessionSnapshot {
  return useSyncExternalStore(
    (onStoreChange) => store.subscribe(onStoreChange),
    () => getSnapshot(store),
  )
}

// getSnapshot must return a referentially stable value when nothing has
// changed, or useSyncExternalStore re-renders forever (a new object literal
// on every call is a new reference every time). Cache per store instance,
// invalidated only via the store's own subscribe/notify.
const snapshotCache = new WeakMap<TokenStorage, SessionSnapshot>()

function getSnapshot(store: TokenStorage): SessionSnapshot {
  const cached = snapshotCache.get(store)
  const isAuthenticated = store.isAuthenticated()
  if (cached?.isAuthenticated === isAuthenticated) {
    return cached
  }

  const snapshot: SessionSnapshot = { isAuthenticated }
  snapshotCache.set(store, snapshot)
  return snapshot
}
