/**
 * api-client.ts — Centralized fetch wrapper for Terra.OS
 *
 * Features:
 *  - Auth header injection (Bearer token from localStorage or Zustand store)
 *  - Request deduplication: parallel identical GET requests collapse to one in-flight fetch
 *  - Typed API errors (ApiError with status, detail, etc.)
 *  - Automatic JSON parsing + error extraction
 *  - Abort controller support
 */

// ── Typed errors ────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly raw: unknown;

  constructor(status: number, detail: string, raw?: unknown) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.raw = raw;
  }
}

export class NetworkError extends Error {
  constructor(cause?: unknown) {
    super(cause instanceof Error ? cause.message : 'Network request failed');
    this.name = 'NetworkError';
  }
}

// ── Request deduplication ────────────────────────────────────────────────────

// Map of in-flight GET requests: url → Promise<unknown>
const inflight = new Map<string, Promise<unknown>>();

// ── Auth token helper ────────────────────────────────────────────────────────

/**
 * Retrieve the auth token. Tries Zustand store first (SSR-safe), falls back
 * to localStorage. Returns null if neither is available.
 */
function getAuthToken(): string | null {
  // Try Zustand store (if available in browser context)
  try {
    // Dynamic import to avoid circular deps — read state synchronously via getState()
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useStore } = require('@/store/useStore');
    const token = useStore.getState?.()?.accessToken;
    if (token) return token;
  } catch {
    // store not available (SSR or test env)
  }

  // Fallback: localStorage key used by the legacy auth flow
  if (typeof window !== 'undefined') {
    return localStorage.getItem('auth_token');
  }

  return null;
}

// ── Core request function ─────────────────────────────────────────────────────

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  /** Parsed JSON body — will be serialized to JSON and Content-Type set automatically */
  body?: unknown;
  /** If true, skip deduplication for this request (useful for mutations) */
  noDedup?: boolean;
  /** If provided, the request will be aborted when this signal fires */
  signal?: AbortSignal;
  /** Override base URL; defaults to process.env.NEXT_PUBLIC_API_URL or '' */
  baseUrl?: string;
}

export async function apiRequest<T = unknown>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const {
    method = 'GET',
    body,
    noDedup = false,
    signal,
    baseUrl = '',
    headers: extraHeaders = {},
    ...restInit
  } = options;

  const url = `${baseUrl}${path}`;
  const isWrite = method !== 'GET' && method !== 'HEAD';

  // Build headers
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(extraHeaders as Record<string, string>),
  };

  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const init: RequestInit = {
    method,
    headers,
    signal,
    ...restInit,
  };

  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }

  const doFetch = async (): Promise<T> => {
    let response: Response;
    try {
      response = await fetch(url, init);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') throw err;
      throw new NetworkError(err);
    }

    if (!response.ok) {
      let raw: unknown;
      try {
        raw = await response.json();
      } catch {
        raw = null;
      }

      const rawDetail = (raw as Record<string, unknown>)?.detail;
      const detail: string = Array.isArray(rawDetail)
        ? rawDetail
            .map((d: { msg?: string; loc?: string[] }) =>
              [d.loc?.slice(-1)[0], d.msg].filter(Boolean).join(': '),
            )
            .join('; ')
        : typeof rawDetail === 'string'
          ? rawDetail
          : `HTTP ${response.status}`;

      throw new ApiError(response.status, detail, raw);
    }

    // 204 No Content
    if (response.status === 204) return undefined as unknown as T;

    return response.json() as Promise<T>;
  };

  // Deduplicate parallel GET requests to the same URL
  if (!isWrite && !noDedup && !signal) {
    const existing = inflight.get(url);
    if (existing) return existing as Promise<T>;

    const promise = doFetch().finally(() => inflight.delete(url));
    inflight.set(url, promise);
    return promise;
  }

  return doFetch();
}

// ── Convenience helpers ──────────────────────────────────────────────────────

export const apiGet = <T = unknown>(path: string, opts?: Omit<ApiRequestOptions, 'method'>) =>
  apiRequest<T>(path, { ...opts, method: 'GET' });

export const apiPost = <T = unknown>(
  path: string,
  body?: unknown,
  opts?: Omit<ApiRequestOptions, 'method' | 'body'>,
) => apiRequest<T>(path, { ...opts, method: 'POST', body, noDedup: true });

export const apiPut = <T = unknown>(
  path: string,
  body?: unknown,
  opts?: Omit<ApiRequestOptions, 'method' | 'body'>,
) => apiRequest<T>(path, { ...opts, method: 'PUT', body, noDedup: true });

export const apiPatch = <T = unknown>(
  path: string,
  body?: unknown,
  opts?: Omit<ApiRequestOptions, 'method' | 'body'>,
) => apiRequest<T>(path, { ...opts, method: 'PATCH', body, noDedup: true });

export const apiDelete = <T = unknown>(path: string, opts?: Omit<ApiRequestOptions, 'method'>) =>
  apiRequest<T>(path, { ...opts, method: 'DELETE', noDedup: true });

// ── React hook wrapper ────────────────────────────────────────────────────────

/**
 * useApiClient — returns stable apiRequest bound to current auth token.
 * Refreshes token on each call (token is read lazily inside apiRequest),
 * so no stale-closure problems.
 *
 * Usage:
 *   const api = useApiClient();
 *   const data = await api.get<MyType>('/api/v2/...');
 */
export function useApiClient() {
  return {
    get: apiGet,
    post: apiPost,
    put: apiPut,
    patch: apiPatch,
    delete: apiDelete,
    request: apiRequest,
  };
}
