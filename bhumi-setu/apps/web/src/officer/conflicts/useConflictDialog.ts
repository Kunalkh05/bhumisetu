import { useCallback, useState } from 'react';
import type { EntityVersionConflictDetail } from '../../api/errors';
import type { Versioned } from '../../api/hooks/useVersionedMutation';

interface ConflictState<TBody> {
  readonly conflict: EntityVersionConflictDetail;
  readonly body: TBody;
}

export function useConflictDialog<TBody>(
  resubmit: (args: { entity: Versioned; body: TBody }) => void,
) {
  const [state, setState] = useState<ConflictState<TBody> | null>(null);

  const onConflict = useCallback(
    (error: { conflict: EntityVersionConflictDetail }, args: { body: TBody }) => {
      setState({ conflict: error.conflict, body: args.body });
    },
    [],
  );

  const close = useCallback(() => setState(null), []);

  const resubmitWithCurrentVersion = useCallback(
    (currentVersion: number) => {
      if (!state) {
        return;
      }
      resubmit({
        entity: {
          id: state.conflict.entity_id,
          entity_version: currentVersion,
        },
        body: state.body,
      });
      setState(null);
    },
    [resubmit, state],
  );

  return {
    conflict: state?.conflict ?? null,
    onConflict,
    close,
    resubmitWithCurrentVersion,
  };
}
