/**
 * Azztec_SaaS_web_workorders_WoListPanel_test_v1_0_0.tsx  ->  web/src/features/workorders/WoListPanel.test.tsx
 * Version:  1.0.0   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §5 · pair of WoListPanel.tsx 1.0.0
 *
 * Landmines §C: cleanup() in afterEach, no jest-dom, the generic on querySelectorAll rather than a
 * cast. The handlers are spies and the spy is the instrument - a click test that only checked the
 * rendered class would pass even if the callback never fired.
 *
 * Changelog:
 *   1.0.0  Initial W1b. 16 cases.
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { WoListRow } from '../../api/client';
import { VERSION, WoListPanel } from './WoListPanel';
import type { WoListPanelProps } from './WoListPanel';

export const TEST_VERSION = '1.0.0';

afterEach(() => {
  cleanup();
});

const ROWS: WoListRow[] = [
  {
    id: 662704,
    sid: '3CL-260826-010',
    title: 'Check bin 16 level PE',
    asset: '3CL-090.170.PE1',
    loc: '3CL-090.170',
    status: 'V',
    prog: 6,
    hasPO: true,
    entry: '2026-08-26 19:17:09',
    badge: 'V|3CL-260826-010|6|1',
  },
  {
    id: 143760,
    sid: '1LY-110705-071',
    title: 'Replace drive belt',
    asset: '1LY-010.020.MT3',
    loc: '1LY-010.020',
    status: 'C',
    prog: 6,
    hasPO: false,
    entry: '2011-07-05 08:02:00',
    badge: 'C|1LY-110705-071|6|0',
  },
];

function props(over: Partial<WoListPanelProps> = {}): WoListPanelProps {
  return {
    rows: ROWS,
    count: 2,
    more: false,
    woType: 'N',
    selectedId: 662704,
    loading: false,
    onTypeChange: vi.fn(),
    onSelect: vi.fn(),
    onLoadMore: vi.fn(),
    ...over,
  };
}

describe('the header', () => {
  it('titles by type, following the view expression', () => {
    const { rerender } = render(<WoListPanel {...props({ woType: 'N' })} />);
    expect(screen.getByText('Work Orders')).toBeTruthy();
    rerender(<WoListPanel {...props({ woType: 'M' })} />);
    expect(screen.getByText('Planned Maintenance')).toBeTruthy();
    rerender(<WoListPanel {...props({ woType: '' })} />);
    expect(screen.getByText('Work Orders + PM')).toBeTruthy();
  });
  it('draws the four type chips in view order', () => {
    render(<WoListPanel {...props()} />);
    expect(screen.getByText('WO')).toBeTruthy();
    expect(screen.getByText('CP')).toBeTruthy();
    expect(screen.getByText('PM')).toBeTruthy();
    expect(screen.getByText('All')).toBeTruthy();
  });
  it('lights exactly the active chip and marks it pressed', () => {
    const { container } = render(<WoListPanel {...props({ woType: 'M' })} />);
    const on = container.querySelectorAll<HTMLButtonElement>('.wo-chip.on');
    expect(on).toHaveLength(1);
    expect(on[0].getAttribute('data-type')).toBe('M');
    expect(on[0].getAttribute('aria-pressed')).toBe('true');
  });
  it('the All chip carries the empty value, not a literal', () => {
    const { container } = render(<WoListPanel {...props({ woType: '' })} />);
    expect(container.querySelector('.wo-chip.on')?.getAttribute('data-type')).toBe('ALL');
  });
  it('a chip click reports its value to the caller', () => {
    const p = props();
    render(<WoListPanel {...p} />);
    fireEvent.click(screen.getByText('PM'));
    expect(p.onTypeChange).toHaveBeenCalledWith('M');
  });
});

describe('the table', () => {
  it('draws four visible columns - WO_ID stays hidden as in the oracle', () => {
    const { container } = render(<WoListPanel {...props()} />);
    const heads = container.querySelectorAll<HTMLTableCellElement>('thead th');
    expect(Array.from(heads).map((h) => h.textContent)).toEqual([
      'WO Number',
      'Title',
      'Asset',
      'Location',
    ]);
  });
  it('renders one row per list row with the badge in the first cell', () => {
    const { container } = render(<WoListPanel {...props()} />);
    expect(container.querySelectorAll('tbody tr')).toHaveLength(2);
    expect(screen.getByText('3CL-260826-010')).toBeTruthy();
    expect(container.querySelectorAll('.wo-badge')).toHaveLength(2);
  });
  it('paints the badge from the row composite, not from the status alone', () => {
    const { container } = render(<WoListPanel {...props()} />);
    const badges = container.querySelectorAll<HTMLSpanElement>('.wo-badge');
    expect(badges[0].style.backgroundColor).toBe('rgba(40, 167, 69, 0.16)');
    expect(badges[1].style.backgroundColor).toBe('rgba(220, 53, 69, 0.16)');
  });
  it('marks the selected row and only that row', () => {
    const { container } = render(<WoListPanel {...props({ selectedId: 143760 })} />);
    const on = container.querySelectorAll<HTMLTableRowElement>('tbody tr.on');
    expect(on).toHaveLength(1);
    expect(on[0].getAttribute('data-wo')).toBe('143760');
    expect(on[0].getAttribute('aria-selected')).toBe('true');
  });
  it('a row click reports the WO id', () => {
    const p = props();
    render(<WoListPanel {...p} />);
    fireEvent.click(screen.getByText('Replace drive belt'));
    expect(p.onSelect).toHaveBeenCalledWith(143760);
  });
  it('shows the empty notice only when not loading', () => {
    const { rerender } = render(<WoListPanel {...props({ rows: [], count: 0 })} />);
    expect(screen.getByText('No work orders match these filters.')).toBeTruthy();
    rerender(<WoListPanel {...props({ rows: [], count: 0, loading: true })} />);
    expect(screen.queryByText('No work orders match these filters.')).toBeNull();
  });
});

describe('the footer and paging (OD-77)', () => {
  it('prints the count with no total', () => {
    render(<WoListPanel {...props({ count: 2, more: false })} />);
    expect(screen.getByText('No of Records: 2')).toBeTruthy();
  });
  it('prints 200+ and offers Load more while more is true', () => {
    render(<WoListPanel {...props({ count: 200, more: true })} />);
    expect(screen.getByText('No of Records: 200+')).toBeTruthy();
    expect(screen.getByText('Load more')).toBeTruthy();
  });
  it('hides Load more on the last page', () => {
    render(<WoListPanel {...props({ more: false })} />);
    expect(screen.queryByText('Load more')).toBeNull();
  });
  it('Load more calls the caller, which owns the offset', () => {
    const p = props({ count: 200, more: true });
    render(<WoListPanel {...p} />);
    fireEvent.click(screen.getByText('Load more'));
    expect(p.onLoadMore).toHaveBeenCalledTimes(1);
  });
});

describe('version', () => {
  it('WoListPanel.tsx is 1.0.0', () => {
    expect(VERSION).toBe('1.0.0');
  });
});
