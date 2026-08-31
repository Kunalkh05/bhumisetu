import { RouterProvider } from 'react-router-dom';
import { router } from './officer/routes';

export function App() {
  return <RouterProvider router={router} />;
}
