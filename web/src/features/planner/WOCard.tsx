/**
 * Azztec_SaaS_web_planner_WOCard_v1_0_1.tsx  ->  web/src/features/planner/WOCard.tsx
 * Version:  1.0.1   Date: 2026-09-13   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §5.5 · OD-1; S1g spec §5.8 · OD-32, OD-33
 * Oracle:   Planner_v1_8_1.html chipEl (585-616), LOCK_SVG / PIN_SVG (486-487)
 *
 * One WO chip. The class string, the data attributes and the child order are the oracle's on purpose:
 * S2 (dnd-kit) and S6 (Playwright) key on `data-wo` / `data-movable`, and the screenshot smoke is held
 * next to the live Ignition planner.
 *
 * S1f is read-only, so of the oracle's three click paths only select() is wired: the .hrs estimate
 * popover and the dblclick openWO are S1g/S2. The chip stays a <div>, not a <button>, because S2 makes
 * it a drag handle - a button swallows pointer events and fires on space/enter mid-drag.
 *
 * The glyphs are the oracle's inline SVGs, 9x11 and 10x11, with their aria-labels. No icon library is
 * installed for two 40-byte paths (spec §1).
 *
 * Changelog:
 *   1.0.1  S1g: optional priRank prop (OD-32) - the badge gains `r1`..`r4` from rules.priClass beside the
 *          oracle's letter class, so RST's P1 lights up and KT's A-D keep their rules. Default 0 = no
 *          rank class, byte-identical to 1.0.0. The title is still chipTitle(wo), unchanged (OD-33).
 *   1.0.0  Initial S1f.
 */
import { chipTitle, fmtH, priClass } from './rules';
import type { Wo } from '../../api/client/types.gen';

export const VERSION = '1.0.1';

/** Oracle LOCK_SVG (486): engine-owned, no pin table - the RST state, 2,364 times (OD-1). */
function LockGlyph() {
  return (
    <svg className="lk" viewBox="0 0 9 11" aria-label="engine owned">
      <path d="M2 5V3.5a2.5 2.5 0 0 1 5 0V5" fill="none" stroke="currentColor" strokeWidth="1.2" />
      <rect x="1" y="5" width="7" height="5.5" rx="1" fill="currentColor" />
    </svg>
  );
}

/** Oracle PIN_SVG (487): pinned by the planner, the release engine leaves it alone. */
function PinGlyph() {
  return (
    <svg className="pn" viewBox="0 0 10 11" aria-label="pinned by planner">
      <path d="M3 1h4v1L6 3v2.5l2 1.5v1H2V7l2-1.5V3L3 2z" fill="currentColor" />
      <path d="M5 8v3" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

export type WOCardProps = {
  wo: Wo;
  /** initials from rules.whoFor(), computed once per render by the grid - never per chip */
  who: string;
  selected: boolean;
  onSelect: (id: number) => void;
  /** 1-based rank of wo.priId in priorities[] (rules.priRankMap), 0 = none - OD-32 */
  priRank?: number;
};

export function WOCard({ wo, who, selected, onSelect, priRank = 0 }: WOCardProps) {
  const rank = priClass(priRank);
  const cls =
    `chip cat-${wo.cat}` + (wo.locked ? ' locked' : '') + (wo.movable ? ' mv' : '') + (selected ? ' sel' : '');
  return (
    <div
      className={cls}
      data-wo={wo.id}
      data-movable={wo.movable ? '1' : '0'}
      title={chipTitle(wo)}
      onClick={(ev) => {
        ev.stopPropagation();
        onSelect(wo.id);
      }}
    >
      {wo.pri ? <span className={rank ? `pri ${wo.pri} ${rank}` : `pri ${wo.pri}`}>{wo.pri}</span> : null}
      <span className="sid">{wo.sid}</span>
      <span className={wo.hrs > 0 ? 'hrs' : 'hrs unk'}>{fmtH(wo.hrs)}</span>
      {who ? <span className="who">{who}</span> : null}
      {wo.pinned ? <PinGlyph /> : wo.locked ? <LockGlyph /> : null}
    </div>
  );
}

export default WOCard;
