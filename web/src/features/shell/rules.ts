/**
 * Azztec_SaaS_web_shell_rules_v1_0_0.ts  ->  web/src/features/shell/rules.ts
 * Version:  1.0.0   Date: 2026-09-16   Author: Adriaan
 * Spec:     Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md s3.1 . OD-50, OD-51, OD-52, OD-53
 * Oracle:   Workmate/Navigation/HeaderToolbar v16.47 and Workmate/Navigation/SideMenu v4.20
 *           (docs/reference/HeaderToolbar_2026-09-16_view.json, SideMenu_2026-09-16_view.json) - every
 *           value below is read from a component's props / propConfig in those files, keyed by the
 *           oracle's own meta.name so a screenshot, DevTools and the JSON line up 1:1.
 *
 * Pure: no Date, no DOM, no React. The tables are the two views as data; the functions are the four
 * expression bindings (menu underline, module underline, rail border, rights gate), the active-key
 * rule the router path replaces session.custom.activePage with, and the Print dispatcher.
 *
 * What is deliberately NOT here: the three menu popups, tips, rights, roles, the brand read, the AI
 * navigator bridge, the legacy toolbar-state handlers, nav-active messaging (spec s1, cut at the audit).
 *
 * Changelog:
 *   1.0.0  Initial S1k.
 */
export const VERSION = '1.0.0';

export type BrandMode = 'AZZTEC' | 'WORKMATE';

/**
 * OD-53. KT reads this from dbo.System_Configuration through workmate.brand.get_mode() (row absent ->
 * 'WORKMATE'; KT's row and its session default both say 'AZZTEC'). The read is its own slice; until
 * then the product's name is the constant.
 */
export const BRAND_MODE: BrandMode = 'AZZTEC';

/** the 22 material/<name> glyphs the two views reference (icons.tsx carries the paths) */
export type IconName =
  | 'event_note'
  | 'event_available'
  | 'shopping_cart'
  | 'build'
  | 'receipt'
  | 'assessment'
  | 'search'
  | 'help_outline'
  | 'fullscreen'
  | 'group'
  | 'dashboard'
  | 'construction'
  | 'engineering'
  | 'assignment'
  | 'flash_on'
  | 'handyman'
  | 'insights'
  | 'local_shipping'
  | 'settings'
  | 'featured_play_list'
  | 'receipt_long'
  | 'print';

/* ---------------------------------------------------------------- header (HeaderToolbar v16.47) */

export type MenuGroup = {
  /** the oracle's meta.name */
  name: string;
  label: string;
  /** the oracle's pipe list, byte-equal - what the underline binding searches */
  pipes: string;
};

/** MenuApplication / MenuUtilities / MenuSystem - the three dropdowns, all inert here (spec s1) */
export const MENU_GROUPS: ReadonlyArray<MenuGroup> = [
  {
    name: 'MenuApplication',
    label: 'Application',
    pipes:
      '|asset|part|meter|locationsetup|supplier|team|maintenance|wizard|pmx|timesheet|planning|schedulex|visualx|resetpassword|',
  },
  {
    name: 'MenuUtilities',
    label: 'Utilities',
    pipes: '|pmrelease|rebuildpmwo|archiveworkorders|assetarchive|partarchive|customformsetup|',
  },
  {
    name: 'MenuSystem',
    label: 'System',
    pipes: '|refcodesetup|usersettings|usermapping|systemsetup|useravailability|securitysetup|',
  },
];

export type ModuleButton = {
  /** the oracle's meta.name */
  name: string;
  /** the session.custom.activePage value the underline binding compares against */
  key: string;
  label: string;
  icon: IconName;
  /** the glyph colour AND the active underline colour (they are the same value in every button) */
  colour: string;
  /** the label's flex basis in px */
  labelBasis: number;
  /** false for BtnMyReports - it has no borderBottom binding at all, so it sits 2px shorter */
  underline: boolean;
  /** true when this build can navigate it (OD-51: Plannex only) */
  live: boolean;
};

