/**
 * Azztec_SaaS_web_planner_WorkerPanel_test_v1_0_0.tsx  ->  web/src/features/planner/WorkerPanel.test.tsx
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §6 (WorkerPanel.test.tsx row) · OD-24, OD-25, OD-26
 *
 * The OD-26 default is a decision, so it is pinned as a test rather than left to the screenshot: the
 * rail opens on loaded internal workers, the count line states what is hidden, and both toggles widen
 * it. The 1000% row is asserted here too - the rail is where a planner actually meets it.
 *
 * Zero network, no jest-dom.
 *
 * Changelog:
 *   1.0.0  Initial S1f.
 */
import { cleanup, render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { VERSION, WorkerPanel } from './WorkerPanel';
import { RANGE, WORKERS } from './range.fixture';
import type { RailOpts } from './rules';

export const TEST_VERSION = '1.0.0';

afterEach(() => {
  cleanup();
});

function must(root: HTMLElement, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

function renderPanel(opts: RailOpts, days = 7) {
  return render(
    <WorkerPanel
      workers={WORKERS}
      load={RANGE.load}
      workerWeeks={RANGE.workerWeeks}
      days={days}
      opts={opts}
      onToggleContractors={vi.fn()}
      onToggleLoadedOnly={vi.fn()}
    />,
  );
}

describe('WorkerPanel - the rail (OD-24 / OD-26)', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.0.0');
  });

  it('the default is loaded internal only, with the hidden rows counted', () => {
    const { container } = renderPanel({ contractors: false, loadedOnly: true });
    const rows = container.querySelectorAll('.wk');
    expect(rows).toHaveLength(1);
    expect(rows[0].getAttribute('data-worker')).toBe('692');
    expect(must(container, '[data-count]').textContent).toBe('1 of 2 internal \u00b7 1 contractors hidden');
    expect(must(container, 'h3 span').textContent).toBe('(1)');
  });

  it('loaded only off shows every internal worker in API order', () => {
    const { container } = renderPanel({ contractors: false, loadedOnly: false });
    const ids = Array.from(container.querySelectorAll('.wk')).map((r) => r.getAttribute('data-worker'));
    expect(ids).toEqual(['692', '2']);
    expect(must(container, '[data-count]').textContent).toBe('2 of 2 internal \u00b7 1 contractors hidden');
  });

  it('contractors on adds the contractor row with the contr class', () => {
    const { container } = renderPanel({ contractors: true, loadedOnly: false });
    const ids = Array.from(container.querySelectorAll('.wk')).map((r) => r.getAttribute('data-worker'));
    expect(ids).toEqual(['692', '2', '3']);
    expect(must(container, '[data-worker="3"]').className).toBe('wk contr');
    expect(must(container, '[data-worker="2"]').className).toBe('wk');
    expect(must(container, '[data-count]').textContent).toBe('2 of 2 internal \u00b7 1 contractors');
  });

  it('the 1000% row: full red bar, real pct in the tooltips, over flag counted', () => {
    const { container } = renderPanel({ contractors: false, loadedOnly: true });
    const row = must(container, '[data-worker="692"]');
    const bar = must(row, '.ld .bar i');
    expect(bar.className).toBe('over');
    expect(bar.style.width).toBe('100%');
    expect(row.getAttribute('title')).toContain('1000% of 1 h');
    expect(must(row, '.wkb i').className).toBe('over');
    expect(must(row, '.wkb i').getAttribute('title')).toBe('wk of 2026-09-14: 10 / 1 h (1000%) over');
    expect(must(row, '.flags').textContent).toBe('1 over');
    expect(must(row, '.ld b').textContent).toBe('10 h');
    expect(must(row, '.cap').textContent).toBe('1/wk');
  });

  it('the row shows initials, name, team and first skill', () => {
    const { container } = renderPanel({ contractors: false, loadedOnly: true });
    const row = must(container, '[data-worker="692"]');
    expect(must(row, '.av').textContent).toBe('JB');
    expect(must(row, '.nm small').textContent).toBe('MAINT \u00b7 Fitter');
  });

  it('a wider window scales capacity, so the same load is a smaller pct', () => {
    const { container } = renderPanel({ contractors: false, loadedOnly: true }, 35);
    expect(must(container, '[data-worker="692"] .ld .bar i').style.width).toBe('100%'); // 200%, still full
    expect(must(container, '[data-worker="692"]').getAttribute('title')).toContain('200% of 5 h');
  });

  it('toggles that match nothing show the empty line, not a blank panel', () => {
    const { container } = render(
      <WorkerPanel
        workers={[]}
        load={{}}
        workerWeeks={{}}
        days={7}
        opts={{ contractors: false, loadedOnly: true }}
        onToggleContractors={vi.fn()}
        onToggleLoadedOnly={vi.fn()}
      />,
    );
    expect(must(container, '.empty').textContent).toBe('nobody matches these toggles');
    expect(must(container, '[data-count]').textContent).toBe('0 of 0 internal \u00b7 0 contractors hidden');
  });
});
