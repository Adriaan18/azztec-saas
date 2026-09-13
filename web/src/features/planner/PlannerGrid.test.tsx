/**
 * Azztec_SaaS_web_planner_PlannerGrid_test_v1_0_1.tsx  ->  web/src/features/planner/PlannerGrid.test.tsx
 * Version:  1.0.1   Date: 2026-09-13   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §6 (PlannerGrid.test.tsx row) · pair rule
 *
 * Covers DayCell as well as the grid - one drawn surface, one test file (spec §10).
 * Zero network: the grid takes data as props and has nothing in its import graph that can fetch.
 * No jest-dom: assertions read className / getAttribute / textContent off the nodes.
 *
 * Changelog:
 *   1.0.1  S1g: renderGrid passes filters / priorities / onOpenDay / onClearSelect; new cases for the
 *          day-head click, the cell click, the strip cap under a selected worker, the P1 rank class.
 *   1.0.0  Initial S1f.
 */
import { cleanup, fireEvent, render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PlannerGrid, VERSION } from './PlannerGrid';
import { FROM, RANGE, TODAY, WORKERS, WOS, mkWo } from './range.fixture';
import { DEFAULT_FILTERS, indexWorkers } from './rules';
import type { Filters } from './rules';
import { windowFor } from '../../lib/dates';

export const TEST_VERSION = '1.0.1';

afterEach(() => {
  cleanup();
});

const byId = indexWorkers(WORKERS);

function must(root: HTMLElement, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

function renderGrid(mode: 'week' | 'twoweek' | 'month', anchor: string, wos = WOS, selected = 0, filters: Filters = DEFAULT_FILTERS) {
  const onSelect = vi.fn();
  const onOpenDay = vi.fn();
  const onClearSelect = vi.fn();
  const r = render(
    <PlannerGrid
      mode={mode}
      window={windowFor(mode, anchor)}
      wos={wos}
      today={TODAY}
      anchorMonth={anchor.slice(0, 7)}
      workers={WORKERS}
      byId={byId}
      filters={filters}
      priorities={RANGE.priorities}
      selected={selected}
      onSelect={onSelect}
      onOpenDay={onOpenDay}
      onClearSelect={onClearSelect}
    />,
  );
  return { ...r, onSelect, onOpenDay, onClearSelect };
}

describe('PlannerGrid - week', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.0.1');
  });

  it('draws 7 cells, no dow row and no strip', () => {
    const { container } = renderGrid('week', '2026-09-16');
    expect(container.querySelectorAll('.cell')).toHaveLength(7);
    expect(container.querySelector('.dow')).toBeNull();
    expect(container.querySelectorAll('.strip')).toHaveLength(0);
    expect(must(container, '.grid').className).toBe('grid week');
  });

  it('each WO lands in the cell for its start date', () => {
    const { container } = renderGrid('week', '2026-09-16');
    const monday = must(container, '[data-date="2026-09-14"]');
    expect(monday.querySelector('.chip')?.getAttribute('data-wo')).toBe('101');
    expect(must(container, '[data-date="2026-09-15"] .chip').getAttribute('data-wo')).toBe('102');
    expect(container.querySelectorAll('[data-date="2026-09-19"] .chip')).toHaveLength(0);
    expect(container.querySelectorAll('.chip')).toHaveLength(5);
  });

  it('the cell header carries DOW, the count text and the hh line', () => {
    const { container } = renderGrid('week', '2026-09-16');
    const monday = must(container, '[data-date="2026-09-14"]');
    expect(must(monday, '.d').textContent).toBe('MON 14 Sep');
    expect(must(monday, '.c').textContent).toBe('1 WO | 3.5h');
    expect(must(monday, '.hh').textContent).toBe('3.5 h planned');
    expect(must(container, '[data-date="2026-09-15"] .hh').textContent).toBe('1 without hours');
  });

  it('past, today and no out-of-month cells', () => {
    const { container } = renderGrid('week', '2026-09-16');
    expect(must(container, '[data-date="2026-09-14"]').className).toBe('cell past');
    expect(must(container, '[data-date="2026-09-16"]').className).toBe('cell today');
    expect(must(container, '[data-date="2026-09-17"]').className).toBe('cell');
    expect(container.querySelectorAll('.cell.out')).toHaveLength(0);
  });

  it('a chip click reaches onSelect with the id, and clears nothing', () => {
    const { container, onSelect, onClearSelect } = renderGrid('week', '2026-09-16');
    fireEvent.click(must(container, '[data-date="2026-09-14"] .chip'));
    expect(onSelect).toHaveBeenCalledWith(101);
    expect(onClearSelect).not.toHaveBeenCalled();
  });

  it('the day head opens that day (S1g); a click on the cell or its list clears the selection', () => {
    const { container, onOpenDay, onClearSelect, onSelect } = renderGrid('week', '2026-09-16');
    fireEvent.click(must(container, '[data-day="2026-09-14"]'));
    expect(onOpenDay).toHaveBeenCalledWith('2026-09-14');
    expect(onClearSelect).not.toHaveBeenCalled();
    fireEvent.click(must(container, '[data-date="2026-09-19"]'));
    expect(onClearSelect).toHaveBeenCalledTimes(1);
    fireEvent.click(must(container, '[data-date="2026-09-19"] .list'));
    expect(onClearSelect).toHaveBeenCalledTimes(2);
    fireEvent.click(must(container, '[data-date="2026-09-14"] .c')); // the count span: neither head nor cell
    expect(onClearSelect).toHaveBeenCalledTimes(2);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('the P1 chip carries the rank class, the N/A chip does not (OD-32)', () => {
    const { container } = renderGrid('week', '2026-09-16');
    expect(must(container, '[data-date="2026-09-14"] .chip .pri').className).toBe('pri P1 r1');
    expect(must(container, '[data-date="2026-09-16"] .chip .pri').className).toBe('pri N/A');
  });
});

