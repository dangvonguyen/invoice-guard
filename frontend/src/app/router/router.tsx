import { createBrowserRouter } from 'react-router';

import { loader as appLayoutLoader } from '@/app/layout/api/loader';
import { AppLayout } from '@/app/layout/AppLayout';
import { paths } from '@/shared/config/paths';

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    loader: appLayoutLoader,
    children: [
      {
        path: paths.home,
        lazy: () => import('@/pages/home'),
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
        path: paths.newClaim,
        lazy: () => import('@/pages/claim-new'),
      },
      {
        path: paths.reviewQueue,
        lazy: () => import('@/pages/review-queue'),
      },
      {
        path: '*',
        lazy: () => import('@/pages/not-found'),
      },
    ],
  },
]);