/** BtnSchedulex .. BtnMyReports, in view order */
export const MODULE_BUTTONS: ReadonlyArray<ModuleButton> = [
  {
    name: 'BtnSchedulex',
    key: 'schedulex',
    label: 'Schedulex',
    icon: 'event_note',
    colour: '#9C27B0',
    labelBasis: 55,
    underline: true,
    live: false,
  },
  {
    name: 'BtnPlannex',
    key: 'plannex',
    label: 'Plannex',
    icon: 'event_available',
    colour: '#4CAF50',
    labelBasis: 55,
    underline: true,
    live: true,
  },
  {
    name: 'BtnProcurex',
    key: 'procurex',
    label: 'Procurex',
    icon: 'shopping_cart',
    colour: '#795548',
    labelBasis: 50,
    underline: true,
    live: false,
  },
  {
    name: 'BtnPMx',
    key: 'pmx',
    label: 'PMx',
    icon: 'build',
    colour: '#607D8B',
    labelBasis: 28,
    underline: true,
    live: false,
  },
  {
    name: 'BtnInvoicex',
    key: 'invoicex',
    label: 'Invoicex',
    icon: 'receipt',
    colour: '#00BCD4',
    labelBasis: 48,
    underline: true,
    live: false,
  },
  {
    name: 'BtnMyReports',
    key: '',
    label: 'Reports',
    icon: 'assessment',
    colour: '#E91E63',
    labelBasis: 45,
    underline: false,
    live: false,
  },
];

/** the menu underline binding: 2px solid #EBC452 when the key is in the group's pipe list */
export const MENU_ACTIVE_COLOUR = '#EBC452';

/* ---------------------------------------------------------------- rail (SideMenu v4.20) */

export type RailItem = {
  /** the oracle's meta.name */
  name: string;
  label: string;
  icon: IconName;
  /** the glyph colour */
  colour: string;
  /** the left border when active - #E91E63 for every item except Insights, which lights in its own gold */
  activeColour: string;
  /** the activePage values that light it (Invoice has two) */
  keys: ReadonlyArray<string>;
  /** the rights gate the oracle puts on position.display, or null */
  gate: 'visualx' | null;
  /** Divider1 follows Home */
  dividerAfter: boolean;
};

/** MenuItem_Home .. MenuItem_Invoice, in view order (NavContainer) */
export const RAIL_ITEMS: ReadonlyArray<RailItem> = [
  {
    name: 'MenuItem_Home',
    label: 'Home',
    icon: 'dashboard',
    colour: '#DEBF7A',
    activeColour: '#E91E63',
    keys: ['home'],
    gate: null,
    dividerAfter: true,
  },
  {
    name: 'MenuItem_Explorer',
    label: 'Explorer',
    icon: 'search',
    colour: '#2196F3',
    activeColour: '#E91E63',
    keys: ['explorer'],
    gate: null,
    dividerAfter: false,
  },
  {
    name: 'MenuItem_Assets',
    label: 'Assets',
    icon: 'construction',
    colour: '#FF9800',
    activeColour: '#E91E63',
    keys: ['assets'],
    gate: null,
    dividerAfter: false,
  },
  {
    name: 'MenuItem_Labour',
    label: 'Labour',
    icon: 'engineering',
    colour: '#FF9800',
    activeColour: '#E91E63',
    keys: ['labour'],
    gate: null,
    dividerAfter: false,
  },
  {
    name: 'MenuItem_WOMaint',
    label: 'WO Maint',
    icon: 'assignment',
    colour: '#E91E63',
    activeColour: '#E91E63',
    keys: ['womaint'],
    gate: null,
    dividerAfter: false,
  },
  {
    name: 'MenuItem_WOWizard',
    label: 'WO Wizard',
    icon: 'flash_on',
    colour: '#9C27B0',
    activeColour: '#E91E63',
    keys: ['wowizard'],
    gate: null,
    dividerAfter: false,
  },
  {
    name: 'MenuItem_PMWizard',
    label: 'PM Wizard',
    icon: 'handyman',
    colour: '#9C27B0',
    activeColour: '#E91E63',
    keys: ['pmwizard'],
    gate: null,
    dividerAfter: false,
  },
  {
    name: 'MenuItem_VisualX',
    label: 'VisualX',
    icon: 'dashboard',
    colour: '#4CAF50',
    activeColour: '#E91E63',
    keys: ['visualx'],
    gate: 'visualx',
    dividerAfter: false,
  },
  {
    name: 'MenuItem_Insights',
    label: 'Insights',
    icon: 'insights',
    colour: '#DEBF7A',
    activeColour: '#DEBF7A',
    keys: ['insights'],
    gate: null,
    dividerAfter: false,
  },
  {
    name: 'MenuItem_Supplier',
    label: 'Supplier',
    icon: 'local_shipping',
    colour: '#00BCD4',
    activeColour: '#E91E63',
    keys: ['supplier'],
    gate: null,
    dividerAfter: false,
  },
  {
    name: 'MenuItem_Parts',
    label: 'Parts',
    icon: 'settings',
    colour: '#009688',
    activeColour: '#E91E63',
    keys: ['parts'],
    gate: null,
    dividerAfter: false,
  },
  {
    name: 'MenuItem_POList',
    label: 'PO List',
    icon: 'featured_play_list',
    colour: '#0B5ED7',
    activeColour: '#E91E63',
    keys: ['purchaseorder'],
    gate: null,
    dividerAfter: false,
  },
  {
    name: 'MenuItem_Invoice',
    label: 'Invoice',
    icon: 'receipt_long',
    colour: '#FFC107',
    activeColour: '#E91E63',
    keys: ['invoicemaint', 'invoicex'],
    gate: null,
    dividerAfter: false,
  },
];

