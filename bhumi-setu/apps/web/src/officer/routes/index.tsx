import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell } from '../shell/AppShell';
import { paths } from './paths';
import { DashboardPage } from '../pages/DashboardPage';
import { CaseListPage } from '../pages/CaseListPage';
import { CaseWorkspacePage } from '../pages/CaseWorkspacePage';
import { MapPage } from '../pages/MapPage';
import { InterventionQueuePage } from '../pages/InterventionQueuePage';
import { ValidationIssuesPage } from '../pages/ValidationIssuesPage';
import { ImportBatchesPage } from '../pages/ImportBatchesPage';
import { NotFoundPage } from '../pages/NotFoundPage';

/**
 * Vite is configured with base '/officer/' and the proxy keeps that prefix, so
 * the router's basename has to match or in-app links break behind Caddy while
 * appearing to work on a bare dev server.
 */
export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <AppShell />,
      children: [
        { index: true, element: <DashboardPage /> },
        { path: 'cases', element: <CaseListPage /> },
        { path: 'cases/:caseId', element: <CaseWorkspacePage /> },
        { path: 'map', element: <MapPage /> },
        { path: 'queue', element: <InterventionQueuePage /> },
        { path: 'issues', element: <ValidationIssuesPage /> },
        { path: 'imports', element: <ImportBatchesPage /> },
        { path: 'dashboard', element: <Navigate to={paths.dashboard} replace /> },
        { path: '*', element: <NotFoundPage /> },
      ],
    },
  ],
  { basename: '/officer' },
);
