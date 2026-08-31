import { QueryClient } from '@tanstack/react-query';
import { ApiError, isConflict, isPolicyValueMissing } from './errors';

/**
 * Retry policy.
 *
 * A version conflict and a missing policy value are both deterministic: the
 * server will answer identically next time, so retrying only delays the officer
 * seeing what happened. Authorization and validation failures are the same. Only
 * transport faults and 5xx are worth another attempt.
 */
function shouldRetry(failureCount: number, error: unknown): boolean {
  if (isConflict(error) || isPolicyValueMissing(error)) {
    return false;
  }
  if (error instanceof ApiError && error.status < 500) {
    return false;
  }
  return failureCount < 2;
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: shouldRetry,
      staleTime: 30_000,
      // R22.4 and R21.7 require the portal to present when data was computed.
      // Silent background refetching would make a displayed timestamp lie about
      // what is on screen, so refresh is explicit.
      refetchOnWindowFocus: false,
    },
    mutations: {
      // Never retry a mutation: the conditional UPDATE in design §7.1 makes a
      // blind replay either a no-op or a conflict, and neither is useful.
      retry: false,
    },
  },
});
