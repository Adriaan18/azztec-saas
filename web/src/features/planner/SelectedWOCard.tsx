/**
 * Azztec_SaaS_web_planner_SelectedWOCard_v1_1_0.tsx  ->  web/src/features/planner/SelectedWOCard.tsx
 * Version:  1.1.0   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md §5.6 · OD-5, OD-34
 *           W1b: Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §3.13 - OD-5 CLOSED
 * Oracle:   Planner_v1_8_1.html renderSelected (801-836)
 *
 * The SELECTED WO card under the workers rail. The strings come from rules.cardRows() so they are
 * pinned there; this file only places them in the oracle's markup (.card.selc > h3 + .t + .kv + the
 * PLANNED LABOUR list + .actions).
 *
 * Read-only, by the audit (OD-34): no `+ person`, no `x` on a labour row, no Unpin, no assistant orb -
 * those are S4 / S3 / S5b affordances and are absent, not disabled.
 *
 * `Open in WO Maintenance` was that one disabled control, greyed since S1g because OD-5's route did
 * not exist. W1b built it, so the button is now a Link to /workorders/$id and OD-5 is closed. It is
 * a <Link>, not a button with a navigate() handler: middle-click and Ctrl-click open a work order in
 * a new tab, which is what a planner user does all day.
 *
 * Changelog:
 *   1.1.0  W1b: the Open button is live - Link to /workorders/$id. OPEN_TITLE is gone with the
 *          disabled state that needed it; the card is otherwise untouched.
 *   1.0.0  Initial S1g.
 */
import { Link } from '@tanstack/react-router';

import { cardRows } from './rules';
import type { LabourRow, Wo, Worker } from '../../api/client/types.gen';

export const VERSION = '1.1.0';

export type SelectedWOCardProps = {
  wo: Wo | null;
  labour: ReadonlyArray<LabourRow>;
  byId: ReadonlyMap<number, Worker>;
  onClear: () => void;
};

export function SelectedWOCard({ wo, labour, byId, onClear }: SelectedWOCardProps) {
  if (!wo) {
    return (
      <div className="card selc" data-wo="0">
        <h3>SELECTED WO</h3>
        <div className="empty">Click a work order.</div>
      </div>
    );
  }
  const c = cardRows(wo, labour, byId);
  return (
    <div className="card selc" data-wo={wo.id}>
      <h3>
        SELECTED WO <span className={`badge ${wo.cat}`}>{wo.cat}</span>
      </h3>
      <div className="t">
        {wo.sid} {'\u00b7'} {wo.title}
      </div>
      <div className="kv">
        <span className="k">Status</span>
        <span className="v" data-k="status">
          {c.status}
        </span>
        {c.pin ? (
          <>
            <span className="k">Pin</span>
            <span className="v" data-k="pin">
              {c.pin}
            </span>
          </>
        ) : null}
        <span className="k">Start</span>
        <span className="v" data-k="start">
          {c.start}
        </span>
        {c.end ? (
          <>
            <span className="k">End</span>
            <span className="v" data-k="end">
              {c.end}
            </span>
          </>
        ) : null}
        <span className="k">Priority</span>
        <span className="v" data-k="priority">
          {c.priority}
        </span>
        {c.asset ? (
          <>
            <span className="k">Asset</span>
            <span className="v" data-k="asset" title={c.assetTitle}>
              {c.asset}
            </span>
          </>
        ) : null}
        {c.loc ? (
          <>
            <span className="k">Location</span>
            <span className="v" data-k="location" title={c.locTitle}>
              {c.loc}
            </span>
          </>
        ) : null}
        <span className="k">Hours</span>
        <span className="v" data-k="hours">
          {c.hours ? (
            <>
              {c.hours} <small>({c.hoursSrc})</small>
            </>
          ) : (
            <span className="none">no estimate yet</span>
          )}
        </span>
        <span className="k">Responsible</span>
        <span className="v" data-k="responsible">
          {c.responsible ? (
            <>
              {c.responsible} <small>(WO owner - not planned hours)</small>
            </>
          ) : (
            <span className="nobody">nobody</span>
          )}
        </span>
      </div>
      <div className="sub">PLANNED LABOUR</div>
      {c.labour.length > 0 ? (
        c.labour.map((r, i) => (
          <div className="lab" key={i}>
            <span>
              {r.name}
              {r.skillTitle ? <small> {r.skillTitle}</small> : null}
            </span>
            <span>
              {r.hours}
              {r.date ? ` \u00b7 ${r.date}` : ''}
            </span>
          </div>
        ))
      ) : (
        <div className="empty">nobody planned yet</div>
      )}
      <div className="actions">
        <Link
          className="gold"
          data-open-wo={wo.id}
          params={{ id: String(wo.id) }}
          to="/workorders/$id"
        >
          Open in WO Maintenance
        </Link>
        <button type="button" onClick={onClear}>
          Clear
        </button>
      </div>
    </div>
  );
}

export default SelectedWOCard;
