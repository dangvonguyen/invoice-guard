import { createBrowserRouter } from 'react-router'

import { paths } from '@/app/router/paths'

export const router = createBrowserRouter([
  {
    path: paths.home,
    lazy: () => import('@/pages/dashboard'),
  },
  {
    path: '*',
    lazy: () => import('@/pages/not-found'),
  },
])
