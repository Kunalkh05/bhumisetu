/**
 * The API error envelope (design §9.4).
 *
 * Every non-2xx response carries a machine-readable `code` plus a `details`
 * object whose shape depends on the code. The UI branches on `code`, never on
 * the human-readable message.
 */
export interface ApiErrorEnvelope {
  readonly code: string;
  readonly message: string;
  readonly details?: Readonly<Record<string, unknown>>;
}

/** A conflicting attribute, as returned on ENTITY_VERSION_CONFLICT (R29.4). */
export interface ConflictingAttribute {
  readonly attribute: string;
  readonly submitted: unknown;
  readonly current: unknown;
}

/**
 * R29.4: the rejection names every differing attribute, the current stored
 * value of each, the actor whose modification produced the current version, and
 * when that modification occurred. All four are required to render a conflict
 * an officer can actually resolve.
 */
export interface EntityVersionConflictDetail {
  readonly entity_type: string;
  readonly entity_id: string;
  readonly current_version: number;
  readonly submitted_version: number;
  readonly conflicting_attributes: readonly ConflictingAttribute[];
  readonly competing_actor_id: string;
  readonly competing_occurrence_time: string;
  /** Present only for the Extracted_Field review path (R29.8). */
  readonly winning_review_state?: string;
  readonly winning_value?: string | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Readonly<Record<string, unknown>> | undefined;

  constructor(status: number, envelope: ApiErrorEnvelope) {
    super(envelope.message);
    this.name = 'ApiError';
    this.status = status;
    this.code = envelope.code;
    this.details = envelope.details;
  }
}

export class EntityVersionConflictError extends ApiError {
  readonly conflict: EntityVersionConflictDetail;

  constructor(status: number, envelope: ApiErrorEnvelope) {
    super(status, envelope);
    this.name = 'EntityVersionConflictError';
    this.conflict = envelope.details as unknown as EntityVersionConflictDetail;
  }
}

/**
 * R28.5: a missing Policy_Config value refuses the dependent operation and
 * returns the key and date rather than substituting a default. Surfaced as its
 * own type because the remedy is configuration, not a retry — and until Q8 is
 * confirmed and periods are seeded, this is an expected response rather than a
 * fault.
 */
export class PolicyValueMissingError extends ApiError {
  constructor(status: number, envelope: ApiErrorEnvelope) {
    super(status, envelope);
    this.name = 'PolicyValueMissingError';
  }
}

export function isConflict(error: unknown): error is EntityVersionConflictError {
  return error instanceof EntityVersionConflictError;
}

export function isPolicyValueMissing(error: unknown): error is PolicyValueMissingError {
  return error instanceof PolicyValueMissingError;
}
