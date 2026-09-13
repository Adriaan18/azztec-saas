/**
 * Azztec_SaaS_web_planner_WOCard_test_v1_0_1.tsx  ->  web/src/features/planner/WOCard.test.tsx
 * Version:  1.0.1   Date: 2026-09-13   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §6 (WOCard.test.tsx row) · pair rule
 *
 * Zero network AND zero fetch: this component never asks for anything, so the stub from the S1e hook
 * test is not needed here - the proof is that nothing in the import graph can reach the client.
 *
 * The harness on the box (verified 2026-09-12): vitest 5, jsdom, NO setupFiles and NO globals, so
 * @testing-library/react's automatic cleanup does not run and jest-dom is not installed. Hence the
 * explicit cleanup() in afterEach and the plain DOM assertions (className / getAttribute /
 * textContent), never toBeInTheDocument().
 *
 * Changelog:
 *   1.0.1  S1g: the OD-32 rank class cases and the OD-33 pin (title unchanged with a rank set).
 *   1.0.0  Initial S1f.
 */
import { cleanup, fireEvent, render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { WOCard, VERSION } from './WOCard';
import { DONE_104, PIN_105, PM_102, RANGE, REQ_103, WO_101, mkWo } from './range.fixture';
import { chipTitle, priRank } from './rules';

export const TEST_VERSION = '1.0.1';

afterEach(() => {
  cleanup();
});

/** querySelector returns Element | null; this keeps the null check honest without a non-null assertion. */
function must(root: HTMLElement, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

describe('WOCard - the chip (oracle chipEl)', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.0.1');
  });

  it('a movable WO: cat class, mv, data attributes, priority badge, hours, initials', () => {
    const { container } = render(<WOCard wo={WO_101} who="JB AK" selected={false} onSelect={vi.fn()} />);
    const chip = must(container, '.chip');
    expect(chip.className).toBe('chip cat-WO mv');
    expect(chip.getAttribute('data-wo')).toBe('101');
    expect(chip.getAttribute('data-movable')).toBe('1');
    expect(must(chip, '.pri').className).toBe('pri P1');
    expect(must(chip, '.pri').textContent).toBe('P1');
    expect(must(chip, '.sid').textContent).toBe('WO-101');
    expect(must(chip, '.hrs').className).toBe('hrs');
    expect(must(chip, '.hrs').textContent).toBe('3.5h');
    expect(must(chip, '.who').textContent).toBe('JB AK');
    expect(chip.querySelector('.lk')).toBeNull();
    expect(chip.querySelector('.pn')).toBeNull();
  });

  it('the locked engine-owned PM: locked class, not movable, unknown hours, lock glyph, OD-1 tooltip', () => {
    const { container } = render(<WOCard wo={PM_102} who="" selected={false} onSelect={vi.fn()} />);
    const chip = must(container, '.chip');
    expect(chip.className).toBe('chip cat-PM locked');
    expect(chip.getAttribute('data-movable')).toBe('0');
    expect(must(chip, '.hrs').className).toBe('hrs unk');
    expect(must(chip, '.hrs').textContent).toBe('?');
    expect(chip.querySelector('.who')).toBeNull();
    expect(chip.querySelector('.pri')).toBeNull();
    const lk = must(chip, '.lk');
    expect(lk.getAttribute('aria-label')).toBe('engine owned');
    expect(chip.getAttribute('title')).toContain('run the S3 DDL (WO_N_Plan) to allow planner pins');
  });

  it('a pinned PM shows the pin glyph, never the lock', () => {
    const { container } = render(<WOCard wo={PIN_105} who="JB AK CS +1" selected={false} onSelect={vi.fn()} />);
    const chip = must(container, '.chip');
    expect(chip.className).toBe('chip cat-PM mv');
    expect(must(chip, '.pn').getAttribute('aria-label')).toBe('pinned by planner');
    expect(chip.querySelector('.lk')).toBeNull();
    expect(must(chip, '.who').textContent).toBe('JB AK CS +1');
  });

  it('a closed WO is cat-DONE, locked and immovable', () => {
    const { container } = render(<WOCard wo={DONE_104} who="" selected={false} onSelect={vi.fn()} />);
    const chip = must(container, '.chip');
    expect(chip.className).toBe('chip cat-DONE locked');
    expect(chip.getAttribute('data-movable')).toBe('0');
    expect(must(chip, '.lk')).toBeTruthy();
  });

  it('selected adds sel, and the title is rules.chipTitle verbatim', () => {
    const { container } = render(<WOCard wo={REQ_103} who="" selected onSelect={vi.fn()} />);
    const chip = must(container, '.chip');
    expect(chip.className).toBe('chip cat-REQ mv sel');
    expect(chip.getAttribute('title')).toBe(
      'REQ-103 \u00b7 Check hydraulic leak\nRequest \u00b7 priority N/A\n2h (estimate)\ndrag to move',
    );
  });

  it('an empty priority renders no badge (RST leaves pri blank on most PMs)', () => {
    const { container } = render(<WOCard wo={mkWo({ id: 9, sid: 'WO-9', pri: '' })} who="" selected={false} onSelect={vi.fn()} />);
    expect(container.querySelector('.pri')).toBeNull();
  });

  it('priRank adds the rank class beside the letter (OD-32); 0 and 5+ leave the badge as 1.0.0 drew it', () => {
    const r1 = render(<WOCard wo={WO_101} who="" selected={false} onSelect={vi.fn()} priRank={priRank(WO_101, RANGE.priorities)} />);
    expect(must(r1.container, '.pri').className).toBe('pri P1 r1');
    expect(must(r1.container, '.pri').textContent).toBe('P1');
    cleanup();
    const r5 = render(<WOCard wo={REQ_103} who="" selected={false} onSelect={vi.fn()} priRank={priRank(REQ_103, RANGE.priorities)} />);
    expect(must(r5.container, '.pri').className).toBe('pri N/A');
    cleanup();
    const r0 = render(<WOCard wo={WO_101} who="" selected={false} onSelect={vi.fn()} />);
    expect(must(r0.container, '.pri').className).toBe('pri P1');
  });

  it('the title is chipTitle whatever the rank (OD-33: the hover is parity)', () => {
    const { container } = render(<WOCard wo={WO_101} who="JB AK" selected={false} onSelect={vi.fn()} priRank={1} />);
    expect(must(container, '.chip').getAttribute('title')).toBe(chipTitle(WO_101));
  });

  it('click calls onSelect with the id, once, and does not bubble to the cell', () => {
    const onSelect = vi.fn();
    const onCell = vi.fn();
    const { container } = render(
      <div onClick={onCell}>
        <WOCard wo={WO_101} who="" selected={false} onSelect={onSelect} />
      </div>,
    );
    fireEvent.click(must(container, '.chip'));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(101);
    expect(onCell).not.toHaveBeenCalled();
  });
});
