import { createBrowserRouter } from 'react-router'

import { paths } from '@/shared/shared/paths'

export const router = createBrowserRouter([
  {
    path: paths.home,
    lazy: () => import('@/pages/dashboard'),
  },
  {
    path: paths.login,
    lazy: () => import('@/pages/login'),
  },
  {
    path: '*',
    lazy: () => import('@/pages/not-found'),
  },
])