describe('PlannerGrid - twoweek and month', () => {
  it('twoweek: 14 cells, a dow row with the strip column, 2 strips', () => {
    const { container } = renderGrid('twoweek', '2026-09-16');
    expect(container.querySelectorAll('.cell')).toHaveLength(14);
    expect(container.querySelectorAll('.strip')).toHaveLength(3); // 2 week strips + the dow header cell
    expect(must(container, '.grid').className).toBe('grid twoweek');
    expect(must(container, '.dow').textContent).toBe('MONTUEWEDTHUFRISATSUNHOURS / WEEK');
  });

  it('month Sep 2026: 35 cells, 5 strips, out-of-month dashed, the 1st labelled', () => {
    const { container } = renderGrid('month', '2026-09-15');
    expect(container.querySelectorAll('.cell')).toHaveLength(35);
    expect(container.querySelectorAll('.grid .strip')).toHaveLength(5);
    expect(must(container, '.grid').className).toBe('grid');
    expect(must(container, '[data-date="2026-08-31"]').className).toBe('cell past out');
    expect(must(container, '[data-date="2026-10-04"]').className).toBe('cell out');
    expect(must(container, '[data-date="2026-08-31"] .d').textContent).toBe('31 Aug'); // first cell of the window
    expect(must(container, '[data-date="2026-09-01"] .d').textContent).toBe('1 Sep');
    expect(must(container, '[data-date="2026-09-15"] .d').textContent).toBe('15');
    expect(container.querySelector('.hh')).toBeNull(); // month cells have no hh line
  });

  it('month strip planned equals the API weeks[] entry with every cat on', () => {
    const { container } = renderGrid('month', '2026-09-15');
    const strips = container.querySelectorAll('.grid .strip');
    const target = Array.from(strips).find((s) => s.getAttribute('title')?.includes('Mon 14 Sep 2026'));
    expect(target).toBeTruthy();
    expect(must(target as HTMLElement, '.n').textContent).toBe(`${RANGE.weeks[0].planned} / 41 h`);
  });

  it('the strip cap follows the filters: a selected worker narrows it to their hours (S1g)', () => {
    const one = renderGrid('month', '2026-09-15', WOS, 0, { ...DEFAULT_FILTERS, workers: { 692: true } });
    const strip = Array.from(one.container.querySelectorAll('.grid .strip')).find((s) => s.getAttribute('title')?.includes('Mon 14 Sep 2026'));
    expect(must(strip as HTMLElement, '.n').textContent).toBe(`${RANGE.weeks[0].planned} / 1 h`);
    expect(strip?.getAttribute('title')).toContain('(1 workers)');
    one.unmount();
    const team = renderGrid('month', '2026-09-15', WOS, 0, { ...DEFAULT_FILTERS, teamId: 9 });
    const s9 = Array.from(team.container.querySelectorAll('.grid .strip')).find((s) => s.getAttribute('title')?.includes('Mon 14 Sep 2026'));
    expect(must(s9 as HTMLElement, '.n').textContent).toBe(`${RANGE.weeks[0].planned} / ? h`); // cap 0 renders `?` (OD-25)
  });

  it('month caps a busy cell at 4 chips with +n more, and expands on click', () => {
    const busy = [
      ...WOS,
      mkWo({ id: 201, sid: 'WO-201', start: FROM }),
      mkWo({ id: 202, sid: 'WO-202', start: FROM }),
      mkWo({ id: 203, sid: 'WO-203', start: FROM }),
      mkWo({ id: 204, sid: 'WO-204', start: FROM }),
    ];
    const { container } = renderGrid('month', '2026-09-15', busy);
    const cell = must(container, '[data-date="2026-09-14"]');
    expect(cell.querySelectorAll('.chip')).toHaveLength(4);
    expect(must(cell, '.more').textContent).toBe('+1 more');
    fireEvent.click(must(cell, '.more'));
    expect(cell.querySelectorAll('.chip')).toHaveLength(5);
    expect(must(cell, '.more').textContent).toBe('show less');
    expect(cell.className).toContain('x');
  });

  it('every window the grid draws is 7-wide and at most 42 cells (OD-23)', () => {
    for (const anchor of ['2026-08-15', '2026-02-15', '2027-05-15']) {
      const { container, unmount } = renderGrid('month', anchor);
      const n = container.querySelectorAll('.cell').length;
      expect(n % 7).toBe(0);
      expect(n).toBeLessThanOrEqual(42);
      unmount();
    }
  });
});
