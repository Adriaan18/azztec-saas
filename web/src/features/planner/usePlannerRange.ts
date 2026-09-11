/**
 * Azztec_SaaS_web_usePlannerRange_v1_0_0.ts  ->  web/src/features/planner/usePlannerRange.ts
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1e_Web_Chunk_Spec_v1_0_0.md §6.2 · OD-22, OD-23 · Landmines §C
 * Consumes: src/api/client (generated 2026-09-12 from docs/api/openapi_0_3_0.json, openapi-ts 0.99.0):
 *           getRangeApiV1PlannerRangeGetOptions(), GetRangeApiV1PlannerRangeGetData, RangeData.
 *
 * GET /api/v1/planner/range behind a hard client-side window cap. The API serves up to 400 days
 * (21 MB on RST); the UI never asks for more than the oracle's widest window - Planner 1.8.1
 * windowFor('month') is at most 6 rows x 7 = 42 inclusive days. Refused windows never fetch:
 * the query is disabled, so the cap is enforced before the network, not after.
 *
 * The query key is whatever the @tanstack/react-query plugin generated - it carries the query
 * params, so ['planner','range',from,to] from Landmines §C is superseded (spec §12).
 *
 * Changelog:
 *   1.0.0  Initial S1e.
 */
import { useQuery } from '@tanstack/react-query';

import { getRangeApiV1PlannerRangeGetOptions } from '../../api/client/@tanstack/react-query.gen';
import { civilDays } from '../../lib/dates';

export const VERSION = '1.0.0';

/** OD-23. Inclusive days. The month view's worst case; the six-month view is out of S1 (spec §6.3). */
export const MAX_WINDOW_DAYS = 42;
/** Landmines §C: staleTime > 0 or every mount refetches. */
export const STALE_MS = 30_000;
/** Architecture §6: the 60 s planner poll. */
export const POLL_MS = 60_000;

export type WindowCode = 'BAD_WINDOW' | 'WINDOW_TOO_WIDE';

export type WindowCheck =
  | { ok: true; days: number }
  | { ok: false; code: WindowCode; message: string };

/**
 * Pure. BAD_WINDOW is the backend's own code for the same failure (service.WindowError, router 1.0.1),
 * so both layers name it identically; WINDOW_TOO_WIDE is client-only - the API would have said yes.
 */
export function checkWindow(from: string, to: string): WindowCheck {
  let span: number;
  try {
    span = civilDays(from, to);
  } catch (e) {
    return { ok: false, code: 'BAD_WINDOW', message: e instanceof Error ? e.message : String(e) };
  }
  if (span < 0) return { ok: false, code: 'BAD_WINDOW', message: `to ${to} is before from ${from}` };
  const days = span + 1;
  if (days > MAX_WINDOW_DAYS) {
    return { ok: false, code: 'WINDOW_TOO_WIDE', message: `${days} days exceeds MAX_WINDOW_DAYS ${MAX_WINDOW_DAYS} (OD-23)` };
  }
  return { ok: true, days };
}

/** The full options object useQuery receives. Exported so the cap and the poll settings are testable as data. */
export function plannerQueryOptions(from: string, to: string) {
  const check = checkWindow(from, to);
  return {
    ...getRangeApiV1PlannerRangeGetOptions({ query: { from, to } }),
    enabled: check.ok,
    staleTime: STALE_MS,
    refetchInterval: POLL_MS,
    refetchIntervalInBackground: false,
  };
}

/**
 * One error channel: `window` is the client-side verdict, `query` is TanStack Query's. When the window
 * is refused the query is disabled (fetchStatus 'idle', no request) and `window.ok` is false.
 */
export function usePlannerRange(from: string, to: string) {
  const window = checkWindow(from, to);
  const query = useQuery(plannerQueryOptions(from, to));
  return { query, window };
}
