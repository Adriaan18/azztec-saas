/**
 * Azztec_SaaS_web_workorders_rules_test_v1_0_1.ts  ->  web/src/features/workorders/rules.test.ts
 * Version:  1.0.1   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §5 · pair of rules.ts 1.0.0
 *
 * Zero DOM, zero network, zero Date. Every expected colour string is the stylesheet v2.69 value
 * resolved by hand from docs/reference/Workmate_Stylesheet_2026-09-20_v2_69.css - if a token there
 * moves, this file names the row that moved.
 *
 * Changelog:
 *   1.0.1  rules.ts is 1.0.1 (typed icon, honest index maps). No case changed - the maps behave
 *          exactly as they did; only what they told the type checker moved. 51 cases.
 *   1.0.0  Initial W1b. 51 cases.
 */
import { describe, expect, it } from 'vitest';

import type { WoRecord } from '../../api/client';
import { recordFixture } from './record.fixture';
import {
  BADGE_PCT,
  ID_PILL,
  PROGRESS_SYMBOL_LABELS,
  SEGMENT_ITEMS,
  SUB_TABS,
  TYPE_CHIPS,
  VERSION,
  WO_STATUS_CARDS,
  badgeStyle,
  detailLeft,
  detailMiddle,
  detailStamps,
  displayDateTime,
  displayStamp,
  idPillStyle,
  linkedTabLabel,
  listTitle,
  mainTabs,
  numText,
  parseBadge,
  poBadgeStyle,
  progressCards,
  recordCount,
  respUsersLine,
  wocText,
} from './rules';

export const TEST_VERSION = '1.0.1';

describe('parseBadge - the WONumBadge transform, exactly', () => {
  it('splits a full composite', () => {
    expect(parseBadge('V|3CL-260826-010|6|1')).toEqual({
      status: 'V',
      text: '3CL-260826-010',
      prog: 6,
      hasPO: true,
    });
  });
  it('hasPO absent means false', () => {
    expect(parseBadge('C|1LY-260826-003|6')).toEqual({
      status: 'C',
      text: '1LY-260826-003',
      prog: 6,
      hasPO: false,
    });
  });
  it('prog absent means 0', () => {
    expect(parseBadge('R|110705/071')).toEqual({ status: 'R', text: '110705/071', prog: 0, hasPO: false });
  });
  it('a lone value is its own text and its first char is the status - the oracle, not a fix', () => {
    expect(parseBadge('3CL-260826-010')).toEqual({
      status: '3',
      text: '3CL-260826-010',
      prog: 0,
      hasPO: false,
    });
  });
  it('empty and null are empty', () => {
    expect(parseBadge('')).toEqual({ status: '', text: '', prog: 0, hasPO: false });
    expect(parseBadge(null)).toEqual({ status: '', text: '', prog: 0, hasPO: false });
  });
  it('junk prog and hasPO fall to 0 / false', () => {
    expect(parseBadge('V|X|abc|junk')).toEqual({ status: 'V', text: 'X', prog: 0, hasPO: false });
  });
});

