/**
 * Azztec_SaaS_web_planner_CapacityBar_test_v1_0_0.tsx  ->  web/src/features/planner/CapacityBar.test.tsx
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §6 (CapacityBar.test.tsx row) · OD-25 · pair rule
 *
 * The first test in this file is the OD-25 pin: pct 1000 must render a FULL bar in the over colour,
 * and the number must survive to the label. The smoke backs it with a screenshot of worker 692 on
 * RST (10 h against 1 h/week, verified 2026-09-12) - a passing assertion and a picture, because this
 * is the one place a "sensible" clamp would quietly lie to a planner.
 *
 * No jest-dom on the box: style.width and className are read straight off the node.
 *
 * Changelog:
 *   1.0.0  Initial S1f.
 */
import { cleanup, render } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { CapacityBar, VERSION, WeekStrip } from './CapacityBar';
import { FROM, TO, WORKERS, WOS } from './range.fixture';

export const TEST_VERSION = '1.0.0';

afterEach(() => {
  cleanup();
});

function must(root: HTMLElement, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

describe('CapacityBar - OD-25', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.0.0');
  });

  it('1000% is a FULL bar in the over colour - the width clamps, the number does not', () => {
    const { container } = render(<CapacityBar pct={1000} />);
    const i = must(container, '.bar i');
    expect(i.className).toBe('over');
    expect(i.style.width).toBe('100%');
  });

  it('2400% behaves the same (RST worker 80)', () => {
    const { container } = render(<CapacityBar pct={2400} />);
    expect(must(container, '.bar i').style.width).toBe('100%');
  });

  it('90% is ok, 10% is neutral, 0% is an empty bar', () => {
    const { container } = render(
      <div>
        <div id="a">
          <CapacityBar pct={90} />
        </div>
        <div id="b">
          <CapacityBar pct={10} />
        </div>
        <div id="c">
          <CapacityBar pct={0} />
        </div>
      </div>,
    );
    expect(must(container, '#a .bar i').className).toBe('ok');
    expect(must(container, '#a .bar i').style.width).toBe('90%');
    expect(must(container, '#b .bar i').className).toBe('');
    expect(must(container, '#b .bar i').style.width).toBe('10%');
    expect(must(container, '#c .bar i').style.width).toBe('0%');
  });
});

describe('WeekStrip - the week capacity strip (oracle stripEl)', () => {
  it('the fixture week: planned / capacity, the bar, and the unknown-hours line', () => {
    const { container } = render(<WeekStrip weekStart={FROM} weekEnd={TO} wos={WOS} cap={41} workers={WORKERS} />);
    const strip = must(container, '.strip');
    expect(must(strip, '.n').textContent).toBe('10.5 / 41 h');
    expect(must(strip, '.bar i').className).toBe('');
    expect(must(strip, '.bar i').style.width).toBe('26%');
    expect(must(strip, '.u').textContent).toBe('+1 WO no hrs');
    expect(strip.querySelector('.w')).toBeNull();
    expect(strip.getAttribute('title')).toBe(
      'Week of Mon 14 Sep 2026\nplanned 10.5 h of 41 h capacity (2 workers)\n1 WO have no hours yet',
    );
  });

  it('with no unknown-hours WO it shows the count line with the pct', () => {
    const wos = WOS.filter((w) => w.hrs > 0);
    const { container } = render(<WeekStrip weekStart={FROM} weekEnd={TO} wos={wos} cap={41} workers={WORKERS} />);
    expect(must(container, '.w').textContent).toBe('4 WO \u00b7 26%');
    expect(container.querySelector('.u')).toBeNull();
  });

  it('capacity 0 renders ? h and drops the pct from the count line (never NaN)', () => {
    const wos = WOS.filter((w) => w.hrs > 0);
    const { container } = render(<WeekStrip weekStart={FROM} weekEnd={TO} wos={wos} cap={0} workers={[]} />);
    expect(must(container, '.n').textContent).toBe('10.5 / ? h');
    expect(must(container, '.w').textContent).toBe('4 WO');
    expect(must(container, '.bar i').style.width).toBe('0%');
  });

  it('an empty week shows 0, and a week with WOs but no hours shows ?', () => {
    const { container } = render(
      <div>
        <div id="empty">
          <WeekStrip weekStart="2026-09-21" weekEnd="2026-09-27" wos={WOS} cap={41} workers={WORKERS} />
        </div>
        <div id="nohrs">
          <WeekStrip weekStart={FROM} weekEnd={TO} wos={WOS.filter((w) => w.hrs === 0)} cap={41} workers={WORKERS} />
        </div>
      </div>,
    );
    expect(must(container, '#empty .n').textContent).toBe('0 / 41 h');
    expect(must(container, '#nohrs .n').textContent).toBe('? / 41 h');
  });
});
