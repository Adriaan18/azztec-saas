/**
 * Azztec_SaaS_web_planner_DayDialog_test_v1_1_0.tsx  ->  web/src/features/planner/DayDialog.test.tsx
 * Version:  1.1.0   Date: 2026-09-14   Author: Adriaan
 * Spec:     Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md §6 (DayDialog.test.tsx row) · OD-5, OD-32, OD-34; S1i spec §5.2 · pair of DayDialog 1.1.0
 *
 * Zero network, zero fetch by import graph. Explicit cleanup(), plain DOM assertions.
 *
 * Changelog:
 *   1.1.0  S1i: every 1.0.1 case kept; VERSION is 1.1.0. New: the second badge site paints from the
 *          payload exactly as the chip does (OD-41), so it cannot silently stay grey.
 *   1.0.1  Lint: querySelectorAll('button') is already NodeListOf<HTMLButtonElement> on TS 6 lib.dom -
 *          the `as HTMLButtonElement` was an unnecessary assertion (no-unnecessary-type-assertion).
 *   1.0.0  Initial S1g.
 */
import { cleanup, fireEvent, render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { DayDialog, OPEN_TITLE, VERSION } from './DayDialog';
import { PIN_105, PM_102, RANGE, REQ_103, WORKERS, WO_101, mkWo } from './range.fixture';
import { indexWorkers } from './rules';
import type { Wo } from '../../api/client/types.gen';

export const TEST_VERSION = '1.1.0';

afterEach(() => {
  cleanup();
});

function must(root: ParentNode, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

const byId = indexWorkers(WORKERS);

function renderDialog(dateIso: string, list: ReadonlyArray<Wo>, onSelect = vi.fn(), onClose = vi.fn()) {
  const r = render(
    <DayDialog
      dateIso={dateIso}
      list={list}
      labour={RANGE.labour}
      byId={byId}
      priorities={RANGE.priorities}
      onSelect={onSelect}
      onClose={onClose}
    />,
  );
  return { ...r, onSelect, onClose };
}

describe('DayDialog - the oracle showDay, read-only', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.1.0');
    expect(OPEN_TITLE).toBe('arrives with the WO module (OD-5)');
  });

  it('renders nothing while closed', () => {
    const { container } = renderDialog('', [WO_101]);
    expect(container.innerHTML).toBe('');
  });

  it('a fixture day: overlay on, uppercase long date + countText, one .job per WO, the P1 rank class', () => {
    const { container } = renderDialog('2026-09-14', [WO_101, PM_102, REQ_103, PIN_105]);
    const ovl = must(container, '.ovl');
    expect(ovl.className).toBe('ovl on');
    expect(ovl.getAttribute('data-day')).toBe('2026-09-14');
    expect(must(ovl, '.dlg').className).toBe('dlg wide dd2');
    expect(must(ovl, 'h2').textContent).toBe('MON 14 SEP 2026 2 WO | 2 PM | 6.5h');
    const jobs = ovl.querySelectorAll('.job');
    expect(jobs).toHaveLength(4);
    expect(Array.from(jobs).map((j) => j.getAttribute('data-wo'))).toEqual(['101', '102', '103', '105']);
    expect(must(jobs[0], '.sid').className).toBe('sid WO');
    expect(must(jobs[0], '.sid').textContent).toBe('WO-101');
    expect(must(jobs[0], '.pri').className).toBe('pri P1 r1');
    expect(must(jobs[2], '.pri').className).toBe('pri N/A');
    expect(jobs[1].querySelector('.pri')).toBeNull();
    expect(must(jobs[1], '.sid').className).toBe('sid PM');
  });

  it('the row strings are rules.dialogRows placed in the oracle order', () => {
    const { container } = renderDialog('2026-09-14', [WO_101, PM_102]);
    const jobs = container.querySelectorAll('.job');
    const metas0 = Array.from(jobs[0].querySelectorAll('.meta')).map((m) => m.textContent);
    expect(metas0).toEqual(['Planned \u2192 2026-09-15', 'INF-01 \u00b7 Infeed conveyor \u00b7 SAW', '3.5h (labour) \u00b7 Jo Bloggs 2.5h, Ann Kowhai 1h']);
    expect(jobs[0].children[1].firstChild?.textContent).toBe('Replace chain on infeed');
    const metas1 = Array.from(jobs[1].querySelectorAll('.meta')).map((m) => m.textContent);
    expect(metas1).toEqual(['Planned \u00b7 engine owned', 'no asset', 'no hours yet \u00b7 owner Ann Kowhai']);
    expect(must(jobs[1], '.meta .none').textContent).toBe('no hours yet');
    expect(jobs[0].querySelector('.meta .none')).toBeNull();
  });

  it('an empty day says so and still offers Close', () => {
    const { container, onClose } = renderDialog('2026-09-19', []);
    expect(must(container, 'h2').textContent).toBe('SAT 19 SEP 2026 nothing scheduled');
    expect(must(container, '.none').textContent).toBe('Nothing scheduled that day (with the current filters).');
    expect(container.querySelectorAll('.job')).toHaveLength(0);
    fireEvent.click(must(container, '.btns button'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('Select sets the selection then closes; Open is disabled with the OD-5 reason; no Plan hours', () => {
    const { container, onSelect, onClose } = renderDialog('2026-09-14', [WO_101, mkWo({ id: 106, sid: 'WO-106', start: '2026-09-14' })]);
    const acts = container.querySelectorAll('.job .acts');
    expect(acts).toHaveLength(2);
    const buttons = acts[1].querySelectorAll('button');
    expect(Array.from(buttons).map((b) => b.textContent)).toEqual(['Select', 'Open']);
    expect(container.textContent).not.toContain('Plan hours');
    const open = buttons[1];
    expect(open.disabled).toBe(true);
    expect(open.getAttribute('title')).toBe(OPEN_TITLE);
    fireEvent.click(buttons[0]);
    expect(onSelect).toHaveBeenCalledWith(106);
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.invocationCallOrder[0]).toBeLessThan(onClose.mock.invocationCallOrder[0]);
  });

  it('the badge paints from the payload here too (OD-41): P1 red on white text, N/A white on dark', () => {
    const { container } = renderDialog('2026-09-14', [WO_101, REQ_103]);
    const jobs = container.querySelectorAll('.job');
    const p1 = must(jobs[0], '.pri');
    expect(p1.className).toBe('pri P1 r1');
    expect(p1.style.backgroundColor).toBe('rgb(255, 0, 0)');
    expect(p1.style.color).toBe('rgb(255, 255, 255)');
    const na = must(jobs[1], '.pri');
    expect(na.className).toBe('pri N/A');
    expect(na.style.backgroundColor).toBe('rgb(255, 255, 255)');
    expect(na.style.color).toBe('rgb(43, 43, 43)');
  });

  it('the title is a dialog role with an accessible name', () => {
    const { container } = renderDialog('2026-09-16', [REQ_103]);
    const dlg = must(container, '[role="dialog"]');
    expect(dlg.getAttribute('aria-label')).toBe('WED 16 SEP 2026');
  });
});
