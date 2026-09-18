/**
 * Azztec_SaaS_web_shell_rules_test_v1_0_1.ts  ->  web/src/features/shell/rules.test.ts
 * Version:  1.0.1   Date: 2026-09-19   Author: Adriaan
 * Spec:     Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md s5 . pair of rules.ts 1.0.0
 *
 * Zero network, zero DOM. The tables are asserted against the two view files' values (spec s2.2 / s2.3)
 * - name, key, glyph, colour, basis - so a typo in the port is a red test, not a screenshot diff.
 *
 * Changelog:
 *   1.0.1  Smoke fix, before the tag: the glyph assertion demanded an absolute moveto, but four of
 *          the 22 - build, construction, handyman, insights - open with a relative 'm' in the library.
 *          It now asserts a path command letter, which is what the claim was meant to be. The tables,
 *          the glyph data and the case count (12) are unchanged.
 *   1.0.0  Initial S1k. 12 cases.
 */
import { describe, expect, it } from 'vitest';

import { MATERIAL, VERSION as ICONS_VERSION } from './icons';
import {
  BRAND_MODE,
  HUB_TITLE,
  LOGOUT_TITLE,
  MENU_ACTIVE_COLOUR,
  MENU_GROUPS,
  MODULE_BUTTONS,
  PRINT_ITEM,
  RAIL_ITEMS,
  TIPS_TITLE,
  VERSION,
  activeKeyFor,
  gateOpen,
  inertTitle,
  menuActive,
  menuUnderline,
  printTarget,
  railBorder,
  underline,
} from './rules';

export const TEST_VERSION = '1.0.1';

