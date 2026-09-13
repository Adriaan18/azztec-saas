/**
 * Azztec_SaaS_web_planner_DayDialog_v1_1_0.tsx  ->  web/src/features/planner/DayDialog.tsx
 * Version:  1.1.0   Date: 2026-09-14   Author: Adriaan
 * Spec:     Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md §5.7 · OD-5, OD-31, OD-32, OD-34; S1i spec §3.3 · OD-41
 * Oracle:   Planner_v1_8_1.html showDay (715-739), .ovl / .dlg / .dd2 CSS (194, 267-272, 361-369)
 *
 * The day dialog: every visible WO on one day, one .job row each, opened from the day head in the
 * grid. A port of showDay, so it is a plain component with the oracle's CSS - OD-27/OD-31 say shadcn
 * is decided at the first component that is NOT a port, and this one is.
 *
 * The row strings come from rules.dialogRows(); the badge look from rules.priBadgeMap() - the OD-32 rank
 * class and, when the payload's colours carry information (OD-39), the same inline paint as the chip
 * (OD-41). This is the second badge site; the `.dd2 .job .pri` rule in planner.css is untouched.
 * Read-only: Select and Close work; `Plan hours` is absent (S4); `Open` is disabled with the OD-5
 * reason. Escape is not handled here - the dialog is store state (dayOpen), so PlannerView's document
 * handler closes it and can tell "dialog open" from "clear the selection".
 *
 * Changelog:
 *   1.1.0  S1i (OD-41): priRankMap -> priBadgeMap in the one useMemo; the badge span gains the inline
 *          backgroundColor/color pair when its entry has a bg. Class string unchanged. No new prop. The
 *          map callback becomes a block body (one lookup per row), which re-indents the row JSX by two
 *          spaces - the diff is wider than the change; every node and string inside it is 1.0.0's.
 *   1.0.0  Initial S1g.
 */
import { useMemo } from 'react';

import { countText, dialogRows, dialogTitle, priBadgeMap, priClass } from './rules';
import type { LabourRow, Priority, Wo, Worker } from '../../api/client/types.gen';

export const VERSION = '1.1.0';

/** OD-5: the handoff arrives with the WO module. */
export const OPEN_TITLE = 'arrives with the WO module (OD-5)';

export type DayDialogProps = {
  /** ISO key of the open day; '' renders nothing */
  dateIso: string;
  /** that day's WOs, already visible-filtered by the caller */
  list: ReadonlyArray<Wo>;
  labour: ReadonlyArray<LabourRow>;
  byId: ReadonlyMap<number, Worker>;
  priorities: ReadonlyArray<Priority>;
  /** sets the selection (the oracle assigns S.selected, it does not toggle) */
  onSelect: (id: number) => void;
  onClose: () => void;
};

export function DayDialog({ dateIso, list, labour, byId, priorities, onSelect, onClose }: DayDialogProps) {
  const badges = useMemo(() => priBadgeMap(priorities), [priorities]);
  if (!dateIso) return null;
  const rows = dialogRows(list, labour, byId);
  return (
    <div className="ovl on" data-day={dateIso}>
      <div className="dlg wide dd2" role="dialog" aria-label={dialogTitle(dateIso)}>
        <h2>
          {dialogTitle(dateIso)} <span>{countText(list) || 'nothing scheduled'}</span>
        </h2>
        {rows.length === 0 ? <div className="none">Nothing scheduled that day (with the current filters).</div> : null}
        {rows.map((r) => {
          const b = badges.get(r.priId);
          return (
            <div className="job" key={r.id} data-wo={r.id}>
              <div>
                <span className={`sid ${r.cat}`}>{r.sid}</span>
                {r.pri ? (
                  <span
                    className={`pri ${r.pri} ${priClass(b?.rank ?? 0)}`.trim()}
                    style={b?.bg ? { backgroundColor: b.bg, color: b.fg } : undefined}
                  >
                    {r.pri}
                  </span>
                ) : null}
                <div className="meta">{r.meta1}</div>
              </div>
              <div>
                {r.title}
                <div className="meta">{r.meta2}</div>
                <div className="meta">
                  {r.noHours ? <span className="none">{r.hours}</span> : r.hours} {'\u00b7'} {r.who}
                </div>
              </div>
              <div className="acts">
                <button
                  type="button"
                  onClick={() => {
                    onSelect(r.id);
                    onClose();
                  }}
                >
                  Select
                </button>
                <button type="button" className="gold" disabled title={OPEN_TITLE}>
                  Open
                </button>
              </div>
            </div>
          );
        })}
        <div className="btns">
          <button type="button" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default DayDialog;
