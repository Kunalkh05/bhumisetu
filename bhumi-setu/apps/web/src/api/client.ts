import {
  ApiError,
  EntityVersionConflictError,
  PolicyValueMissingError,
  type ApiErrorEnvelope,
} from './errors';

/**
 * The single seam between the officer portal and its data source.
 *
 * Every request in the app goes through `request()`. Pointing the portal at a
 * mock instead of a live API is a change to `baseUrl` or to this module's fetch
 * implementation, and nothing above it needs to know which it is talking to.
 */
export interface RequestOptions {
  readonly method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  readonly body?: unknown;
  /**
   * Entity_Version observed when the entity was read (R29.2). Sent as If-Match
   * so the conditional UPDATE in design §7.1 can reject a stale write. Every
   * mutation against a versioned entity must supply it.
   */
  readonly expectedVersion?: number;
  readonly signal?: AbortSignal;
}

const baseUrl = (import.meta.env['VITE_API_URL'] as string | undefined) ?? '/api/officer';

function envelopeFrom(status: number, payload: unknown): ApiErrorEnvelope {
  if (
    typeof payload === 'object' &&
    payload !== null &&
    'code' in payload &&
    typeof (payload as { code: unknown }).code === 'string'
  ) {
    return payload as ApiErrorEnvelope;
  }
  // A response that is not an envelope is itself a defect; surface it as one
  // rather than pretending it parsed.
  return { code: `HTTP_${status}`, message: `Unenveloped ${status} response` };
}

function raise(status: number, envelope: ApiErrorEnvelope): never {
  switch (envelope.code) {
    case 'ENTITY_VERSION_CONFLICT':
      throw new EntityVersionConflictError(status, envelope);
    case 'POLICY_VALUE_MISSING':
      throw new PolicyValueMissingError(status, envelope);
    default:
      throw new ApiError(status, envelope);
  }
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, expectedVersion, signal } = options;

  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (expectedVersion !== undefined) {
    headers['If-Match'] = String(expectedVersion);
  }

  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers,
    // Officer sessions are opaque tokens in an HttpOnly cookie (design §3.4),
    // so the cookie has to ride along and there is no token to attach here.
    credentials: 'same-origin',
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    ...(signal ? { signal } : {}),
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    raise(response.status, envelopeFrom(response.status, payload));
  }

  return payload as T;
}
