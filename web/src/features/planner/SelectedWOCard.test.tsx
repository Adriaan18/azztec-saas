/**
 * Azztec_SaaS_web_planner_SelectedWOCard_test_v1_1_2.tsx  ->  web/src/features/planner/SelectedWOCard.test.tsx
 * Version:  1.1.2   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md §6 (SelectedWOCard.test.tsx row) · OD-5, OD-34
 *
 * Zero network, zero fetch by import graph. Explicit cleanup(), plain DOM assertions. The absent
 * affordances are asserted absent - a card that grew a `+ person` link by accident would be a write
 * surface in a read-only slice.
 *
 * Changelog:
 *   1.1.2  Smoke fix, before the tag. `importOriginal<typeof import('...')>()` is an inline import()
 *          type, which the repo forbids (consistent-type-imports). The module is imported as a
 *          type-only namespace at the top instead, and the generic points at that. Same mock.
 *   1.1.1  Smoke fix, before the tag. The vi.mock sat between the imports, which put three imports
 *          after a statement (import/first, 3 lint errors). vi.mock is hoisted by Vitest regardless
 *          of where it is written, so it lives below the import block now. It also spreads
 *          importOriginal, so nothing but Link is replaced.
 *   1.1.0  W1b: the Open control is a Link now, so OD-5's disabled case is replaced by a live-link
 *          case. @tanstack/react-router is mocked to a plain <a> rather than standing a memory
 *          router up: this is a unit test of one card, and the mock lets it assert the `to` and
 *          `params` the card hands the router - which is the actual contract - without the route
 *          tree. The router's own resolution is covered by the smoke's click-through (spec s7.7).
 *   1.0.1  Lint: Element.textContent is `string` on TS 6 lib.dom, so `?? ''` was an unnecessary
 *          condition. getAttribute() is still `string | null`; that `??` stays.
 *   1.0.0  Initial S1g.
 */
import { cleanup, fireEvent, render } from '@testing-library/react';
import type { ReactNode } from 'react';
import type * as ReactRouter from '@tanstack/react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';


import { SelectedWOCard, VERSION } from './SelectedWOCard';
import { PIN_105, PM_102, RANGE, REQ_103, WORKERS, WO_101 } from './range.fixture';
import { indexWorkers } from './rules';

/**
 * Link needs a RouterProvider and there is none here by design. importOriginal keeps every other
 * export real, so only Link is swapped - for a plain <a> carrying `to` and `params` as data
 * attributes, which is the contract the card owes the router. The router's own resolution is
 * covered by the smoke's click-through.
 */
vi.mock('@tanstack/react-router', async (importOriginal) => ({
  ...(await importOriginal<typeof ReactRouter>()),
  Link: ({
    children,
    to,
    params,
    className,
    ...rest
  }: {
    children: ReactNode;
    to: string;
    params: Record<string, string>;
    className?: string;
  }) => (
    <a className={className} data-params={JSON.stringify(params)} data-to={to} href="#" {...rest}>
      {children}
    </a>
  ),
}));

export const TEST_VERSION = '1.1.2';

afterEach(() => {
  cleanup();
});

