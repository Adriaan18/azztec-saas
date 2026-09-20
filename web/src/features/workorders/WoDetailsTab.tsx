/**
 * Azztec_SaaS_web_workorders_WoDetailsTab_v1_0_0.tsx  ->  web/src/features/workorders/WoDetailsTab.tsx
 * Version:  1.0.0   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §3.10 · OD-51, OD-76
 * Oracle:   WOMaint_v16_28_3 DetailsSubTab - ThreeColRow (wrap, gap 20), then NotesSection
 *           (marginTop 8, txtNotes 1px solid #C8CECE, radius 4, 11px, minHeight 60, width 100%).
 *
 * A map over three tables in rules.ts, not thirty hand-written fields - so the Details tab becomes
 * the edit surface in W2/W3 by changing what the map renders, once, rather than in thirty places.
 *
 * Two oracle facts kept deliberately: lblDeptDesc and lblClassDesc carry NO binding in the export
 * (dead labels), so Dept. and Class show the resolved title alone and no small id beside it; and
 * the Created By row pairs with the LOGGED date, not a separate create stamp - the oracle binds
 * Logged_Date there. Both are in rules.ts with the same note.
 *
 * Changelog:
 *   1.0.0  Initial W1b.
 */
import type { WoRecord } from '../../api/client';
import { detailLeft, detailMiddle, detailStamps } from './rules';
import type { FieldRow } from './rules';

export const VERSION = '1.0.0';

function Row({ row }: { row: FieldRow }) {
  return (
    <div className="wo-frow">
      <span className="wo-flabel">{row.label}</span>
      <span className="wo-val ro">{row.value}</span>
      {row.desc === undefined ? null : <span className="wo-desc">{row.desc}</span>}
    </div>
  );
}

export function WoDetailsTab({ record }: { record: WoRecord }) {
  return (
    <div className="wo-tabbody">
      <div className="wo-details">
        <div className="wo-col-left">
          {detailLeft(record).map((r) => (
            <Row key={r.label} row={r} />
          ))}
        </div>

        <div className="wo-col-mid">
          {detailMiddle(record).map((r) => (
            <Row key={r.label} row={r} />
          ))}
        </div>

        <div className="wo-col-right">
          {detailStamps(record).map((s) => (
            <div className="wo-frow" key={s.label}>
              <span className="wo-flabel">{s.label}</span>
              <span className="wo-val ro">{s.user}</span>
              <span className="wo-val ro">{s.date}</span>
            </div>
          ))}
        </div>
      </div>

      <label className="wo-cardtitle" htmlFor="wo-notes">
        Notes
      </label>
      <textarea
        aria-describedby="wo-notes-hint"
        className="wo-notes"
        id="wo-notes"
        readOnly
        title="editing notes arrives with the write slice (OD-51)"
        value={record.notes}
      />
      <span className="wo-desc" id="wo-notes-hint">
        Read only - editing arrives with the write slice (OD-51).
      </span>
    </div>
  );
}