describe('badgeStyle - three longhands, both layers always', () => {
  it('paints V from the active token pair', () => {
    const s = badgeStyle('V|X|1|0');
    expect(s.backgroundColor).toBe('rgba(40, 167, 69, 0.16)');
    expect(s.color).toBe('rgba(40, 167, 69, 0.8)');
  });
  it('paints F from the deferred token the status row cannot draw (OD-74)', () => {
    const s = badgeStyle('F|X|1|0');
    expect(s.backgroundColor).toBe('rgba(255, 152, 0, 0.16)');
    expect(s.color).toBe('rgba(255, 152, 0, 0.8)');
  });
  it('an unknown status falls to the muted cancelled pair', () => {
    const s = badgeStyle('Z|X|1|0');
    expect(s.backgroundColor).toBe('rgba(108, 117, 125, 0.08)');
    expect(s.color).toBe('rgba(108, 117, 125, 0.5)');
    expect(s.backgroundImage).toContain('#196690');
  });
  it('emits the transparent PO dot layer even with no PO', () => {
    const s = badgeStyle('V|X|1|0');
    expect(s.backgroundImage.startsWith('radial-gradient(circle, transparent 55%, transparent 60%), ')).toBe(
      true,
    );
  });
  it('emits the #0B5ED7 dot when hasPO', () => {
    expect(badgeStyle('V|X|1|1').backgroundImage).toContain('radial-gradient(circle, #0B5ED7 55%');
  });
  it('maps progress 1/3/4/5/6 to 0/25/50/75/100 on the underline', () => {
    for (const [prog, pct] of Object.entries(BADGE_PCT)) {
      const s = badgeStyle(`V|X|${prog}|0`);
      expect(s.backgroundImage).toContain(`rgba(40, 167, 69, 0.95) ${pct}%, transparent ${pct}%`);
    }
  });
  it('progress 2 is the muted 8% nub, not 2%', () => {
    expect(badgeStyle('V|X|2|0').backgroundImage).toContain(
      'linear-gradient(to right, rgba(100, 116, 139, 0.55) 8%, transparent 8%)',
    );
  });
  it('an unmapped progress id underlines at 0%', () => {
    expect(badgeStyle('V|X|7|0').backgroundImage).toContain('0.95) 0%, transparent 0%');
  });
});

describe('poBadgeStyle - PONumBadge v1.2.0 colours and text', () => {
  it('paints I (Issued) - the green badge in the live shot', () => {
    const s = poBadgeStyle('I|K-260830-002');
    expect(s.backgroundColor).toBe('rgba(40, 167, 69, 0.16)');
    expect(s.color).toBe('rgba(40, 167, 69, 0.8)');
  });
  it('strips exactly two characters for the text', () => {
    expect(poBadgeStyle('I|K-260830-002').text).toBe('K-260830-002');
  });
  it('an unknown status falls to the muted cancelled pair', () => {
    const s = poBadgeStyle('Z|X');
    expect(s.backgroundColor).toBe('rgba(108, 117, 125, 0.08)');
    expect(s.color).toBe('rgba(108, 117, 125, 0.5)');
  });
  it('a value of two or fewer characters is its own text', () => {
    expect(poBadgeStyle('I|').text).toBe('I|');
    expect(poBadgeStyle('').text).toBe('');
  });
});

describe('WO_STATUS_CARDS - eight, not nine (OD-74)', () => {
  it('is R H P K A V C D in card order, with no F', () => {
    expect(WO_STATUS_CARDS.map((c) => c.code)).toEqual(['R', 'H', 'P', 'K', 'A', 'V', 'C', 'D']);
  });
  it('carries the eight glyphs in card order', () => {
    expect(WO_STATUS_CARDS.map((c) => c.icon)).toEqual([
      'warning',
      'assignment',
      'schedule',
      'thumb_up',
      'check_circle',
      'play_circle_filled',
      'cancel',
      'block',
    ]);
  });
  it('R is the only dark-text card', () => {
    expect(WO_STATUS_CARDS.filter((c) => c.darkText).map((c) => c.code)).toEqual(['R']);
  });
  it('every lit background and accent is distinct', () => {
    expect(new Set(WO_STATUS_CARDS.map((c) => c.hex)).size).toBe(8);
    expect(new Set(WO_STATUS_CARDS.map((c) => c.accent)).size).toBe(8);
  });
});

