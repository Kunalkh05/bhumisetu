import { Link } from 'react-router-dom';
import { paths } from '../routes/paths';

export function NotFoundPage() {
  return (
    <section aria-labelledby="page-title">
      <h1 id="page-title" className="text-xl font-semibold text-ink">
        Page not found
      </h1>
      <p className="mt-2 text-sm text-ink-muted">
        No route matches this address.
      </p>
      <Link
        to={paths.dashboard}
        className="mt-4 inline-block text-sm text-severity-advisory underline"
      >
        Return to dashboard
      </Link>
    </section>
  );
}
