/**
 * Azztec_SaaS_web_workorders_WoDetailsTab_test_v1_0_0.tsx  ->  web/src/features/workorders/WoDetailsTab.test.tsx
 * Version:  1.0.0   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §5 · pair of WoDetailsTab.tsx 1.0.0
 *
 * Column ORDER is asserted, not just presence: the three columns are the oracle's layout and a map
 * that silently reordered them would still contain every label.
 *
 * Changelog:
 *   1.0.0  Initial W1b. 12 cases.
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { VERSION, WoDetailsTab } from './WoDetailsTab';
import { recordFixture } from './record.fixture';

export const TEST_VERSION = '1.0.0';

afterEach(() => {
  cleanup();
});

function labelsIn(container: HTMLElement, sel: string): (string | null)[] {
  const col = container.querySelector<HTMLElement>(sel);
  return Array.from(col?.querySelectorAll<HTMLSpanElement>('.wo-flabel') ?? []).map(
    (e) => e.textContent,
  );
}

describe('the three columns', () => {
  it('left column is the seven rows in view order', () => {
    const { container } = render(<WoDetailsTab record={recordFixture()} />);
    expect(labelsIn(container, '.wo-col-left')).toEqual([
      'WO Group :',
      'Reason :',
      'Fault :',
      'Dept. :',
      'Class :',
      'Charge To :',
      'Responsibility :',
    ]);
  });
  it('middle column is the six rows in view order', () => {
    const { container } = render(<WoDetailsTab record={recordFixture()} />);
    expect(labelsIn(container, '.wo-col-mid')).toEqual([
      'WOC 1 :',
      'WOC 2 :',
      'WOC 3 :',
      'Company :',
      'Ref. 1 :',
      'Ref. 2 :',
    ]);
  });
  it('right column is the six stamp rows in view order', () => {
    const { container } = render(<WoDetailsTab record={recordFixture()} />);
    expect(labelsIn(container, '.wo-col-right')).toEqual([
      'Created By :',
      'Ack. By :',
      'Approved By :',
      'Closed By :',
      'Cancelled By :',
      'Last Save :',
    ]);
  });
});

describe('the values', () => {
  it('resolves the reference titles rather than showing ids', () => {
    render(<WoDetailsTab record={recordFixture()} />);
    expect(screen.getByText('Maintenance')).toBeTruthy();
    expect(screen.getByText('Electrical Fault')).toBeTruthy();
    expect(screen.getByText('652 KPP Plant')).toBeTruthy();
    expect(screen.getByText('627 Outfeed')).toBeTruthy();
  });
  it('shows the supplier shorts beside Charge To and Responsibility only', () => {
    const { container } = render(<WoDetailsTab record={recordFixture()} />);
    const descs = Array.from(
      container.querySelectorAll<HTMLSpanElement>('.wo-col-left .wo-desc'),
    ).map((e) => e.textContent);
    expect(descs).toEqual(['TM-MAINT', 'TM-ELEC']);
  });
  it('shows -- No Selection -- for an unset WOC', () => {
    const { container } = render(<WoDetailsTab record={recordFixture()} />);
    const mid = container.querySelector<HTMLElement>('.wo-col-mid');
    const values = Array.from(mid?.querySelectorAll<HTMLSpanElement>('.wo-val') ?? []).map(
      (e) => e.textContent,
    );
    expect(values.slice(0, 3)).toEqual(['-- No Selection --', '-- No Selection --', '-- No Selection --']);
  });
  it('shows a set WOC title as itself', () => {
    render(<WoDetailsTab record={recordFixture({ woc1Id: 4, woc1Title: 'Safety' })} />);
    expect(screen.getByText('Safety')).toBeTruthy();
  });
  it('pairs Created By with the logged date', () => {
    const { container } = render(<WoDetailsTab record={recordFixture()} />);
    const first = container.querySelector<HTMLElement>('.wo-col-right .wo-frow');
    const cells = Array.from(first?.querySelectorAll<HTMLSpanElement>('.wo-val') ?? []).map(
      (e) => e.textContent,
    );
    expect(cells).toEqual(['KF', '26/08/2026 19:17']);
  });
  it('leaves an unstamped row blank rather than printing a zero date', () => {
    const { container } = render(<WoDetailsTab record={recordFixture()} />);
    const rows = container.querySelectorAll<HTMLElement>('.wo-col-right .wo-frow');
    const ack = Array.from(rows[1].querySelectorAll<HTMLSpanElement>('.wo-val')).map(
      (e) => e.textContent,
    );
    expect(ack).toEqual(['', '']);
  });
});

describe('notes', () => {
  it('renders the record notes read-only with an OD-51 title', () => {
    const { container } = render(<WoDetailsTab record={recordFixture()} />);
    const ta = container.querySelector<HTMLTextAreaElement>('.wo-notes');
    expect(ta?.value).toContain('Last few bins are causing issues');
    expect(ta?.readOnly).toBe(true);
    expect(ta?.getAttribute('title') ?? '').toContain('OD-51');
  });
  it('renders an empty note as empty, not as the string null', () => {
    const { container } = render(<WoDetailsTab record={recordFixture({ notes: '' })} />);
    expect(container.querySelector<HTMLTextAreaElement>('.wo-notes')?.value).toBe('');
  });
});

describe('version', () => {
  it('WoDetailsTab.tsx is 1.0.0', () => {
    expect(VERSION).toBe('1.0.0');
  });
});
