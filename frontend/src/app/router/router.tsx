import { createBrowserRouter } from 'react-router'

import { AppLayout } from '@/app/layout/AppLayout'
import { paths } from '@/shared/config/paths'

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      {
        path: paths.home,
        lazy: () => import('@/pages/dashboard'),
      },
      {
        path: paths.login,
        lazy: () => import('@/pages/login'),
      },
      {
        path: paths.invoices,
        lazy: () => import('@/pages/invoice-list'),
      },
      {
        path: paths.invoiceDetail,
        lazy: () => import('@/pages/invoice-detail'),
      },
      {
        path: '*',
        lazy: () => import('@/pages/not-found'),
      },
    ],
  },
])
