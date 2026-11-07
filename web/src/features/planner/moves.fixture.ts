/**
 * Azztec_SaaS_web_planner_moves_fixture_v1_0_0.ts  ->  web/src/features/planner/moves.fixture.ts
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (the tests) · OD-112
 *
 * The bodies the move tests answer with, in the 0.7.0 contract's shapes (MoveResult, MovePreview,
 * MoveConfirm, WriteError). The numbers are WO-101 from range.fixture moving Mon 14 -> Wed 16 Sep 2026;
 * the reason texts are rules.py's own (moveRules). Override what a case needs.
 *
 * Changelog:
 *   1.0.0  Initial DP3b.
 */
import type { MoveConfirm, MovePreview, MoveResult } from '../../api/client/types.gen';

export const FIXTURE_VERSION = '1.0.0';

export const PAST_REASON = { code: 'PAST', text: 'The target date is in the past' };
export const SPAN_REASON = { code: 'SPAN', text: 'Multi-day span: the end date moves 2026-09-15 -> 2026-09-17' };

/** A successful move of WO-101, +2 days. */
export function mkResult(over: Partial<MoveResult> = {}): MoveResult {
  return {
    ok: true,
    dryRun: false,
    woId: 101,
    sid: 'WO-101',
    prevStart: '2026-09-14',
    prevEnd: '2026-09-15',
    newStart: '2026-09-16',
    newEnd: '2026-09-17',
    delta: 2,
    weekNo: 2026.38,
    prevWeekNo: 2026.38,
    subtasks: 0,
    labourRows: 1,
    reasons: [],
    events: 3,
    willPin: false,
    willUnpin: false,
    pinned: false,
    engineDate: '',
    undo: { woId: 101, toIso: '2026-09-14', expectStartIso: '2026-09-16' },
    actor: 21,
    ...over,
  };
}

/** The preview a CONFIRM carries: WO-101 to Wed 16 Sep, asked because the day is past. */
export function mkPreview(over: Partial<MovePreview> = {}): MovePreview {
  return {
    ok: true,
    code: '',
    message: '',
    confirm: true,
    reasons: [PAST_REASON, SPAN_REASON],
    delta: 2,
    newStart: '2026-09-16',
    newEnd: '2026-09-17',
    willPin: false,
    willUnpin: false,
    pinnedAfter: false,
    woId: 101,
    sid: 'WO-101',
    title: 'Replace chain on infeed',
    status: 'H',
    statusTitle: 'Planned',
    prevStart: '2026-09-14',
    prevEnd: '2026-09-15',
    subtasks: 0,
    labourDates: [['2026-09-14', 1]],
    labourMoves: [{ from: '2026-09-14', to: '2026-09-16', rows: 1 }],
    ...over,
  };
}

/** OD-112: a 200 with ok:false, the flat error keys, the sid and the preview. */
export function mkConfirm(preview: MovePreview = mkPreview()): MoveConfirm {
  return {
    ok: false,
    code: 'CONFIRM',
    message: `${preview.sid}: The target date is in the past`,
    rid: 'rid-confirm',
    sid: preview.sid,
    preview,
  };
}

/** A flat refusal (OD-15 plus sid, and currentStart on STALE). */
export function mkError(code: string, message: string, extra: { sid?: string; currentStart?: string } = {}) {
  return {
    ok: false,
    code,
    message,
    rid: `rid-${code.toLowerCase()}`,
    sid: extra.sid ?? 'WO-101',
    currentStart: extra.currentStart ?? '',
  };
}
