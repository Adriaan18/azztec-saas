/**
 * Azztec_SaaS_web_planner_moves_v1_0_1.ts  ->  web/src/features/planner/moves.ts
 * Version:  1.0.1   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (moves.ts row) · OD-107, OD-112, OD-113,
 *           OD-114, OD-116
 * Oracle:   Planner_v1_8_1.html whyNotMovable, applyMoveLocally, doMove (the toast and its pin note),
 *           undoLast (the move branch), handleWriteError, post
 * Consumes: src/api/client (generated from docs/api/openapi_0_7_0.json): postMoveApiV1PlannerMovePost,
 *           postUndoApiV1PlannerUndoPost, MoveResult, MoveConfirm, MovePreview, UndoRef, RangeData, Wo.
 *
 * The two writes the planner makes and everything pure around them. No React, no store: PlannerView
 * owns the flow (busy, the confirm, the toast, the undo stack) and calls in here for the wire and the
 * words, so the strings and the outcome map test with plain objects.
 *
 * outcomeOf is the oracle's handleWriteError as data. CONFIRM is a 200 with ok:false (OD-112), so the
 * client discriminates on `ok` and `code`, never on the status alone. The six kinds are what the view
 * does next: apply, ask, toast and refetch, banner, toast, toast. A network failure never throws - the
 * generated client returns it as an error with no response, and anything thrown is caught here too.
 *
 * Departures from the oracle, both OD-113 or OD-116:
 *   - movedToast adds `· ends <day>` when the move carried a SPAN reason - the move no longer asks
 *     about the end landing later (OD-116), so the toast says where it landed.
 *   - the undo stack is capped here (pushUndo) and kept in the store; a refused undo is dropped by the
 *     caller rather than pushed back (PlannerView), which is why `refused` and `stale` are kinds of
 *     their own and not folded into `failed`.
 *
 * Changelog:
 *   1.0.1  Lint fix before the tag (Block 1): loose() returned `v as Loose`, but the narrowed `object` is
 *          already a Loose, so @typescript-eslint/no-unnecessary-type-assertion refused it. The cast is gone;
 *          nothing behaves differently.
 *   1.0.0  Initial DP3b.
 */
import { postMoveApiV1PlannerMovePost, postUndoApiV1PlannerUndoPost } from '../../api/client/sdk.gen';
import type { MovePreview, MoveResult, RangeData, UndoRef, Wo } from '../../api/client/types.gen';
import { fmtLongAny } from './rules';

export const VERSION = '1.0.1';

/** Oracle doMove: S.undo keeps the last ten. */
export const UNDO_MAX = 10;
/** Oracle toast(): 4 s by default. */
export const TOAST_MS = 4000;
/** Oracle doMove: the Undo toast stays 6.5 s. */
export const UNDO_TOAST_MS = 6500;

/** No response at all - the generated client returns the fetch failure as an error without one. */
export const NETWORK_MESSAGE =
  'The planner service did not answer - check the connection; the planner refreshes to show where things are';

export type MoveBody = {
  woId: number;
  toIso: string;
  /** the WO's start as this planner last saw it - the server's STALE check (oracle doMove) */
  expectStartIso: string;
  confirm: boolean;
};

export type Outcome =
  | { kind: 'ok'; result: MoveResult }
  | { kind: 'confirm'; message: string; preview: MovePreview }
  | { kind: 'stale'; code: string; message: string; currentStart: string }
  | { kind: 'identity'; code: string; message: string }
  | { kind: 'refused'; code: string; message: string }
  | { kind: 'failed'; code: string; message: string };

type Loose = {
  ok?: unknown;
  code?: unknown;
  message?: unknown;
  preview?: unknown;
  currentStart?: unknown;
};

function loose(v: unknown): Loose {
  return typeof v === 'object' && v !== null ? v : {};
}

function text(v: unknown): string {
  return typeof v === 'string' ? v : '';
}

/**
 * Oracle handleWriteError, as a value. `status` 0 means no response. The body is whatever the client
 * parsed: MoveResult or MoveConfirm on a 200, the flat OD-15 error (plus sid / currentStart) otherwise.
 */
