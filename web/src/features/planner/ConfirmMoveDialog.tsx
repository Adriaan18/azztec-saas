/**
 * Azztec_SaaS_web_planner_ConfirmMoveDialog_v1_0_0.tsx  ->  web/src/features/planner/ConfirmMoveDialog.tsx
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (ConfirmMoveDialog.tsx row) · OD-113, OD-116
 * Oracle:   Planner_v1_8_1.html showConfirm, closeDlg, wire (a click on the overlay itself closes it)
 *
 * The confirm the server asks for (CONFIRM, a 200 with ok:false and a preview - OD-112): `MOVE X?`, the
 * old day -> the new one in bold with the delta, title · status, every reason the server gave (SPAN
 * included - it is shown, never asked on its own, OD-116), the planned-labour moves, the subtask count,
 * Cancel / Move it. Move it takes the focus, as the oracle's did, so Enter moves; the document-level
 * Enter and Escape live in PlannerView with the rest of the keyboard.
 *
 * Same overlay and dialog classes as the day dialog (.ovl absolute inside .wm-planner, OD-54); renders
 * nothing when there is no preview.
 *
 * Changelog:
 *   1.0.0  Initial DP3b.
 */
import { fmtDelta } from './moves';
import { fmtLongAny } from './rules';
import type { MovePreview } from '../../api/client/types.gen';

export const VERSION = '1.0.0';

export type ConfirmMoveDialogProps = {
  /** the CONFIRM's preview; null renders nothing */
  preview: MovePreview | null;
  onYes: () => void;
  onNo: () => void;
};

/** A day the dialog names; '?' rather than a broken date if the server ever sends none. */
function dayName(iso: string): string {
  return iso ? fmtLongAny(iso) : '?';
}

/** `3 rows`, `1 row` - the oracle's labour-move and subtask plurals. */
export function rows(n: number, noun: string): string {
  return `${n} ${noun}${n === 1 ? '' : 's'}`;
}

export function ConfirmMoveDialog({ preview, onYes, onNo }: ConfirmMoveDialogProps) {
  if (!preview) return null;
  const title = `MOVE ${preview.sid}?`;
  return (
    <div
      className="ovl on"
      data-confirm={preview.woId}
      onClick={(ev) => {
        if (ev.target === ev.currentTarget) onNo();
      }}
    >
      <div className="dlg" role="dialog" aria-label={title}>
        <h2>{title}</h2>
        <div className="mv">
          {dayName(preview.prevStart)} {'→'} <b>{dayName(preview.newStart)}</b>{' '}
          <span className="sub">({fmtDelta(preview.delta)})</span>
        </div>
        <div className="sub">
          {preview.title} {'·'} {preview.statusTitle}
        </div>
        <ul className="why">
          {preview.reasons.map((r) => (
            <li key={r.code}>{r.text}</li>
          ))}
        </ul>
        {preview.labourMoves.length ? (
          <>
            <div className="sub">Planned labour:</div>
            <ul className="lm">
              {preview.labourMoves.map((m) => (
                <li key={`${m.from}>${m.to}`}>
                  {m.from} {'→'} {m.to} ({rows(m.rows, 'row')})
                </li>
              ))}
            </ul>
          </>
        ) : null}
        {preview.subtasks ? <div className="sub">{rows(preview.subtasks, 'subtask row')} move too.</div> : null}
        <div className="btns">
          <button type="button" onClick={onNo}>
            Cancel
          </button>
          <button type="button" className="gold" onClick={onYes} autoFocus>
            Move it
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmMoveDialog;