describe('progressCards - one card per active row (OD-75)', () => {
  it("uses the symbol's own labels for 1..6, with the symbol id", () => {
    const cards = progressCards([
      { id: 1, title: 'No Progress', short: 'NONE' },
      { id: 6, title: '100% Complete', short: '100' },
    ]);
    expect(cards).toEqual([
      { id: 1, label: 'None', symbol: 1 },
      { id: 6, label: '100%', symbol: 6 },
    ]);
  });
  it('draws a plain titled card for 7 and 8 - three quarters of the open work on RST', () => {
    const cards = progressCards(recordFixture().progressAll);
    expect(cards).toHaveLength(8);
    expect(cards[6]).toEqual({ id: 7, label: 'Scheduled', symbol: null });
    expect(cards[7]).toEqual({ id: 8, label: 'Assigned', symbol: null });
  });
  it('an unknown id beyond the label table keeps its own title and no symbol', () => {
    expect(progressCards([{ id: 9, title: 'Machining', short: 'MACH' }])).toEqual([
      { id: 9, label: 'Machining', symbol: null },
    ]);
  });
  it('sorts by id whatever order the rows arrive in', () => {
    const cards = progressCards([
      { id: 6, title: 'x', short: 'x' },
      { id: 1, title: 'y', short: 'y' },
    ]);
    expect(cards.map((c) => c.id)).toEqual([1, 6]);
  });
  it('an empty list draws nothing', () => {
    expect(progressCards([])).toEqual([]);
  });
});

describe('idPillStyle - the pill has its own map, not the tokens', () => {
  it('paints V green with white text', () => {
    expect(idPillStyle('V')).toEqual({ backgroundColor: '#28A745', color: '#FFF' });
  });
  it('P and K deliberately share #6F42C1 and A is #007BFF - ported, not fixed', () => {
    expect(ID_PILL.P).toBe('#6F42C1');
    expect(ID_PILL.K).toBe('#6F42C1');
    expect(ID_PILL.A).toBe('#007BFF');
  });
  it('an unknown status is #FFFFCC with white text - the oracle only darkens on empty', () => {
    expect(idPillStyle('Z')).toEqual({ backgroundColor: '#FFFFCC', color: '#FFF' });
  });
  it('an empty status is #FFFFCC with black text', () => {
    expect(idPillStyle('')).toEqual({ backgroundColor: '#FFFFCC', color: '#000' });
  });
});

describe('the segment and the contract', () => {
  it('SEGMENT_ITEMS is the six, in the backend order and spelling', () => {
    const values: WoRecord['completeWithin'][] = SEGMENT_ITEMS.map((s) => s.value);
    expect(values).toEqual(['day', 'week', 'month', '3month', 'nextshut', 'range']);
  });
  it('labels are the oracle labels', () => {
    expect(SEGMENT_ITEMS.map((s) => s.label)).toEqual([
      'Day',
      'Week',
      'Month',
      '3-Month',
      'Next shut',
      'Range',
    ]);
  });
});

describe('list panel strings', () => {
  it('listTitle follows the view expression', () => {
    expect(listTitle('M')).toBe('Planned Maintenance');
    expect(listTitle('')).toBe('Work Orders + PM');
    expect(listTitle('N')).toBe('Work Orders');
    expect(listTitle('CP')).toBe('Work Orders');
  });
  it('the four chips map WO/CP/PM/All to N/CP/M/empty in order', () => {
    expect(TYPE_CHIPS).toEqual([
      { label: 'WO', value: 'N' },
      { label: 'CP', value: 'CP' },
      { label: 'PM', value: 'M' },
      { label: 'All', value: '' },
    ]);
  });
  it('recordCount is honest about more - never a total (OD-77)', () => {
    expect(recordCount(200, true)).toBe('No of Records: 200+');
    expect(recordCount(10, false)).toBe('No of Records: 10');
  });
});

describe('tabs', () => {
  it('linkedTabLabel gains (+) above one row', () => {
    expect(linkedTabLabel(0)).toBe('Linked WO');
    expect(linkedTabLabel(1)).toBe('Linked WO');
    expect(linkedTabLabel(2)).toBe('Linked WO (+)');
  });
  it('mainTabs: only Work Order is live in W1b', () => {
    const tabs = mainTabs(1);
    expect(tabs.map((t) => t.label)).toEqual([
      'Work Order',
      'Activity',
      'Query/Notes',
      'Linked WO',
      'WO Event History',
    ]);
    expect(tabs.filter((t) => t.live).map((t) => t.key)).toEqual(['workorder']);
  });
  it('SUB_TABS is the VIEW order - Purchase Orders second - and Details only is live', () => {
    expect(SUB_TABS.map((t) => t.label)).toEqual([
      'Details',
      'Purchase Orders',
      'Attachments',
      'Procedures',
      'Parts',
      'Labour',
    ]);
    expect(SUB_TABS.filter((t) => t.live).map((t) => t.key)).toEqual(['details']);
  });
});

