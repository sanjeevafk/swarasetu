/**
 * Typed fetch client for the SwaraSetu FastAPI backend.
 * In dev, Vite proxies /api -> http://localhost:8000 (see vite.config.ts).
 */

import type {
  AnalyticsSummary,
  PHCNearby,
  SyncCaseItem,
  SyncResponse,
  TriageEvaluateRequest,
  TriageEvaluateResponse,
} from '@/types/api';

const DEFAULT_TIMEOUT_MS = 6000;

export class ApiUnreachableError extends Error {
  constructor(cause?: unknown) {
    super('Backend unreachable');
    this.name = 'ApiUnreachableError';
    this.cause = cause;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
  try {
    const res = await fetch(path, {
      ...init,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    });
    if (!res.ok) {
      throw new Error(`API ${res.status}: ${await res.text()}`);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof TypeError || (err instanceof DOMException && err.name === 'AbortError')) {
      throw new ApiUnreachableError(err);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  health(): Promise<{ status: string }> {
    return request('/health');
  },

  evaluateTriage(body: TriageEvaluateRequest): Promise<TriageEvaluateResponse> {
    return request('/api/v1/triage/evaluate', { method: 'POST', body: JSON.stringify(body) });
  },

  nearestPhcs(lat: number, lon: number, limit = 5): Promise<PHCNearby[]> {
    return request(`/api/v1/phcs/nearest?lat=${lat}&lon=${lon}&limit=${limit}`);
  },

  analyticsSummary(): Promise<AnalyticsSummary> {
    return request('/api/v1/analytics/summary');
  },

  syncCases(items: SyncCaseItem[]): Promise<SyncResponse> {
    return request('/api/v1/sync/cases', { method: 'POST', body: JSON.stringify(items) });
  },
};
