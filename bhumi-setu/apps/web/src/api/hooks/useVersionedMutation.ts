import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';
import { request, type RequestOptions } from '../client';
import { EntityVersionConflictError } from '../errors';

/**
 * A versioned entity as the API returns it. Every mutable entity carries its
 * Entity_Version (R29.1), and a mutation has to echo the version it was read at.
 */
export interface Versioned {
  readonly id: string;
  readonly entity_version: number;
}

interface VersionedMutationArgs<TBody> {
  /** The entity as it was read. Its version becomes the If-Match header. */
  readonly entity: Versioned;
  readonly body: TBody;
}

interface UseVersionedMutationOptions<TBody> {
  readonly path: (entity: Versioned) => string;
  readonly method?: NonNullable<RequestOptions['method']>;
  /** Query keys to invalidate on success. */
  readonly invalidates?: readonly (readonly unknown[])[];
  readonly onConflict?: (error: EntityVersionConflictError, args: VersionedMutationArgs<TBody>) => void;
}

/**
 * Mutation hook that carries Entity_Version automatically.
 *
 * R29.2 requires the version observed at read time to be presented with the
 * modification request. Putting that in the data layer rather than in each form
 * means a new screen gets conflict detection by default — the failure mode this
 * avoids is a form that simply forgets, which is silent and only manifests as a
 * lost update under concurrent edit.
 */
export function useVersionedMutation<TResult, TBody>(
  options: UseVersionedMutationOptions<TBody>,
): UseMutationResult<TResult, unknown, VersionedMutationArgs<TBody>> {
  const client = useQueryClient();
  const { path, method = 'PATCH', invalidates = [], onConflict } = options;

  return useMutation<TResult, unknown, VersionedMutationArgs<TBody>>({
    mutationFn: ({ entity, body }) =>
      request<TResult>(path(entity), {
        method,
        body,
        expectedVersion: entity.entity_version,
      }),
    onSuccess: () => {
      for (const key of invalidates) {
        void client.invalidateQueries({ queryKey: key });
      }
    },
    onError: (error, args) => {
      if (error instanceof EntityVersionConflictError) {
        // Refetch so the officer resolves against current state rather than the
        // stale copy that just lost.
        for (const key of invalidates) {
          void client.invalidateQueries({ queryKey: key });
        }
        onConflict?.(error, args);
      }
    },
  });
}
