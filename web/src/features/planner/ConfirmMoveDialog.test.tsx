/**
 * Azztec_SaaS_web_planner_ConfirmMoveDialog_test_v1_0_0.tsx  ->  web/src/features/planner/ConfirmMoveDialog.test.tsx
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (ConfirmMoveDialog.test.tsx row) · pair of
 *           ConfirmMoveDialog.tsx 1.0.0
 *
 * Zero network. The oracle's showConfirm markup on moves.fixture's preview: the title, the old -> new
 * line, every reason (SPAN shown with PAST - OD-116), the labour moves and the subtask line with their
 * plurals, the two buttons and where the focus lands. Explicit cleanup(), plain DOM assertions.
 *
 * Changelog:
 *   1.0.0  Initial DP3b.
 */
import { cleanup, fireEvent, render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ConfirmMoveDialog, VERSION, rows } from './ConfirmMoveDialog';
import { mkPreview } from './moves.fixture';

export const TEST_VERSION = '1.0.0';

afterEach(() => {
  cleanup();
});

function must(root: ParentNode, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

describe('ConfirmMoveDialog - the oracle showConfirm', () => {
  it('carries its version; rows() is the oracle plural', () => {
    expect(VERSION).toBe('1.0.0');
    expect(rows(1, 'row')).toBe('1 row');
    expect(rows(3, 'row')).toBe('3 rows');
    expect(rows(2, 'subtask row')).toBe('2 subtask rows');
  });

  it('renders nothing without a preview', () => {
    const { container } = render(<ConfirmMoveDialog preview={null} onYes={vi.fn()} onNo={vi.fn()} />);
    expect(container.querySelector('.ovl')).toBeNull();
  });

  it('title, the move line, title and status, every reason, the labour moves', () => {
    const { container } = render(<ConfirmMoveDialog preview={mkPreview()} onYes={vi.fn()} onNo={vi.fn()} />);
    expect(must(container, '.ovl').className).toBe('ovl on');
    expect(must(container, '.dlg h2').textContent).toBe('MOVE WO-101?');
    expect(must(container, '[role="dialog"]').getAttribute('aria-label')).toBe('MOVE WO-101?');
    expect(must(container, '.dlg .mv').textContent).toBe('Mon 14 Sep 2026 → Wed 16 Sep 2026 (+2 d)');
    expect(must(container, '.dlg .mv b').textContent).toBe('Wed 16 Sep 2026');
    expect(must(container, '.dlg > .sub').textContent).toBe('Replace chain on infeed · Planned');
    expect(Array.from(container.querySelectorAll('.why li')).map((li) => li.textContent)).toEqual([
      'The target date is in the past',
      'Multi-day span: the end date moves 2026-09-15 -> 2026-09-17',
    ]);
    expect(Array.from(container.querySelectorAll('.lm li')).map((li) => li.textContent)).toEqual([
      '2026-09-14 → 2026-09-16 (1 row)',
    ]);
    expect(container.textContent).not.toContain('subtask');
  });

  it('no labour block when nothing moves; the subtask line when subtasks do', () => {
    const { container } = render(
      <ConfirmMoveDialog preview={mkPreview({ labourMoves: [], subtasks: 2 })} onYes={vi.fn()} onNo={vi.fn()} />,
    );
    expect(container.querySelector('.lm')).toBeNull();
    expect(container.textContent).not.toContain('Planned labour:');
    expect(container.textContent).toContain('2 subtask rows move too.');
  });

  it('Move it has the focus; the buttons call onYes / onNo', () => {
    const onYes = vi.fn();
    const onNo = vi.fn();
    const { container } = render(<ConfirmMoveDialog preview={mkPreview()} onYes={onYes} onNo={onNo} />);
    const [cancel, move] = Array.from(container.querySelectorAll('.btns button'));
    expect(move.textContent).toBe('Move it');
    expect(document.activeElement).toBe(move);
    fireEvent.click(move);
    expect(onYes).toHaveBeenCalledTimes(1);
    fireEvent.click(cancel);
    expect(onNo).toHaveBeenCalledTimes(1);
  });

  it('a click on the overlay closes it; a click inside the dialog does not', () => {
    const onNo = vi.fn();
    const { container } = render(<ConfirmMoveDialog preview={mkPreview()} onYes={vi.fn()} onNo={onNo} />);
    fireEvent.click(must(container, '.dlg h2'));
    expect(onNo).not.toHaveBeenCalled();
    fireEvent.click(must(container, '.ovl'));
    expect(onNo).toHaveBeenCalledTimes(1);
  });
});
