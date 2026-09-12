/**
 * Azztec_SaaS_web_planner_DayCell_v1_0_0.tsx  ->  web/src/features/planner/DayCell.tsx
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §5.6 · OD-6
 * Oracle:   Planner_v1_8_1.html month cell (643-656), week cell (684-691), twoweek cell (703-711)
 *
 * One day. Two header shapes, exactly as the oracle has them:
 *   month          - `14` (or `1 Sep` on the 1st and on the first cell of the window) + countText
 *   week / twoweek - `MON 14 Sep` + countText + the `hh` line (`3.5 h planned \u00b7 1 without hours`)
 * and one list of chips. Month caps the list at four with a `+n more` toggle.
 *
 * The oracle kept expansion in a global S.expanded map keyed by date; here it is useState per cell,
 * which is the same behaviour with none of the cross-render bookkeeping. It resets when the window
 * changes, which is what the oracle's render() did anyway.
 *
 * `isToday` comes from the API's `today` (OD-6, server tz) - never from the browser clock. The cell
 * is a plain div: the day dialog (click `.d`) is S1g and the drop target is S2.
 *
 * Changelog:
 *   1.0.0  Initial S1f.
 */
import { useState } from 'react';

import { WOCard } from './WOCard';
import { DOW, MON, countText, fmtNum, whoFor, ymd } from './rules';
import type { Wo, Worker } from '../../api/client/types.gen';

export const VERSION = '1.0.0';

const MONTH_CAP = 4;

export type DayCellProps = {
  dateIso: string;
  /** 'month' draws the short header and caps the list; 'week' and 'twoweek' draw the hh line */
  mode: 'week' | 'twoweek' | 'month';
  /** 0-6 within the row, for the DOW label */
  col: number;
  list: ReadonlyArray<Wo>;
  isPast: boolean;
  isToday: boolean;
  /** month only: the day belongs to a neighbouring month */
  out: boolean;
  /** month only: this is the very first cell of the window, so the month name is shown */
  first: boolean;
  byId: ReadonlyMap<number, Worker>;
  selected: number;
  onSelect: (id: number) => void;
};

export function DayCell({
  dateIso,
  mode,
  col,
  list,
  isPast,
  isToday,
  out,
  first,
  byId,
  selected,
  onSelect,
}: DayCellProps) {
  const [expanded, setExpanded] = useState(false);
  const p = ymd(dateIso);
  const isMonth = mode === 'month';

  const cls =
    'cell' + (isPast ? ' past' : '') + (isToday ? ' today' : '') + (out ? ' out' : '') + (expanded ? ' x' : '');

  const dayLabel = isMonth
    ? `${p.d}${p.d === 1 || first ? ` ${MON[p.m - 1]}` : ''}`
    : `${DOW[col]} ${p.d} ${MON[p.m - 1]}`;

  let hrs = 0;
  let unk = 0;
  for (const w of list) {
    if (w.hrs > 0) hrs += w.hrs;
    else unk++;
  }
  const hh =
    (hrs > 0 ? `${fmtNum(hrs)} h planned` : '') + (unk > 0 ? `${hrs > 0 ? ' \u00b7 ' : ''}${unk} without hours` : '');

  const shown = isMonth && !expanded ? list.slice(0, MONTH_CAP) : list;

  return (
    <div className={cls} data-date={dateIso}>
      <div className="ch">
        <span className="d" data-day={dateIso}>
          {dayLabel}
        </span>
        <span className="c">{countText(list)}</span>
        {isMonth ? null : <span className="hh">{hh}</span>}
      </div>
      <div className="list">
        {shown.map((wo) => (
          <WOCard key={wo.id} wo={wo} who={whoFor(wo, byId)} selected={selected === wo.id} onSelect={onSelect} />
        ))}
      </div>
      {isMonth && list.length > MONTH_CAP ? (
        <div
          className="more"
          onClick={(ev) => {
            ev.stopPropagation();
            setExpanded((x) => !x);
          }}
        >
          {expanded ? 'show less' : `+${list.length - MONTH_CAP} more`}
        </div>
      ) : null}
    </div>
  );
}

export default DayCell;
