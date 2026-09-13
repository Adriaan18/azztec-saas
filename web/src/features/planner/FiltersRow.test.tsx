/**
 * Azztec_SaaS_web_planner_FiltersRow_test_v1_0_0.tsx  ->  web/src/features/planner/FiltersRow.test.tsx
 * Version:  1.0.0   Date: 2026-09-13   Author: Adriaan
 * Spec:     Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md §6 (FiltersRow.test.tsx row) · pair rule
 *
 * Zero network, zero fetch by import graph. No setupFiles / no globals on the box: explicit cleanup(),
 * plain DOM assertions. Fake timers only in the search cases, restored in afterEach.
 *
 * Changelog:
 *   1.0.0  Initial S1g.
 */
import { cleanup, fireEvent, render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { FiltersRow, SEARCH_SETTLE_MS, VERSION } from './FiltersRow';
import { RANGE, WORKERS } from './range.fixture';
import { DEFAULT_FILTERS, HINT, indexWorkers } from './rules';
import type { Filters } from './rules';

export const TEST_VERSION = '1.0.0';

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

function must(root: ParentNode, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

const byId = indexWorkers(WORKERS);

function renderRow(over: Partial<Filters> = {}, spies: Partial<Record<'onTeam' | 'onToggleWorker' | 'onPri' | 'onUnassigned' | 'onQ' | 'onClear', ReturnType<typeof vi.fn>>> = {}) {
  const s = {
    onTeam: vi.fn(),
    onToggleWorker: vi.fn(),
    onPri: vi.fn(),
    onUnassigned: vi.fn(),
    onQ: vi.fn(),
    onClear: vi.fn(),
    ...spies,
  };
  const r = render(
    <FiltersRow
      teams={RANGE.teams}
      priorities={RANGE.priorities}
      workers={WORKERS}
      byId={byId}
      filters={{ ...DEFAULT_FILTERS, ...over }}
      actor={1}
      onTeam={s.onTeam}
      onToggleWorker={s.onToggleWorker}
      onPri={s.onPri}
      onUnassigned={s.onUnassigned}
      onQ={s.onQ}
      onClear={s.onClear}
    />,
  );
  return { ...r, ...s };
}

describe('FiltersRow - the oracle filters row', () => {
  it('carries its version and the oracle settle time', () => {
    expect(VERSION).toBe('1.0.0');
    expect(SEARCH_SETTLE_MS).toBe(150);
  });

  it('team and priority selects: All teams / Any first, then the rules.ts labels', () => {
    const { container } = renderRow();
    const selects = container.querySelectorAll('select');
    expect(selects).toHaveLength(2);
    expect(Array.from(selects[0].options).map((o) => o.textContent)).toEqual(['All teams', 'MAINT \u00b7 2', 'ACME (contractor) \u00b7 1']);
    expect(Array.from(selects[1].options).map((o) => o.textContent)).toEqual([
      'Any',
      'P1 \u00b7 Urgent',
      'P2 \u00b7 High',
      'P3 \u00b7 Normal',
      'P4 \u00b7 Low',
      'N/A \u00b7 Not Applicable',
    ]);
  });

  it('changing team / priority / unassigned calls the numeric and boolean setters', () => {
    const { container, onTeam, onPri, onUnassigned } = renderRow();
    const selects = container.querySelectorAll('select');
    fireEvent.change(selects[0], { target: { value: '1' } });
    expect(onTeam).toHaveBeenCalledWith(1);
    fireEvent.change(selects[1], { target: { value: '7' } });
    expect(onPri).toHaveBeenCalledWith(7);
    fireEvent.change(selects[0], { target: { value: '0' } });
    expect(onTeam).toHaveBeenLastCalledWith(0);
    const boxes = container.querySelectorAll('.filters > label > input[type="checkbox"]');
    expect(boxes).toHaveLength(1);
    fireEvent.click(boxes[0]);
    expect(onUnassigned).toHaveBeenCalledWith(true);
  });

  it('the worker menu: closed by default, button opens, a checkbox toggles a worker, outside click closes', () => {
    const { container, onToggleWorker } = renderRow();
    const wsel = must(container, '.wsel');
    expect(wsel.className).toBe('wsel');
    expect(must(wsel, '.who').textContent).toBe('any');
    fireEvent.click(must(wsel, 'button'));
    expect(wsel.className).toBe('wsel open');
    expect(Array.from(wsel.querySelectorAll('.grp')).map((g) => g.textContent)).toEqual(['MAINT', 'ACME \u00b7 contractor']);
    const labels = wsel.querySelectorAll('.menu label');
    expect(labels).toHaveLength(3);
    expect(labels[0].textContent).toBe(' Ann Kowhai 40/wk');
    fireEvent.click(must(labels[1], 'input'));
    expect(onToggleWorker).toHaveBeenCalledWith(692);
    fireEvent.click(document.body);
    expect(wsel.className).toBe('wsel');
  });

  it('the button label names one selected worker, and the checkbox reflects the selection', () => {
    const { container } = renderRow({ workers: { 692: true } });
    expect(must(container, '.who').textContent).toBe('Jo Bloggs');
    fireEvent.click(must(container, '.wsel button'));
    const labels = container.querySelectorAll('.menu label');
    expect((must(labels[1], 'input') as HTMLInputElement).checked).toBe(true);
    expect((must(labels[0], 'input') as HTMLInputElement).checked).toBe(false);
  });

  it('a team filter narrows the menu to that team', () => {
    const { container } = renderRow({ teamId: 9 });
    fireEvent.click(must(container, '.wsel button'));
    expect(Array.from(container.querySelectorAll('.grp')).map((g) => g.textContent)).toEqual(['ACME \u00b7 contractor']);
  });

  it('Escape inside the row closes the menu and does not reach the document', () => {
    const doc = vi.fn();
    document.addEventListener('keydown', doc);
    try {
      const { container } = renderRow();
      const wsel = must(container, '.wsel');
      fireEvent.click(must(wsel, 'button'));
      expect(wsel.className).toBe('wsel open');
      fireEvent.keyDown(must(wsel, 'button'), { key: 'Escape' });
      expect(wsel.className).toBe('wsel');
      expect(doc).not.toHaveBeenCalled();
      // menu closed: Escape now bubbles like any other key
      fireEvent.keyDown(must(wsel, 'button'), { key: 'Escape' });
      expect(doc).toHaveBeenCalledTimes(1);
    } finally {
      document.removeEventListener('keydown', doc);
    }
  });

  it('search settles after 150 ms, trimmed, once for a burst of keystrokes', () => {
    vi.useFakeTimers();
    const { container, onQ } = renderRow();
    const input = must(container, 'input[type="text"]') as HTMLInputElement;
    expect(input.placeholder).toBe('Search WO / title / asset / location');
    fireEvent.change(input, { target: { value: ' sta' } });
    fireEvent.change(input, { target: { value: ' stack' } });
    fireEvent.change(input, { target: { value: ' stacker ' } });
    expect(input.value).toBe(' stacker ');
    expect(onQ).not.toHaveBeenCalled();
    vi.advanceTimersByTime(SEARCH_SETTLE_MS - 1);
    expect(onQ).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onQ).toHaveBeenCalledTimes(1);
    expect(onQ).toHaveBeenCalledWith('stacker');
  });

  it('Clear calls onClear; when the store clears q the box empties too', () => {
    const { container, onClear, rerender } = renderRow({ q: 'infeed' });
    const input = must(container, 'input[type="text"]') as HTMLInputElement;
    expect(input.value).toBe('infeed');
    fireEvent.click(Array.from(container.querySelectorAll('button')).find((b) => b.textContent === 'Clear') as HTMLElement);
    expect(onClear).toHaveBeenCalledTimes(1);
    rerender(
      <FiltersRow
        teams={RANGE.teams}
        priorities={RANGE.priorities}
        workers={WORKERS}
        byId={byId}
        filters={{ ...DEFAULT_FILTERS }}
        actor={1}
        onTeam={vi.fn()}
        onToggleWorker={vi.fn()}
        onPri={vi.fn()}
        onUnassigned={vi.fn()}
        onQ={vi.fn()}
        onClear={onClear}
      />,
    );
    expect(input.value).toBe('');
  });

  it('hint and actor are the OD-34 strings, nothing about dragging', () => {
    const { container } = renderRow();
    const hints = container.querySelectorAll('.hint');
    expect(hints).toHaveLength(2);
    expect(hints[0].textContent).toBe(HINT);
    expect(hints[0].textContent).not.toContain('Drag');
    expect(must(container, '[data-actor]').textContent).toBe('actor #1');
  });
});