describe('shell rules - the two views as data', () => {
  it('carries its version, and the icons module its own', () => {
    expect(VERSION).toBe('1.0.0');
    expect(ICONS_VERSION).toBe('1.0.0');
  });

  it('the six module buttons: name, key, glyph, colour, basis, in view order (HeaderToolbar s2.2)', () => {
    expect(MODULE_BUTTONS.map((b) => [b.name, b.key, b.icon, b.colour, b.labelBasis])).toEqual([
      ['BtnSchedulex', 'schedulex', 'event_note', '#9C27B0', 55],
      ['BtnPlannex', 'plannex', 'event_available', '#4CAF50', 55],
      ['BtnProcurex', 'procurex', 'shopping_cart', '#795548', 50],
      ['BtnPMx', 'pmx', 'build', '#607D8B', 28],
      ['BtnInvoicex', 'invoicex', 'receipt', '#00BCD4', 48],
      ['BtnMyReports', '', 'assessment', '#E91E63', 45],
    ]);
    // only Plannex navigates (OD-51); only Reports has no underline binding
    expect(MODULE_BUTTONS.filter((b) => b.live).map((b) => b.name)).toEqual(['BtnPlannex']);
    expect(MODULE_BUTTONS.filter((b) => !b.underline).map((b) => b.name)).toEqual(['BtnMyReports']);
  });

  it('the three pipe lists are the oracle strings, byte for byte', () => {
    expect(MENU_GROUPS.map((g) => g.label)).toEqual(['Application', 'Utilities', 'System']);
    expect(MENU_GROUPS[0].pipes).toBe(
      '|asset|part|meter|locationsetup|supplier|team|maintenance|wizard|pmx|timesheet|planning|schedulex|visualx|resetpassword|',
    );
    expect(MENU_GROUPS[1].pipes).toBe(
      '|pmrelease|rebuildpmwo|archiveworkorders|assetarchive|partarchive|customformsetup|',
    );
    expect(MENU_GROUPS[2].pipes).toBe(
      '|refcodesetup|usersettings|usermapping|systemsetup|useravailability|securitysetup|',
    );
  });

  it('menuActive: Application lights on pmx and schedulex, NOT on plannex (its list says "planning"); "" lights nothing', () => {
    const app = MENU_GROUPS[0].pipes;
    expect(menuActive(app, 'pmx')).toBe(true);
    expect(menuActive(app, 'schedulex')).toBe(true);
    expect(menuActive(app, 'visualx')).toBe(true);
    expect(menuActive(app, 'plannex')).toBe(false);
    expect(menuActive(app, 'planning')).toBe(true);
    expect(menuActive(app, '')).toBe(false);
    expect(menuActive(MENU_GROUPS[2].pipes, 'usersettings')).toBe(true);
    expect(menuActive(MENU_GROUPS[1].pipes, 'usersettings')).toBe(false);
  });

  it('the underline and border strings are the binding literals', () => {
    expect(MENU_ACTIVE_COLOUR).toBe('#EBC452');
    expect(menuUnderline(true)).toBe('2px solid #EBC452');
    expect(menuUnderline(false)).toBe('2px solid transparent');
    expect(underline('#4CAF50', true)).toBe('2px solid #4CAF50');
    expect(underline('#4CAF50', false)).toBe('2px solid transparent');
    expect(railBorder('#E91E63', true)).toBe('4px solid #E91E63');
    expect(railBorder('#E91E63', false)).toBe('4px solid transparent');
  });

  it('the thirteen rail items: name, glyph, colour, keys, in view order (SideMenu s2.3)', () => {
    expect(RAIL_ITEMS.map((r) => [r.name, r.icon, r.colour, r.keys.join(',')])).toEqual([
      ['MenuItem_Home', 'dashboard', '#DEBF7A', 'home'],
      ['MenuItem_Explorer', 'search', '#2196F3', 'explorer'],
      ['MenuItem_Assets', 'construction', '#FF9800', 'assets'],
      ['MenuItem_Labour', 'engineering', '#FF9800', 'labour'],
      ['MenuItem_WOMaint', 'assignment', '#E91E63', 'womaint'],
      ['MenuItem_WOWizard', 'flash_on', '#9C27B0', 'wowizard'],
      ['MenuItem_PMWizard', 'handyman', '#9C27B0', 'pmwizard'],
      ['MenuItem_VisualX', 'dashboard', '#4CAF50', 'visualx'],
      ['MenuItem_Insights', 'insights', '#DEBF7A', 'insights'],
      ['MenuItem_Supplier', 'local_shipping', '#00BCD4', 'supplier'],
      ['MenuItem_Parts', 'settings', '#009688', 'parts'],
      ['MenuItem_POList', 'featured_play_list', '#0B5ED7', 'purchaseorder'],
      ['MenuItem_Invoice', 'receipt_long', '#FFC107', 'invoicemaint,invoicex'],
    ]);
    expect(RAIL_ITEMS.filter((r) => r.dividerAfter).map((r) => r.name)).toEqual(['MenuItem_Home']);
    expect(PRINT_ITEM).toEqual({ name: 'MenuItem_Print', label: 'Print', icon: 'print', colour: '#AAAAAA' });
  });

  it('Insights lights in its own gold; everything else lights #E91E63; Invoice answers to two keys', () => {
    for (const r of RAIL_ITEMS) {
      expect(r.activeColour).toBe(r.name === 'MenuItem_Insights' ? '#DEBF7A' : '#E91E63');
    }
    const invoice = RAIL_ITEMS.find((r) => r.name === 'MenuItem_Invoice');
    expect(invoice?.keys).toEqual(['invoicemaint', 'invoicex']);
  });

  it('activeKeyFor: /planner (with or without a trailing slash) is plannex; anything else is ""', () => {
    expect(activeKeyFor('/planner')).toBe('plannex');
    expect(activeKeyFor('/planner/')).toBe('plannex');
    expect(activeKeyFor('/')).toBe('');
    expect(activeKeyFor('/plannerx')).toBe('');
    expect(activeKeyFor('')).toBe('');
  });

  it('printTarget is the SideMenu dispatcher: PO, the four WO spellings, and the browser for the rest', () => {
    expect(printTarget('purchaseorder')).toBe('POPrintPopup');
    expect(printTarget(' PurchaseOrder ')).toBe('POPrintPopup');
    for (const k of ['workorder', 'wo', 'womaint', 'workorders']) expect(printTarget(k)).toBe('WOPrintPopup');
    expect(printTarget('plannex')).toBe('browser');
    expect(printTarget('')).toBe('browser');
    expect(printTarget('home')).toBe('browser');
  });

  it('gateOpen: the rights gate is closed until rights exist (OD-52)', () => {
    expect(gateOpen(null)).toBe(true);
    expect(gateOpen('visualx')).toBe(false);
    expect(RAIL_ITEMS.filter((r) => gateOpen(r.gate)).length).toBe(12);
  });

  it('the brand is a constant (OD-53) and the inert titles say why (OD-51 / OD-34)', () => {
    expect(BRAND_MODE).toBe('AZZTEC');
    expect(inertTitle('Schedulex')).toBe('arrives with Schedulex (OD-51)');
    expect(inertTitle('the Application menu')).toBe('arrives with the Application menu (OD-51)');
    expect(HUB_TITLE).toBe('arrives with the Hub (OD-51)');
    expect(LOGOUT_TITLE).toBe('arrives with sign-in (OD-12)');
    expect(TIPS_TITLE).toBe('arrives with tips (item 33)');
  });

  it('every glyph the tables name exists in icons.tsx, with at least one path', () => {
    const named = new Set<string>([
      ...MODULE_BUTTONS.map((b) => b.icon),
      ...RAIL_ITEMS.map((r) => r.icon),
      PRINT_ITEM.icon,
      'search',
      'help_outline',
      'fullscreen',
      'group',
    ]);
    for (const n of named) {
      const paths = MATERIAL[n as keyof typeof MATERIAL];
      expect(paths.length, n).toBeGreaterThan(0);
      // a path opens with a command letter - four of the 22 use the relative moveto 'm', not 'M'
      for (const d of paths) expect(/^[MmLlHhVvCcSsQqTtAaZz]/.test(d), `${n}: ${d.slice(0, 12)}`).toBe(true);
    }
    expect(Object.keys(MATERIAL).length).toBe(22);
  });
});