export function outcomeOf(status: number, body: unknown): Outcome {
  const b = loose(body);
  const code = text(b.code);
  const message = text(b.message) || (status ? `HTTP ${status}` : NETWORK_MESSAGE);
  if (status === 0) return { kind: 'failed', code: 'NETWORK', message: NETWORK_MESSAGE };
  if (status === 200 && b.ok === true) return { kind: 'ok', result: body as MoveResult };
  if (status === 200 && code === 'CONFIRM' && typeof b.preview === 'object' && b.preview !== null) {
    return { kind: 'confirm', message, preview: b.preview as MovePreview };
  }
  if (status === 200) return { kind: 'failed', code: code || 'BAD_RESPONSE', message };
  if (code === 'STALE') return { kind: 'stale', code, message, currentStart: text(b.currentStart) };
  if (status === 401 || code === 'NO_IDENTITY' || code === 'NO_RIGHT') {
    return { kind: 'identity', code: code || 'NO_SESSION', message };
  }
  if (status === 400 || status === 404 || status === 422) return { kind: 'refused', code, message };
  return { kind: 'failed', code: code || `HTTP_${status}`, message };
}

/** The HTTP status, or 0 when the client returned no response (a network failure). */
function statusOf(response: Response | undefined): number {
  return response ? response.status : 0;
}

/** POST /api/v1/planner/move. Never throws; the API's body default dryRun:false is the real move (OD-111). */
export async function postMove(body: MoveBody): Promise<Outcome> {
  try {
    const r = await postMoveApiV1PlannerMovePost({ body });
    return outcomeOf(statusOf(r.response), r.data ?? r.error);
  } catch {
    return outcomeOf(0, null);
  }
}

/** POST /api/v1/planner/undo with the `undo` dict the move returned. Never throws. */
export async function postUndo(u: UndoRef): Promise<Outcome> {
  try {
    const r = await postUndoApiV1PlannerUndoPost({
      body: { woId: u.woId, toIso: u.toIso, expectStartIso: u.expectStartIso },
    });
    return outcomeOf(statusOf(r.response), r.data ?? r.error);
  } catch {
    return outcomeOf(0, null);
  }
}

/** Oracle whyNotMovable, byte for byte: the toast a not-movable chip gets when it is dragged. */
export function whyNotMovable(wo: Wo): string {
  if (wo.status === 'C' || wo.status === 'D') return `${wo.sid} is ${wo.statusTitle.toLowerCase()} - it does not move`;
  if (wo.locked) return `${wo.sid} is a PM the release engine owns - run the S3 DDL (WO_N_Plan) to allow planner pins`;
  return `${wo.sid} cannot be moved`;
}

/** `+7 d`, `-1 d` - the oracle's delta spelling in the toast and the confirm. */
export function fmtDelta(delta: number): string {
  return `${delta > 0 ? '+' : ''}${delta} d`;
}

/** Oracle doMove's pin note; '' when the move did not touch a pin. */
export function pinNote(r: Pick<MoveResult, 'willPin' | 'willUnpin' | 'pinned'>): string {
  if (r.willPin) return ' · pinned (engine leaves it)';
  if (r.willUnpin) return ' · back on the engine date, pin cleared';
  return r.pinned ? ' · still pinned' : '';
}

/** OD-116: a SPAN move went through without asking, so the toast says where the end landed. */
export function endNote(r: Pick<MoveResult, 'reasons' | 'newEnd'>): string {
  return r.newEnd && r.reasons.some((x) => x.code === 'SPAN') ? ` · ends ${fmtLongAny(r.newEnd)}` : '';
}

/** Oracle doMove: `Moved WO-1 → Tue 29 Dec 2026 (+7 d)`, then the end note (OD-116) and the pin note. */
export function movedToast(r: MoveResult): string {
  return `Moved ${r.sid} → ${fmtLongAny(r.newStart)} (${fmtDelta(r.delta)})${endNote(r)}${pinNote(r)}`;
}

/** Oracle undoLast: `Undone: WO-1 back on Tue 22 Dec 2026`. */
export function undoneToast(r: MoveResult): string {
  return `Undone: ${r.sid} back on ${fmtLongAny(r.newStart)}`;
}

/**
 * Oracle applyMoveLocally, immutable: the moved WO gets its new start, end and week, and its pin when
 * the result says so. Every other WO, and the range itself when the WO is not in it, is returned as is.
 */
export function applyMove(range: RangeData, r: MoveResult): RangeData {
  if (!range.wos.some((w) => w.id === r.woId)) return range;
  return {
    ...range,
    wos: range.wos.map((w) =>
      w.id === r.woId
        ? {
            ...w,
            start: r.newStart,
            end: r.newEnd,
            weekNo: r.weekNo || w.weekNo,
            pinned: r.pinned,
            engineDate: r.engineDate || w.engineDate,
          }
        : w,
    ),
  };
}

/** Oracle doMove: push, then drop the oldest past ten. Immutable. */
export function pushUndo(stack: ReadonlyArray<UndoRef>, u: UndoRef): UndoRef[] {
  const next = [...stack, u];
  return next.length > UNDO_MAX ? next.slice(next.length - UNDO_MAX) : next;
}
