/**
 * Azztec_SaaS_web_workorders_symbols_test_v1_0_2.tsx  ->  web/src/features/workorders/symbols.test.tsx
 * Version:  1.0.2   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §5 · pair of symbols.tsx + icons.tsx 1.0.0
 *
 * Landmines §C throughout: cleanup() in afterEach (there is no setupFiles and adding one would touch
 * every existing test), no jest-dom matchers, the generic passed to querySelectorAll rather than a
 * cast (TS 6's lib.dom is narrower), and colours asserted as jsdom reports them - rgb()/rgba(), never
 * the hex (the S1i lesson).
 *
 * Changelog:
 *   1.0.2  symbols.tsx is 1.0.2. Only the version pin moved - 26 cases, all unchanged. (The pin means
 *          a patch to the module always costs a patch here; that is the price of asserting it.)
 *   1.0.1  Smoke fix, before the tag. The 13-glyph assertion passed while the status row threw on a
 *          14th glyph it needed, because nothing tied the CARD TABLE to the glyph record. The new
 *          case walks WO_STATUS_CARDS and resolves each icon through GLYPHS - the assertion the
 *          old one only looked like. 25 -> 26.
 *   1.0.0  Initial W1b. 25 cases.
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import {
  ASSIGNMENT,
  GLYPHS,
  SEARCH,
  SHELL_VIEWBOX,
  VERSION as ICONS_VERSION,
  VIEW_BOX,
  WO_MATERIAL,
} from './icons';
import { recordFixture } from './record.fixture';
import { WO_STATUS_CARDS } from './rules';
import { CompleteWithinSeg, VERSION, WoNumBadge, WoProgressRow, WoStatusRow } from './symbols';

export const TEST_VERSION = '1.0.2';

afterEach(() => {
  cleanup();
});

describe('icons.tsx - copied, not typed', () => {
  it('carries exactly the 13 glyphs the shell does not', () => {
    expect(Object.keys(WO_MATERIAL).sort()).toEqual([
      'block',
      'cancel',
      'check_circle',
      'clear_all',
      'close',
      'edit',
      'group_add',
      'local_printshop',
      'play_circle_filled',
      'save',
      'schedule',
      'thumb_up',
      'warning',
    ]);
  });
  it('every glyph is a non-empty path list and schedule is the two-path one', () => {
    for (const [name, paths] of Object.entries(WO_MATERIAL)) {
      expect(paths.length, name).toBeGreaterThan(0);
      for (const d of paths) expect(d.length, name).toBeGreaterThan(20);
    }
    expect(WO_MATERIAL.schedule).toHaveLength(2);
  });
  it('every glyph WO_STATUS_CARDS names resolves to real paths through GLYPHS', () => {
    for (const c of WO_STATUS_CARDS) {
      const paths = GLYPHS[c.icon];
      expect(paths, `${c.code} -> ${c.icon}`).toBeDefined();
      expect(paths.length, `${c.code} -> ${c.icon}`).toBeGreaterThan(0);
    }
  });
  it('agrees with the shell on the viewBox, so the two files stay diffable', () => {
    expect(VIEW_BOX).toBe('0 0 24 24');
    expect(VIEW_BOX).toBe(SHELL_VIEWBOX);
  });
  it('re-exports assignment and search rather than duplicating them', () => {
    expect(ASSIGNMENT.length).toBeGreaterThan(0);
    expect(SEARCH.length).toBeGreaterThan(0);
    expect(Object.keys(WO_MATERIAL)).not.toContain('assignment');
    expect(Object.keys(WO_MATERIAL)).not.toContain('search');
  });
});

describe('WoNumBadge', () => {
  it('renders the short id, not the composite', () => {
    render(<WoNumBadge value="V|3CL-260826-010|6|1" />);
    expect(screen.getByText('3CL-260826-010')).toBeTruthy();
  });
  it('paints the active pair as jsdom reports it', () => {
    const { container } = render(<WoNumBadge value="V|X|6|0" />);
    const el = container.querySelector<HTMLSpanElement>('.wo-badge');
    expect(el?.style.backgroundColor).toBe('rgba(40, 167, 69, 0.16)');
    expect(el?.style.color).toBe('rgba(40, 167, 69, 0.8)');
  });
  it('emits both background layers even with no PO', () => {
    const { container } = render(<WoNumBadge value="V|X|6|0" />);
    const img = container.querySelector<HTMLSpanElement>('.wo-badge')?.style.backgroundImage ?? '';
    expect(img.split('gradient').length - 1).toBe(2);
    expect(img).toContain('transparent 55%');
  });
  it('shows the blue dot when the WO has a PO', () => {
    const { container } = render(<WoNumBadge value="V|X|6|1" />);
    const img = container.querySelector<HTMLSpanElement>('.wo-badge')?.style.backgroundImage ?? '';
    expect(img).toContain('rgb(11, 94, 215)');
  });
  it('renders nothing visible for an empty value but does not crash', () => {
    const { container } = render(<WoNumBadge value="" />);
    expect(container.querySelector('.wo-badge')?.textContent).toBe('');
  });
});

describe('WoStatusRow - eight cards (OD-74)', () => {
  it('draws eight cards, never nine', () => {
    const { container } = render(<WoStatusRow status="V" />);
    expect(container.querySelectorAll('.wo-symcard')).toHaveLength(8);
  });
  it('lights exactly the matching card', () => {
    const { container } = render(<WoStatusRow status="V" />);
    const lit = container.querySelectorAll<HTMLDivElement>('[data-lit="true"]');
    expect(lit).toHaveLength(1);
    expect(lit[0].getAttribute('data-code')).toBe('V');
    expect(lit[0].style.backgroundColor).toBe('rgb(40, 167, 69)');
  });
  it('lights nothing for F - the oracle has no Deferred card', () => {
    const { container } = render(<WoStatusRow status="F" />);
    expect(container.querySelectorAll('[data-lit="true"]')).toHaveLength(0);
    expect(container.querySelectorAll('.wo-symcard')).toHaveLength(8);
  });
  it('lights nothing for an empty status', () => {
    const { container } = render(<WoStatusRow status="" />);
    expect(container.querySelectorAll('[data-lit="true"]')).toHaveLength(0);
  });
  it('R is the dark-text card when lit', () => {
    const { container } = render(<WoStatusRow status="R" />);
    const lit = container.querySelector<HTMLDivElement>('[data-lit="true"]');
    expect(lit?.style.color).toBe('rgb(0, 0, 0)');
  });
  it('a lit card that is not R takes white text', () => {
    const { container } = render(<WoStatusRow status="C" />);
    expect(container.querySelector<HTMLDivElement>('[data-lit="true"]')?.style.color).toBe(
      'rgb(255, 255, 255)',
    );
  });
  it('shows all eight labels in card order', () => {
    render(<WoStatusRow status="V" />);
    for (const c of WO_STATUS_CARDS) expect(screen.getByText(c.label)).toBeTruthy();
  });
});

describe('WoProgressRow - one card per active row (OD-75)', () => {
  const all = recordFixture().progressAll;

  it("draws eight cards on RST's eight active rows", () => {
    const { container } = render(<WoProgressRow prog={6} progressAll={all} />);
    expect(container.querySelectorAll('.wo-symcard')).toHaveLength(8);
  });
  it('lights the 100% card green, not the standard slate', () => {
    const { container } = render(<WoProgressRow prog={6} progressAll={all} />);
    const lit = container.querySelector<HTMLDivElement>('[data-lit="true"]');
    expect(lit?.getAttribute('data-progress')).toBe('6');
    expect(lit?.style.backgroundColor).toBe('rgb(22, 163, 74)');
  });
  it('lights any other card slate', () => {
    const { container } = render(<WoProgressRow prog={3} progressAll={all} />);
    expect(container.querySelector<HTMLDivElement>('[data-lit="true"]')?.style.backgroundColor).toBe(
      'rgb(61, 79, 82)',
    );
  });
  it('lights 7 Scheduled and draws it without a symbol - the plain card', () => {
    const { container } = render(<WoProgressRow prog={7} progressAll={all} />);
    const lit = container.querySelector<HTMLDivElement>('[data-lit="true"]');
    expect(lit?.getAttribute('data-progress')).toBe('7');
    expect(lit?.querySelector('svg')).toBeNull();
    expect(screen.getByText('Scheduled')).toBeTruthy();
  });
  it('the quarter cards letter 1 2 3, not 25 50 75', () => {
    render(<WoProgressRow prog={0} progressAll={all} />);
    expect(screen.getByText('1')).toBeTruthy();
    expect(screen.getByText('2')).toBeTruthy();
    expect(screen.getByText('3')).toBeTruthy();
    expect(screen.getByText('25%')).toBeTruthy();
  });
  it('prog 0 lights nothing', () => {
    const { container } = render(<WoProgressRow prog={0} progressAll={all} />);
    expect(container.querySelectorAll('[data-lit="true"]')).toHaveLength(0);
  });
});

describe('CompleteWithinSeg - read-only in W1b (OD-79)', () => {
  it('draws six segments and marks the record value', () => {
    const { container } = render(<CompleteWithinSeg value="week" />);
    expect(container.querySelectorAll('.wo-seg-item')).toHaveLength(6);
    const on = container.querySelectorAll<HTMLSpanElement>('.wo-seg-item.on');
    expect(on).toHaveLength(1);
    expect(on[0].getAttribute('data-seg')).toBe('week');
  });
  it('every segment is inert with an OD-51 title and no button role', () => {
    const { container } = render(<CompleteWithinSeg value="range" />);
    const items = container.querySelectorAll<HTMLSpanElement>('.wo-seg-item');
    for (const el of items) {
      expect(el.getAttribute('aria-disabled')).toBe('true');
      expect((el.getAttribute('title') ?? '').length).toBeGreaterThan(0);
    }
    expect(container.querySelectorAll('button')).toHaveLength(0);
  });
});

describe('version', () => {
  it('symbols.tsx is 1.0.2 and icons.tsx is 1.0.1', () => {
    expect(VERSION).toBe('1.0.2');
    expect(ICONS_VERSION).toBe('1.0.1');
  });
});
