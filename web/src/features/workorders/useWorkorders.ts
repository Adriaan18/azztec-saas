/**
 * Azztec_SaaS_web_workorders_useWorkorders_v1_0_0.ts  ->  web/src/features/workorders/useWorkorders.ts
 * Version:  1.0.0   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §3.6 · OD-73, OD-77, OD-78 · Landmines §C
 * Consumes: src/api/client (generated 2026-09-19 from docs/api/openapi_0_5_0.json):
 *           listWorkordersApiV1WorkordersGetOptions(), getWorkorderApiV1WorkordersWoIdGetOptions().
 *
 * Two hooks, no poll: a WO list is not the planner - nothing repaints it behind the user's back,
 * so staleTime 30s and refetch on filter change only (the planner's 60s poll stays the planner's,
 * OD-59 volume rule untouched). The search term is debounced 300ms and gated at two characters
 * (OD-78, item 53's page-side answer): the leading-wildcard LIKE stays exactly the oracle's query,
 * the page just asks less often. The record query is disabled at woId 0 - no request, not a 404.
 *
 * The query keys are whatever the @tanstack plugin generated - they carry the query params, so
 * two different filter sets are two cache entries and Load more (OD-77) appends by offset.
 *
 * Changelog:
 *   1.0.0  Initial W1b.
 */
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import {
  getWorkorderApiV1WorkordersWoIdGetOptions,
  listWorkordersApiV1WorkordersGetOptions,
} from '../../api/client/@tanstack/react-query.gen';

export const VERSION = '1.0.0';

/** Landmines §C: staleTime > 0 or every mount refetches. */
export const STALE_MS = 30_000;
/** OD-78. */
export const SEARCH_DEBOUNCE_MS = 300;
export const SEARCH_MIN_CHARS = 2;
/** OD-77: the page size the footer's `200+` is honest about. */
export const PAGE_SIZE = 200;

/** Pure. The two-character gate: a shorter term is the empty search, never a one-letter LIKE scan. */
export function settleSearch(raw: string): string {
  const t = raw.trim();
  return t.length >= SEARCH_MIN_CHARS ? t : '';
}

/** Generic debounce: returns `value` after it has held still for `ms`. First render is immediate. */
export function useDebouncedValue<T>(value: T, ms: number): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setSettled(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return settled;
}

export interface WoListFilters {
  woType: '' | 'N' | 'CP' | 'M';
  includeClosed: 0 | 1 | 2;
  includeArchive: 0 | 1 | 2;
  search: string;
  limit: number;
  offset: number;
}

/** The full options object useQuery receives - exported so the wire shape is testable as data. */
export function woListQueryOptions(f: WoListFilters) {
  return {
    ...listWorkordersApiV1WorkordersGetOptions({
      query: {
        woType: f.woType,
        includeClosed: f.includeClosed,
        includeArchive: f.includeArchive,
        search: f.search,
        limit: f.limit,
        offset: f.offset,
      },
    }),
    staleTime: STALE_MS,
  };
}

/**
 * The list. `search` arrives RAW from the input - the gate and the debounce live here, so every
 * caller gets the same manners. The settled term is what goes on the wire.
 */
export function useWoList(f: WoListFilters) {
  const settled = settleSearch(f.search);
  const search = useDebouncedValue(settled, SEARCH_DEBOUNCE_MS);
  return useQuery(woListQueryOptions({ ...f, search }));
}

export function woRecordQueryOptions(woId: number) {
  return {
    ...getWorkorderApiV1WorkordersWoIdGetOptions({ path: { wo_id: woId } }),
    staleTime: STALE_MS,
    enabled: woId > 0,
  };
}

/** The 23-join record. Disabled at 0 - the empty state renders without a request. */
export function useWoRecord(woId: number) {
  return useQuery(woRecordQueryOptions(woId));
}
