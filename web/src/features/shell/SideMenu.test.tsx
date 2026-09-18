/**
 * Azztec_SaaS_web_shell_SideMenu_test_v1_0_1.tsx  ->  web/src/features/shell/SideMenu.test.tsx
 * Version:  1.0.1   Date: 2026-09-19   Author: Adriaan
 * Spec:     Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md s5 . pair of SideMenu.tsx 1.0.0
 *
 * Zero network. No setupFiles / globals: explicit cleanup(), plain DOM assertions, colours in rgb().
 *
 * Changelog:
 *   1.0.1  Smoke fix, before the tag: querySelectorAll now takes its element type as a generic instead
 *          of an assertion afterwards. With the assertion there TypeScript infers the same type FROM it,
 *          so no-unnecessary-type-assertion was right. Six cases, unchanged.
 *   1.0.0  Initial S1k. 6 cases.
 */
import { cleanup, fireEvent, render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { SideMenu, VERSION } from './SideMenu';

export const TEST_VERSION = '1.0.1';

afterEach(() => {
  cleanup();
});

function must(root: HTMLElement, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

function names(root: HTMLElement, sel: string): Array<string> {
  return Array.from(root.querySelectorAll(sel)).map((e) => e.getAttribute('data-name') ?? '');
}

describe('SideMenu - the left dock (SideMenu v4.20)', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.0.0');
  });

  it('twelve items and Print in view order, VisualX absent (OD-52), the dividers where the oracle puts them', () => {
    const { container } = render(<SideMenu activeKey="" onPrint={vi.fn()} />);
    expect(must(container, '.wm-rail').getAttribute('data-name')).toBe('SideMenu_v4_20');
    expect(names(container, '[data-name="NavContainer"] > [data-name]')).toEqual([
      'MenuItem_Home',
      'Divider1',
      'MenuItem_Explorer',
      'MenuItem_Assets',
      'MenuItem_Labour',
      'MenuItem_WOMaint',
      'MenuItem_WOWizard',
      'MenuItem_PMWizard',
      'MenuItem_Insights',
      'MenuItem_Supplier',
      'MenuItem_Parts',
      'MenuItem_POList',
      'MenuItem_Invoice',
    ]);
    expect(names(container, '[data-name="BottomContainer"] > [data-name]')).toEqual(['Divider2', 'MenuItem_Print']);
    expect(container.querySelector('[data-name="MenuItem_VisualX"]')).toBeNull();
    expect(must(container, '[data-name="MenuItem_WOMaint"] .lbl').textContent).toBe('WO Maint');
  });

  it('plannex lights nothing on the rail - every border is transparent (as at KT)', () => {
    const { container } = render(<SideMenu activeKey="plannex" onPrint={vi.fn()} />);
    const items = Array.from(container.querySelectorAll<HTMLElement>('.nav .item'));
    expect(items.length).toBe(12);
    for (const el of items) {
      expect(el.getAttribute('data-active')).toBe('0');
      expect(el.style.borderLeftColor).toBe('transparent');
      expect(el.style.borderLeftWidth).toBe('4px');
    }
  });

  it('insights lights in gold, invoicex lights Invoice (its second key), womaint lights WO Maint in pink', () => {
    const a = render(<SideMenu activeKey="insights" onPrint={vi.fn()} />);
    const insights = must(a.container, '[data-name="MenuItem_Insights"]');
    expect(insights.getAttribute('data-active')).toBe('1');
    expect(insights.style.borderLeftColor).toBe('rgb(222, 191, 122)');
    expect(must(a.container, '[data-name="MenuItem_Home"]').style.borderLeftColor).toBe('transparent');
    cleanup();
    const b = render(<SideMenu activeKey="invoicex" onPrint={vi.fn()} />);
    expect(must(b.container, '[data-name="MenuItem_Invoice"]').style.borderLeftColor).toBe('rgb(233, 30, 99)');
    cleanup();
    const c = render(<SideMenu activeKey="womaint" onPrint={vi.fn()} />);
    expect(must(c.container, '[data-name="MenuItem_WOMaint"]').getAttribute('data-active')).toBe('1');
    expect(must(c.container, '[data-name="MenuItem_WOMaint"]').style.borderLeftColor).toBe('rgb(233, 30, 99)');
  });

  it('every rail item is inert with its title; Print is live and calls onPrint', () => {
    const onPrint = vi.fn();
    const { container } = render(<SideMenu activeKey="" onPrint={onPrint} />);
    for (const [name, label] of [
      ['MenuItem_Home', 'Home'],
      ['MenuItem_Explorer', 'Explorer'],
      ['MenuItem_Labour', 'Labour'],
      ['MenuItem_WOMaint', 'WO Maint'],
      ['MenuItem_PMWizard', 'PM Wizard'],
      ['MenuItem_Invoice', 'Invoice'],
    ]) {
      const el = must(container, `[data-name="${name}"]`);
      expect(el.getAttribute('aria-disabled'), name).toBe('true');
      expect(el.getAttribute('title'), name).toBe(`arrives with ${label} (OD-51)`);
      fireEvent.click(el);
    }
    expect(onPrint).not.toHaveBeenCalled();
    const print = must(container, '[data-name="MenuItem_Print"]');
    expect(print.tagName).toBe('BUTTON');
    expect(print.getAttribute('aria-disabled')).toBeNull();
    fireEvent.click(print);
    expect(onPrint).toHaveBeenCalledTimes(1);
  });

  it('glyphs paint in the view colours: Home gold, Parts teal, Print grey', () => {
    const { container } = render(<SideMenu activeKey="" onPrint={vi.fn()} />);
    expect(must(container, '[data-name="MenuItem_Home"] svg').getAttribute('fill')).toBe('#DEBF7A');
    expect(must(container, '[data-name="MenuItem_Parts"] svg').getAttribute('fill')).toBe('#009688');
    expect(must(container, '[data-name="MenuItem_Print"] svg').getAttribute('fill')).toBe('#AAAAAA');
    expect(must(container, '[data-name="MenuItem_Home"] svg').getAttribute('width')).toBe('19');
  });
});
