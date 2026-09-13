/**
 * Azztec_SaaS_web_planner_store_v1_1_0.ts  ->  web/src/features/planner/store.ts
 * Version:  1.1.0   Date: 2026-09-13   Author: Adriaan
 * Spec:     Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md §5.2 · OD-26, OD-29 · Port Spec §7 (state)
 * Oracle:   Planner_v1_8_1.html S (492-496): cats, selected, railOpen, teamId, workers, pri, unassigned,
 *           q; select() 869; the filter setters 1533-1536; Clear 1537; showDay/closeDlg 715-739.
 *
 * Client state only (Port Spec §7: server state = TanStack Query, client state = Zustand). mode and
 * anchor are NOT here - they are the URL (OD-29). Nothing is persisted: the oracle's savePrefs to
 * localStorage is out (S1f spec §1). Server data never enters this store.
 *
 * Changelog:
 *   1.1.0  S1g. filters (teamId / workers / pri / unassigned / q) with the oracle's setters - setTeam
 *          clears the worker selection like 1533; clearFilters is 1537 exactly (filters, cats to
 *          default, selection off); dayOpen is the day dialog (ISO key, '' = closed); clearSelect
 *          because select() toggles and the grid-background click / Esc must not re-select.
 *   1.0.0  Initial S1f.
 */
import { create } from 'zustand';

import { DEFAULT_CATS, DEFAULT_FILTERS, DEFAULT_RAIL } from './rules';
import type { Cat, Cats, Filters } from './rules';

export const VERSION = '1.1.0';

export type PlannerState = {
  cats: Cats;
  /** selected WO id, 0 = none (the oracle's S.selected) */
  selected: number;
  railOpen: boolean;
  /** OD-26 */
  contractors: boolean;
  loadedOnly: boolean;
  /** S1g - the oracle's S.teamId / S.workers / S.pri / S.unassigned / S.q */
  filters: Filters;
  /** the day dialog: ISO key of the open day, '' when closed */
  dayOpen: string;

  toggleCat: (cat: Cat) => void;
  setAllCats: (on: boolean) => void;
  /** click again to clear, like the oracle's select() */
  select: (id: number) => void;
  /** always to 0 - never toggles */
  clearSelect: () => void;
  toggleRail: () => void;
  toggleContractors: () => void;
  toggleLoadedOnly: () => void;

  /** oracle 1533: a team change drops the worker selection */
  setTeam: (teamId: number) => void;
  toggleWorker: (id: number) => void;
  setPri: (pri: number) => void;
  setUnassigned: (on: boolean) => void;
  /** already trimmed by the caller (oracle 1536) */
  setQ: (q: string) => void;
  /** oracle 1537: filters off, cats to default, selection off */
  clearFilters: () => void;

  openDay: (key: string) => void;
  closeDay: () => void;
};

export const usePlannerStore = create<PlannerState>()((set) => ({
  cats: { ...DEFAULT_CATS },
  selected: 0,
  railOpen: true,
  contractors: DEFAULT_RAIL.contractors,
  loadedOnly: DEFAULT_RAIL.loadedOnly,
  filters: { ...DEFAULT_FILTERS },
  dayOpen: '',

  toggleCat: (cat) => set((s) => ({ cats: { ...s.cats, [cat]: !s.cats[cat] } })),
  setAllCats: (on) => set({ cats: { WO: on, PM: on, REQ: on, DONE: on } }),
  select: (id) => set((s) => ({ selected: s.selected === id ? 0 : id })),
  clearSelect: () => set({ selected: 0 }),
  toggleRail: () => set((s) => ({ railOpen: !s.railOpen })),
  toggleContractors: () => set((s) => ({ contractors: !s.contractors })),
  toggleLoadedOnly: () => set((s) => ({ loadedOnly: !s.loadedOnly })),

  setTeam: (teamId) => set((s) => ({ filters: { ...s.filters, teamId, workers: {} } })),
  toggleWorker: (id) =>
    set((s) => ({ filters: { ...s.filters, workers: { ...s.filters.workers, [id]: !s.filters.workers[id] } } })),
  setPri: (pri) => set((s) => ({ filters: { ...s.filters, pri } })),
  setUnassigned: (on) => set((s) => ({ filters: { ...s.filters, unassigned: on } })),
  setQ: (q) => set((s) => ({ filters: { ...s.filters, q } })),
  clearFilters: () => set({ filters: { ...DEFAULT_FILTERS }, cats: { ...DEFAULT_CATS }, selected: 0 }),

  openDay: (key) => set({ dayOpen: key }),
  closeDay: () => set({ dayOpen: '' }),
}));
