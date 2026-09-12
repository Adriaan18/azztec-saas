/**
 * Azztec_SaaS_web_planner_store_v1_0_0.ts  ->  web/src/features/planner/store.ts
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §5.3 · OD-26, OD-29 · Port Spec §7 (state)
 * Oracle:   Planner_v1_8_1.html S (492-496): cats, selected, railOpen; select() 869
 *
 * Client state only (Port Spec §7: server state = TanStack Query, client state = Zustand). mode and
 * anchor are NOT here - they are the URL (OD-29). Nothing is persisted: the oracle's savePrefs to
 * localStorage is out of S1f (spec §1). Server data never enters this store.
 *
 * Changelog:
 *   1.0.0  Initial S1f.
 */
import { create } from 'zustand';

import { DEFAULT_CATS, DEFAULT_RAIL } from './rules';
import type { Cat, Cats } from './rules';

export const VERSION = '1.0.0';

export type PlannerState = {
  cats: Cats;
  /** selected WO id, 0 = none (the oracle's S.selected) */
  selected: number;
  railOpen: boolean;
  /** OD-26 */
  contractors: boolean;
  loadedOnly: boolean;

  toggleCat: (cat: Cat) => void;
  setAllCats: (on: boolean) => void;
  /** click again to clear, like the oracle's select() */
  select: (id: number) => void;
  toggleRail: () => void;
  toggleContractors: () => void;
  toggleLoadedOnly: () => void;
};

export const usePlannerStore = create<PlannerState>()((set) => ({
  cats: { ...DEFAULT_CATS },
  selected: 0,
  railOpen: true,
  contractors: DEFAULT_RAIL.contractors,
  loadedOnly: DEFAULT_RAIL.loadedOnly,

  toggleCat: (cat) => set((s) => ({ cats: { ...s.cats, [cat]: !s.cats[cat] } })),
  setAllCats: (on) => set({ cats: { WO: on, PM: on, REQ: on, DONE: on } }),
  select: (id) => set((s) => ({ selected: s.selected === id ? 0 : id })),
  toggleRail: () => set((s) => ({ railOpen: !s.railOpen })),
  toggleContractors: () => set((s) => ({ contractors: !s.contractors })),
  toggleLoadedOnly: () => set((s) => ({ loadedOnly: !s.loadedOnly })),
}));