describe('display strings - no Date object anywhere', () => {
  it('displayStamp renders dd/MM/yyyy HH:mm and drops seconds', () => {
    expect(displayStamp('2026-08-26 19:19:04')).toBe('26/08/2026 19:19');
  });
  it('displayStamp on empty or short input is empty', () => {
    expect(displayStamp('')).toBe('');
    expect(displayStamp(null)).toBe('');
    expect(displayStamp('2026-08-26')).toBe('');
  });
  it('displayDateTime renders the date-time input string with a 12-hour clock', () => {
    expect(displayDateTime('2026-09-17', '10:11')).toBe('Sep 17, 2026 10:11 AM');
    expect(displayDateTime('2026-08-26', '19:17')).toBe('Aug 26, 2026 7:17 PM');
  });
  it('displayDateTime handles noon, midnight and a missing time', () => {
    expect(displayDateTime('2026-01-05', '12:00')).toBe('Jan 5, 2026 12:00 PM');
    expect(displayDateTime('2026-01-05', '00:05')).toBe('Jan 5, 2026 12:05 AM');
    expect(displayDateTime('2026-01-05', '')).toBe('Jan 5, 2026');
    expect(displayDateTime('', '10:00')).toBe('');
  });
  it("numText prints a float column the oracle's way - '0.0', not '0'", () => {
    expect(numText(0)).toBe('0.0');
    expect(numText(2.5)).toBe('2.5');
    expect(numText(2026.35)).toBe('2026.35');
    expect(numText(null)).toBe('');
  });
});

describe('respUsersLine', () => {
  it('joins short ids with a comma', () => {
    expect(
      respUsersLine([
        { userId: 1, shortId: 'KF', name: 'Ken Fisher' },
        { userId: 2, shortId: 'AB', name: 'A B' },
      ]),
    ).toBe('KF, AB');
  });
  it('an empty list is (none)', () => {
    expect(respUsersLine([])).toBe('(none)');
  });
});

describe('the Details rows against the 662704 fixture', () => {
  it('left column: seven rows in view order, with the supplier shorts as desc', () => {
    const rows = detailLeft(recordFixture());
    expect(rows.map((r) => r.label)).toEqual([
      'WO Group :',
      'Reason :',
      'Fault :',
      'Dept. :',
      'Class :',
      'Charge To :',
      'Responsibility :',
    ]);
    expect(rows[3].value).toBe('652 KPP Plant');
    expect(rows[5]).toEqual({ label: 'Charge To :', value: 'Maintenance Team', desc: 'TM-MAINT' });
    expect(rows[6].desc).toBe('TM-ELEC');
  });
  it('middle column: an empty WOC shows -- No Selection --', () => {
    const rows = detailMiddle(recordFixture());
    expect(rows[0]).toEqual({ label: 'WOC 1 :', value: '-- No Selection --' });
    expect(rows[3].value).toBe('Red Stag Timber');
    expect(wocText('Safety')).toBe('Safety');
  });
  it("stamps: Created By pairs with the LOGGED date - the oracle's binding", () => {
    const rows = detailStamps(recordFixture());
    expect(rows[0]).toEqual({ label: 'Created By :', user: 'KF', date: '26/08/2026 19:17' });
    expect(rows[1]).toEqual({ label: 'Ack. By :', user: '', date: '' });
    expect(rows[5]).toEqual({ label: 'Last Save :', user: 'KF', date: '26/08/2026 19:19' });
  });
});

describe('version', () => {
  it('rules.ts is 1.0.1', () => {
    expect(VERSION).toBe('1.0.1');
  });
  it('the symbol label table covers exactly 1..6', () => {
    expect(Object.keys(PROGRESS_SYMBOL_LABELS).map(Number).sort((a, b) => a - b)).toEqual([
      1, 2, 3, 4, 5, 6,
    ]);
  });
});