function must(root: ParentNode, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

const byId = indexWorkers(WORKERS);

function kv(root: ParentNode): Record<string, string> {
  const out: Record<string, string> = {};
  for (const v of Array.from(root.querySelectorAll('.kv .v'))) out[v.getAttribute('data-k') ?? '?'] = v.textContent;
  return out;
}

describe('SelectedWOCard - the read-only card (oracle renderSelected)', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.1.0');
  });

  it('nothing selected: the oracle empty line, no kv, no actions', () => {
    const { container } = render(<SelectedWOCard wo={null} labour={[]} byId={byId} onClear={vi.fn()} />);
    const card = must(container, '.card.selc');
    expect(card.getAttribute('data-wo')).toBe('0');
    expect(must(card, 'h3').textContent).toBe('SELECTED WO');
    expect(must(card, '.empty').textContent).toBe('Click a work order.');
    expect(card.querySelector('.kv')).toBeNull();
    expect(card.querySelector('.actions')).toBeNull();
  });

  it('the labour WO: badge, title line, every kv row, two labour rows, no write affordances', () => {
    const { container } = render(<SelectedWOCard wo={WO_101} labour={RANGE.labour} byId={byId} onClear={vi.fn()} />);
    const card = must(container, '.card.selc');
    expect(card.getAttribute('data-wo')).toBe('101');
    expect(must(card, 'h3 .badge').className).toBe('badge WO');
    expect(must(card, '.t').textContent).toBe('WO-101 \u00b7 Replace chain on infeed');
    expect(Array.from(card.querySelectorAll('.kv .k')).map((k) => k.textContent)).toEqual([
      'Status',
      'Start',
      'End',
      'Priority',
      'Asset',
      'Location',
      'Hours',
      'Responsible',
    ]);
    expect(kv(card)).toEqual({
      status: 'Planned \u00b7 PO linked',
      start: 'Mon 14 Sep 2026',
      end: 'Tue 15 Sep 2026 (2 days)',
      priority: 'P1',
      asset: 'INF-01 \u00b7 Infeed conveyor',
      location: 'SAW \u00b7 Sawmill',
      hours: '3.5h (labour)',
      responsible: 'nobody',
    });
    expect(must(card, '[data-k="asset"]').getAttribute('title')).toBe('Infeed conveyor');
    expect(must(card, '[data-k="location"]').getAttribute('title')).toBe('Sawmill');
    expect(must(card, '.sub').textContent).toBe('PLANNED LABOUR');
    const labs = card.querySelectorAll('.lab');
    expect(labs).toHaveLength(2);
    expect(labs[0].textContent).toBe('Jo Bloggs Fitter2.5h \u00b7 2026-09-14');
    expect(must(labs[0], 'small').textContent).toBe(' Fitter');
    expect(labs[1].textContent).toBe('Ann Kowhai1h');
    expect(card.querySelector('.lab .x')).toBeNull();
    expect(card.textContent).not.toContain('+ person');
    expect(card.textContent).not.toContain('Unpin');
    expect(card.querySelector('.orb')).toBeNull();
  });

  it('the locked PM: engine owned, no estimate yet, responsible named, nobody planned', () => {
    const { container } = render(<SelectedWOCard wo={PM_102} labour={RANGE.labour} byId={byId} onClear={vi.fn()} />);
    const card = must(container, '.card.selc');
    expect(must(card, 'h3 .badge').className).toBe('badge PM');
    const rows = kv(card);
    expect(rows.status).toBe('Planned \u00b7 engine owned');
    expect(rows.priority).toBe('\u2014');
    expect(rows.hours).toBe('no estimate yet');
    expect(must(card, '[data-k="hours"] .none')).toBeTruthy();
    expect(rows.responsible).toBe('Ann Kowhai (WO owner - not planned hours)');
    expect(card.querySelector('[data-k="end"]')).toBeNull();
    expect(card.querySelector('[data-k="asset"]')).toBeNull();
    expect(card.querySelector('[data-k="pin"]')).toBeNull();
    expect(card.querySelectorAll('.lab')).toHaveLength(0);
    expect(must(card, '.empty').textContent).toBe('nobody planned yet');
  });

  it('the pinned PM shows the Pin row; the REQ shows N/A and estimate hours', () => {
    const { container } = render(<SelectedWOCard wo={PIN_105} labour={RANGE.labour} byId={byId} onClear={vi.fn()} />);
    const rows = kv(container);
    expect(rows.status).toBe('Planned \u00b7 pinned');
    expect(rows.pin).toBe('since 2026-09-10 \u00b7 engine date 2026-09-25');
    expect(rows.hours).toBe('1h (estimate)');
    cleanup();
    const r2 = render(<SelectedWOCard wo={REQ_103} labour={RANGE.labour} byId={byId} onClear={vi.fn()} />);
    expect(kv(r2.container)).toMatchObject({ priority: 'N/A', hours: '2h (estimate)', status: 'Request' });
  });

  it('Clear calls onClear and is now the only button in .actions', () => {
    const onClear = vi.fn();
    const { container } = render(<SelectedWOCard wo={WO_101} labour={RANGE.labour} byId={byId} onClear={onClear} />);
    const buttons = container.querySelectorAll('.actions button');
    expect(buttons).toHaveLength(1);
    fireEvent.click(buttons[0]);
    expect(onClear).toHaveBeenCalledTimes(1);
  });

  it('Open in WO Maintenance is a live link to /workorders/$id - OD-5 closed', () => {
    const { container } = render(
      <SelectedWOCard wo={WO_101} labour={RANGE.labour} byId={byId} onClear={vi.fn()} />,
    );
    const open = must(container, '.actions a');
    expect(open.textContent).toBe('Open in WO Maintenance');
    expect(open.className).toBe('gold');
    expect(open.getAttribute('data-to')).toBe('/workorders/$id');
    expect(open.getAttribute('data-params')).toBe(JSON.stringify({ id: String(WO_101.id) }));
    expect(open.getAttribute('data-open-wo')).toBe(String(WO_101.id));
  });

  it('the Open link is no longer disabled chrome - no disabled button remains', () => {
    const { container } = render(
      <SelectedWOCard wo={WO_101} labour={RANGE.labour} byId={byId} onClear={vi.fn()} />,
    );
    expect(container.querySelectorAll('button[disabled]')).toHaveLength(0);
  });
});
