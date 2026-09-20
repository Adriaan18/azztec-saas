/**
 * Azztec_SaaS_web_workorders_WoRecordCard_test_v1_0_0.tsx  ->  web/src/features/workorders/WoRecordCard.test.tsx
 * Version:  1.0.0   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §5 · pair of WoRecordCard.tsx 1.0.0
 *
 * Renders WO 662704 as the W1a smoke read it on RST, so a figure that changes here is a figure that
 * changed on the wire. The resources line is asserted CHARACTER FOR CHARACTER including its double
 * spaces - the API composes it and the page must not quietly re-space it.
 *
 * Changelog:
 *   1.0.0  Initial W1b. 19 cases.
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { VERSION, WoRecordCard } from './WoRecordCard';
import { recordFixture } from './record.fixture';

export const TEST_VERSION = '1.0.0';

afterEach(() => {
  cleanup();
});

describe('the header card', () => {
  it('shows the short id in the pill, not the numeric WO_ID', () => {
    render(<WoRecordCard record={recordFixture()} />);
    expect(screen.getByText('3CL-260826-010')).toBeTruthy();
    expect(screen.queryByText('662704')).toBeNull();
  });
  it("paints the pill from the pill's own map", () => {
    const { container } = render(<WoRecordCard record={recordFixture()} />);
    const pill = container.querySelector<HTMLSpanElement>('.wo-idpill');
    expect(pill?.style.backgroundColor).toBe('rgb(40, 167, 69)');
    expect(pill?.style.color).toBe('rgb(255, 255, 255)');
  });
  it('shows title, asset and the joined hierarchy', () => {
    render(<WoRecordCard record={recordFixture()} />);
    expect(screen.getByText('Check bin 16 level PE')).toBeTruthy();
    expect(screen.getByText('3CL-090.170.PE1')).toBeTruthy();
    expect(
      screen.getByText(
        'Red Stag Timber Waipa > 3 Secondary Processing > 08 Coastal > 090 Viking Bins > 170 Bin 16',
      ),
    ).toBeTruthy();
  });
  it('draws both symbol rows and lights Active and 100%', () => {
    const { container } = render(<WoRecordCard record={recordFixture()} />);
    expect(container.querySelectorAll('.wo-symrow')).toHaveLength(2);
    const lit = container.querySelectorAll<HTMLDivElement>('[data-lit="true"]');
    expect(lit).toHaveLength(2);
    expect(container.querySelector('[data-code="V"]')?.getAttribute('data-lit')).toBe('true');
    expect(container.querySelector('[data-progress="6"]')?.getAttribute('data-lit')).toBe('true');
  });
  it('hides the progress row when prog is 0 rather than drawing eight dead cards', () => {
    const { container } = render(<WoRecordCard record={recordFixture({ prog: 0 })} />);
    expect(container.querySelectorAll('.wo-symrow')).toHaveLength(1);
    expect(container.querySelector('[data-code="V"]')).toBeTruthy();
  });
  it('hides the status row when the status is empty', () => {
    const { container } = render(<WoRecordCard record={recordFixture({ status: '' })} />);
    expect(container.querySelectorAll('.wo-symrow')).toHaveLength(1);
    expect(container.querySelector('[data-progress="6"]')).toBeTruthy();
  });
});

describe('the schedule card', () => {
  it('draws the segment marking the record value', () => {
    const { container } = render(<WoRecordCard record={recordFixture()} />);
    expect(container.querySelector('.wo-seg-item.on')?.getAttribute('data-seg')).toBe('week');
  });
  it('renders the date-time fields through the string formatter', () => {
    render(<WoRecordCard record={recordFixture()} />);
    expect(screen.getByText('Aug 26, 2026 7:17 PM')).toBeTruthy();
    expect(screen.getByText('Sep 2, 2026 7:17 PM')).toBeTruthy();
  });
  it('renders the logged stamp as dd/MM/yyyy HH:mm', () => {
    render(<WoRecordCard record={recordFixture()} />);
    expect(screen.getByText('26/08/2026 19:17')).toBeTruthy();
  });
  it("prints float columns the oracle's way - 0.0, not 0", () => {
    const { container } = render(<WoRecordCard record={recordFixture()} />);
    const sched = container.querySelector<HTMLElement>('[aria-label="Schedule"]');
    const values = Array.from(sched?.querySelectorAll<HTMLSpanElement>('.wo-val') ?? []).map(
      (e) => e.textContent,
    );
    expect(values).toContain('0.0');
    expect(values).toContain('2026.35');
  });
  it('shows the OD-65 notice instead of six zeroes when the detail row is missing', () => {
    render(<WoRecordCard record={recordFixture({ detailsMissing: true })} />);
    expect(screen.getByText(/no detail record/i)).toBeTruthy();
    expect(screen.queryByText('Week No :')).toBeNull();
  });
});

describe('the assignment card', () => {
  it('shows priority, charge-to and responsibility with their supplier shorts', () => {
    render(<WoRecordCard record={recordFixture()} />);
    expect(screen.getByText('Priority 2')).toBeTruthy();
    expect(screen.getByText('Maintenance Team')).toBeTruthy();
    expect(screen.getByText('TM-MAINT')).toBeTruthy();
    expect(screen.getByText('Electrical Team')).toBeTruthy();
    expect(screen.getByText('TM-ELEC')).toBeTruthy();
  });
  it('shows (none) when no responsible users are attached', () => {
    render(<WoRecordCard record={recordFixture()} />);
    expect(screen.getByText('(none)')).toBeTruthy();
  });
  it('joins responsible users with a comma when there are some', () => {
    render(
      <WoRecordCard
        record={recordFixture({
          respUsers: [
            { userId: 1, shortId: 'KF', name: 'Ken F' },
            { userId: 2, shortId: 'AB', name: 'A B' },
          ],
        })}
      />,
    );
    expect(screen.getByText('KF, AB')).toBeTruthy();
  });
  it('the Manage button is inert with an OD-51 title', () => {
    const { container } = render(<WoRecordCard record={recordFixture()} />);
    const btn = container.querySelector<HTMLSpanElement>('[data-inert="Manage resp. users"]');
    expect(btn?.getAttribute('aria-disabled')).toBe('true');
    expect(btn?.getAttribute('title') ?? '').toContain('OD-51');
  });
});

describe('the resources card', () => {
  it('draws the seven columns in oracle order', () => {
    const { container } = render(<WoRecordCard record={recordFixture()} />);
    const res = container.querySelector<HTMLElement>('[aria-label="All resources"]');
    const heads = Array.from(res?.querySelectorAll<HTMLTableCellElement>('thead th') ?? []).map(
      (h) => h.textContent,
    );
    expect(heads).toEqual(['Type', 'Item', 'Plan Qty', 'Plan $', 'Act Qty', 'Act $', 'Diff $']);
  });
  it('renders one row per resource row and blanks a null figure', () => {
    const { container } = render(<WoRecordCard record={recordFixture()} />);
    const res = container.querySelector<HTMLElement>('[aria-label="All resources"]');
    const cells = Array.from(res?.querySelectorAll<HTMLTableCellElement>('tbody td') ?? []).map(
      (c) => c.textContent,
    );
    expect(cells).toEqual(['Labour', 'E1', '', '', '1.0', '36.52', '36.52']);
  });
  it('prints the API-composed line byte for byte, double spaces and all', () => {
    render(<WoRecordCard record={recordFixture()} />);
    const line = screen.getByText((_t, el) => el?.className === 'wo-resline');
    expect(line.textContent).toBe('Planned $0.00  |  Actual $36.52  |  Diff +$36.52');
  });
});

describe('version', () => {
  it('WoRecordCard.tsx is 1.0.0', () => {
    expect(VERSION).toBe('1.0.0');
  });
});
