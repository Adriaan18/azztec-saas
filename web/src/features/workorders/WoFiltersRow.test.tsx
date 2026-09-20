/**
 * Azztec_SaaS_web_workorders_WoFiltersRow_test_v1_0_0.tsx  ->  web/src/features/workorders/WoFiltersRow.test.tsx
 * Version:  1.0.0   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §5 · pair of WoFiltersRow.tsx 1.0.0
 *
 * The inert-control tests assert the ABSENCE of a handler as well as the presence of the title:
 * a control that fired a callback while wearing aria-disabled would be the exact OD-34 failure
 * (chrome that lies), and asserting only the attribute would not catch it.
 *
 * Changelog:
 *   1.0.0  Initial W1b. 17 cases.
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { INERT_CONTROLS, VERSION, WoFiltersRow } from './WoFiltersRow';
import type { WoFiltersRowProps } from './WoFiltersRow';

export const TEST_VERSION = '1.0.0';

afterEach(() => {
  cleanup();
});

function props(over: Partial<WoFiltersRowProps> = {}): WoFiltersRowProps {
  return {
    search: '',
    includeClosed: 0,
    includeArchive: 0,
    onSearchChange: vi.fn(),
    onClosedChange: vi.fn(),
    onArchiveChange: vi.fn(),
    ...over,
  };
}

describe('the search box', () => {
  it("carries the oracle's placeholder verbatim", () => {
    render(<WoFiltersRow {...props()} />);
    expect(screen.getByPlaceholderText('Search work orders...')).toBeTruthy();
  });
  it('is controlled - it shows what the caller gave it', () => {
    render(<WoFiltersRow {...props({ search: 'bin 16' })} />);
    const input = screen.getByLabelText<HTMLInputElement>('Search work orders');
    expect(input.value).toBe('bin 16');
  });
  it('reports every keystroke raw - the debounce lives in the hook, not here', () => {
    const p = props();
    render(<WoFiltersRow {...p} />);
    fireEvent.change(screen.getByLabelText('Search work orders'), { target: { value: 'b' } });
    expect(p.onSearchChange).toHaveBeenCalledWith('b');
  });
  it('the clear button empties the term', () => {
    const p = props({ search: 'bin 16' });
    render(<WoFiltersRow {...p} />);
    fireEvent.click(screen.getByLabelText('Clear search'));
    expect(p.onSearchChange).toHaveBeenCalledWith('');
  });
});

describe('the two mode chips', () => {
  it('draws both unlit by default', () => {
    const { container } = render(<WoFiltersRow {...props()} />);
    expect(container.querySelectorAll('.wo-modechip')).toHaveLength(2);
    expect(container.querySelectorAll('.wo-modechip.on')).toHaveLength(0);
  });
  it('lights Closed and marks it pressed', () => {
    const { container } = render(<WoFiltersRow {...props({ includeClosed: 1 })} />);
    const chip = container.querySelector<HTMLSpanElement>('[data-chip="closed"]');
    expect(chip?.className).toContain('on');
    expect(chip?.getAttribute('aria-pressed')).toBe('true');
  });
  it('lights Archive independently of Closed', () => {
    const { container } = render(<WoFiltersRow {...props({ includeArchive: 2 })} />);
    expect(container.querySelector('[data-chip="archive"]')?.className).toContain('on');
    expect(container.querySelector('[data-chip="closed"]')?.className).not.toContain('on');
  });
  it('turning Closed on zeroes Archive', () => {
    const p = props({ includeArchive: 1 });
    const { container } = render(<WoFiltersRow {...p} />);
    fireEvent.click(container.querySelector<HTMLSpanElement>('[data-chip="closed"]')!);
    expect(p.onArchiveChange).toHaveBeenCalledWith(0);
    expect(p.onClosedChange).toHaveBeenCalledWith(1);
  });
  it('turning Archive on zeroes Closed', () => {
    const p = props({ includeClosed: 1 });
    const { container } = render(<WoFiltersRow {...p} />);
    fireEvent.click(container.querySelector<HTMLSpanElement>('[data-chip="archive"]')!);
    expect(p.onClosedChange).toHaveBeenCalledWith(0);
    expect(p.onArchiveChange).toHaveBeenCalledWith(1);
  });
  it('clicking a lit chip turns it off without touching the other', () => {
    const p = props({ includeClosed: 1 });
    const { container } = render(<WoFiltersRow {...p} />);
    fireEvent.click(container.querySelector<HTMLSpanElement>('[data-chip="closed"]')!);
    expect(p.onClosedChange).toHaveBeenCalledWith(0);
    expect(p.onArchiveChange).not.toHaveBeenCalled();
  });
  it('a chip at 2 reads as lit - the tri-state the URL can carry', () => {
    const { container } = render(<WoFiltersRow {...props({ includeClosed: 2 })} />);
    expect(container.querySelector('[data-chip="closed"]')?.getAttribute('aria-pressed')).toBe('true');
  });
});

describe('the inert write controls (OD-51 / OD-79)', () => {
  it('draws all seven', () => {
    const { container } = render(<WoFiltersRow {...props()} />);
    expect(container.querySelectorAll('[data-inert]')).toHaveLength(INERT_CONTROLS.length);
    expect(INERT_CONTROLS).toHaveLength(7);
  });
  it('every one is aria-disabled with a title that names the slice', () => {
    const { container } = render(<WoFiltersRow {...props()} />);
    const items = container.querySelectorAll<HTMLSpanElement>('[data-inert]');
    for (const el of items) {
      expect(el.getAttribute('aria-disabled')).toBe('true');
      expect(el.getAttribute('title') ?? '').toContain('OD-51');
    }
  });
  it('none of them is a disabled <button> - Chrome would eat the hover title', () => {
    const { container } = render(<WoFiltersRow {...props()} />);
    const disabled = container.querySelectorAll<HTMLButtonElement>('button[disabled]');
    expect(disabled).toHaveLength(0);
  });
  it('clicking one changes nothing - no handler, not merely a flag', () => {
    const p = props();
    const { container } = render(<WoFiltersRow {...p} />);
    for (const el of container.querySelectorAll<HTMLSpanElement>('[data-inert]')) {
      fireEvent.click(el);
    }
    expect(p.onSearchChange).not.toHaveBeenCalled();
    expect(p.onClosedChange).not.toHaveBeenCalled();
    expect(p.onArchiveChange).not.toHaveBeenCalled();
  });
  it('the chrome that would lie is not rendered at all (OD-52)', () => {
    render(<WoFiltersRow {...props()} />);
    expect(screen.queryByText('Summary')).toBeNull();
    expect(screen.queryByText(/ask|assistant/i)).toBeNull();
  });
});

describe('version', () => {
  it('WoFiltersRow.tsx is 1.0.0', () => {
    expect(VERSION).toBe('1.0.0');
  });
});