/** MenuItem_Print (BottomContainer, after Divider2) - a static 3px transparent border, no binding */
export const PRINT_ITEM = {
  name: 'MenuItem_Print',
  label: 'Print',
  icon: 'print' as const,
  colour: '#AAAAAA',
};

/* ---------------------------------------------------------------- the bindings, as functions */

/** MenuApplication et al: `indexOf(pipes, '|' + activePage + '|') >= 0` */
export function menuActive(pipes: string, key: string): boolean {
  return pipes.indexOf(`|${key}|`) >= 0;
}

/** the three menu labels' borderBottom */
export function menuUnderline(on: boolean): string {
  return on ? `2px solid ${MENU_ACTIVE_COLOUR}` : '2px solid transparent';
}

/** a module button's borderBottom - `if({activePage} = '<key>', '2px solid <c>', '2px solid transparent')` */
export function underline(colour: string, on: boolean): string {
  return on ? `2px solid ${colour}` : '2px solid transparent';
}

/** a rail item's borderLeft - `if({activePage} = '<key>', '4px solid <c>', '4px solid transparent')` */
export function railBorder(colour: string, on: boolean): string {
  return on ? `4px solid ${colour}` : '4px solid transparent';
}

/**
 * OD-52. The oracle gates VisualX (rail) and the search pill (header) on
 * runScript('workmate.security.allowed', ...) - rights this build does not have. False until it does.
 */
export function gateOpen(gate: RailItem['gate']): boolean {
  return gate === null;
}

/**
 * session.custom.activePage, derived from the router path instead of set by each button's onClick.
 * One row per page this build can draw; a module port lights itself by adding its row here.
 */
const ACTIVE_KEY_BY_PATH: ReadonlyArray<readonly [string, string]> = [['/planner', 'plannex']];

export function activeKeyFor(pathname: string): string {
  const path = pathname.length > 1 && pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
  for (const [p, key] of ACTIVE_KEY_BY_PATH) if (p === path) return key;
  return '';
}

export type PrintTarget = 'POPrintPopup' | 'WOPrintPopup' | 'browser';

/** MenuItem_Print's dispatcher (SideMenu v4.7 / v4.18): trim + lower, then the two popups, else the browser */
export function printTarget(pageKey: string): PrintTarget {
  const page = pageKey.trim().toLowerCase();
  if (page === 'purchaseorder') return 'POPrintPopup';
  if (page === 'workorder' || page === 'wo' || page === 'womaint' || page === 'workorders') {
    return 'WOPrintPopup';
  }
  return 'browser';
}

/* ---------------------------------------------------------------- OD-51 / OD-34 - the chrome says only what is true */

/** the hover title of a control that draws as the oracle draws it and does nothing yet */
export function inertTitle(what: string): string {
  return `arrives with ${what} (OD-51)`;
}

export const LOGOUT_TITLE = 'arrives with sign-in (OD-12)';
export const TIPS_TITLE = 'arrives with tips (item 33)';
export const HUB_TITLE = inertTitle('the Hub');
