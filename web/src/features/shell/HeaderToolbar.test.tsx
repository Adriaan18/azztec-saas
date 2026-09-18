/**
 * Azztec_SaaS_web_shell_HeaderToolbar_test_v1_0_0.tsx  ->  web/src/features/shell/HeaderToolbar.test.tsx
 * Version:  1.0.0   Date: 2026-09-16   Author: Adriaan
 * Spec:     Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md s5 . pair of HeaderToolbar.tsx 1.0.0
 *
 * Zero network, zero fetch - nothing in the import graph reaches the client. The harness has no
 * setupFiles and no globals (Landmines s.C): explicit cleanup(), plain DOM assertions. jsdom reports a
 * colour set through a border shorthand on the longhand in rgb() form - asserted that way (S1i).
 *
 * Changelog:
 *   1.0.0  Initial S1k. 8 cases.
 */
import { cleanup, fireEvent, render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { HeaderToolbar, VERSION } from './HeaderToolbar';
import { AZZTEC_LOGO_URI } from './icons';

export const TEST_VERSION = '1.0.0';

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

function draw(activeKey: string, onPlannex = vi.fn(), onFullscreen = vi.fn()) {
  const r = render(
    <HeaderToolbar
      activeKey={activeKey}
      dateText="Sep 16"
      timeText="13:08:06"
      onPlannex={onPlannex}
      onFullscreen={onFullscreen}
    />,
  );
  return { ...r, onPlannex, onFullscreen };
}

describe('HeaderToolbar - the top dock (HeaderToolbar v16.47)', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.0.0');
  });

  it('renders the oracle components in view order, by data-name', () => {
    const { container } = draw('');
    expect(must(container, '.wm-hdr').getAttribute('data-name')).toBe('HeaderToolbar_v16_47');
    expect(names(container, '.wm-hdr > [data-name]')).toEqual([
      'AzztecLogo',
      'BrandBlock',
      'MenuApplication',
      'MenuUtilities',
      'MenuSystem',
      'SepMenuNav',
      'BtnSchedulex',
      'BtnPlannex',
      'BtnProcurex',
      'BtnPMx',
      'BtnInvoicex',
      'BtnMyReports',
      'Spacer',
      'RightControls',
    ]);
    expect(names(container, '[data-name="RightControls"] > [data-name]')).toEqual(['TipsToggle', 'ControlStack']);
    expect(names(container, '[data-name="topRow"] > [data-name]')).toEqual(['fsCoord', 'logoutCoord', 'dateLabel']);
    expect(names(container, '[data-name="bottomRow"] > [data-name]')).toEqual(['timeLabel']);
  });

  it('the AZZTEC brand: the logo src is the view data URI byte for byte, the wordmark reads Azztec, no Workmate parts', () => {
    const { container } = draw('');
    const logo = must(container, '[data-name="AzztecLogo"]');
    expect(logo.getAttribute('src')).toBe(AZZTEC_LOGO_URI);
    expect(AZZTEC_LOGO_URI.length).toBe(16706);
    expect(must(container, '[data-name="lblBrandNameAzztec"]').textContent).toBe('Azztec');
    expect(container.querySelector('[data-name="WorkmateLogo"]')).toBeNull();
    expect(container.querySelector('[data-name="AMMSSpine"]')).toBeNull();
    expect(container.querySelector('[data-name="lblBrandName"]')).toBeNull();
  });

  it('on plannex: Plannex underlines in its green, the other buttons stay transparent, Reports has no border, no menu lights', () => {
    const { container } = draw('plannex');
    const plannex = must(container, '[data-name="BtnPlannex"]');
    expect(plannex.getAttribute('data-active')).toBe('1');
    expect(plannex.style.borderBottomColor).toBe('rgb(76, 175, 80)');
    expect(plannex.style.borderBottomWidth).toBe('2px');
    for (const n of ['BtnSchedulex', 'BtnProcurex', 'BtnPMx', 'BtnInvoicex']) {
      const b = must(container, `[data-name="${n}"]`);
      expect(b.getAttribute('data-active')).toBe('0');
      expect(b.style.borderBottomColor).toBe('transparent');
    }
    const reports = must(container, '[data-name="BtnMyReports"]');
    expect(reports.getAttribute('data-active')).toBe('0');
    expect(reports.getAttribute('style')).toBeNull();
    for (const n of ['MenuApplication', 'MenuUtilities', 'MenuSystem']) {
      expect(must(container, `[data-name="${n}"]`).style.borderBottomColor).toBe('transparent');
    }
    // and on pmx the Application menu lights, Plannex does not
    const two = draw('pmx');
    expect(must(two.container, '[data-name="MenuApplication"]').style.borderBottomColor).toBe('rgb(235, 196, 82)');
    expect(must(two.container, '[data-name="BtnPlannex"]').getAttribute('data-active')).toBe('0');
  });

  it('Plannex is a link: click and Enter each call onPlannex once; Space does not', () => {
    const { container, onPlannex } = draw('');
    const plannex = must(container, '[data-name="BtnPlannex"]');
    expect(plannex.getAttribute('role')).toBe('link');
    expect(plannex.getAttribute('tabindex')).toBe('0');
    fireEvent.click(plannex);
    expect(onPlannex).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(plannex, { key: 'Enter' });
    expect(onPlannex).toHaveBeenCalledTimes(2);
    fireEvent.keyDown(plannex, { key: ' ' });
    expect(onPlannex).toHaveBeenCalledTimes(2);
  });

  it('every inert control carries aria-disabled and a title that says what it waits for, and a click does nothing', () => {
    const { container, onPlannex, onFullscreen } = draw('');
    const expectInert = (name: string, title: string) => {
      const el = must(container, `[data-name="${name}"]`);
      expect(el.getAttribute('aria-disabled'), name).toBe('true');
      expect(el.getAttribute('title'), name).toBe(title);
      expect(el.className.split(' '), name).toContain('inert');
      fireEvent.click(el);
    };
    expectInert('AzztecLogo', 'arrives with the Hub (OD-51)');
    expectInert('MenuApplication', 'arrives with the Application menu (OD-51)');
    expectInert('MenuUtilities', 'arrives with the Utilities menu (OD-51)');
    expectInert('MenuSystem', 'arrives with the System menu (OD-51)');
    expectInert('BtnSchedulex', 'arrives with Schedulex (OD-51)');
    expectInert('BtnProcurex', 'arrives with Procurex (OD-51)');
    expectInert('BtnPMx', 'arrives with PMx (OD-51)');
    expectInert('BtnInvoicex', 'arrives with Invoicex (OD-51)');
    expectInert('BtnMyReports', 'arrives with Reports (OD-51)');
    expectInert('TipsToggle', 'arrives with tips (item 33)');
    expectInert('logoutBtn', 'arrives with sign-in (OD-12)');
    expect(onPlannex).not.toHaveBeenCalled();
    expect(onFullscreen).not.toHaveBeenCalled();
  });

  it('the gated controls are not rendered (OD-52); tips draws in its no-prefs state', () => {
    const { container } = draw('');
    expect(container.querySelector('[data-name="VXSearchPill"]')).toBeNull();
    expect(container.querySelector('[data-name="userCoord"]')).toBeNull();
    expect(container.querySelector('[data-name="userBtn"]')).toBeNull();
    expect(must(container, '[data-name="TipsToggle"]').className).toBe('tips on inert');
  });

  it('the clock strings render as given, and fsBtn calls onFullscreen', () => {
    const { container, onFullscreen } = draw('');
    expect(must(container, '[data-name="dateLabel"]').textContent).toBe('Sep 16');
    expect(must(container, '[data-name="timeLabel"]').textContent).toBe('13:08:06');
    fireEvent.click(must(container, '[data-name="fsBtn"]'));
    expect(onFullscreen).toHaveBeenCalledTimes(1);
  });
});
