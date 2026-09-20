/**
 * Azztec_SaaS_web_workorders_symbols_v1_0_2.tsx  ->  web/src/features/workorders/symbols.tsx
 * Version:  1.0.2   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §3.5 · OD-74, OD-75, OD-79
 * Oracle:   WONumBadge_2026-09-19_view.json (WONumBadge_v1_3_0), WOStatus_2026-09-19_view.json,
 *           WOProgress_2026-09-19_view.json, CompleteWithinSeg_2026-09-19_view.json - all four read
 *           element by element 2026-09-20. Every geometry number and paint below is the export's own.
 *
 * Four presentational components. No state, no fetch, no handlers - every colour decision lives in
 * rules.ts as data, so the tests read a table rather than a render tree. The oracle passes a
 * `progressId` / `status` param to each embedded card and the card decides lit vs unlit against its
 * own id; ported as `lit` computed by the row, same result, one comparison instead of six.
 *
 * The six progress symbols are the export's `elements` arrays transcribed as SVG: `bg` is the
 * rounded 22x22 rect every one carries, then the id's own shape. 25/50/75 print '1' '2' '3' - the
 * QUARTER COUNT, not the percentage - and their fill bar sits at y 17.5 / 12 / 6.5. That is the
 * oracle's own lettering; do not "correct" it to 25/50/75.
 *
 * Changelog:
 *   1.0.2  Smoke fix, before the tag. BadgeStyle's three longhands already satisfy CSSProperties, so
 *          the `as CSSProperties` on it was doing nothing but hiding future type errors (lint). Gone.
 *          CSSProperties stays imported - the two card styles annotate with it, which is the honest use.
 *   1.0.1  Smoke fix, before the tag. Indexes GLYPHS (all fifteen) instead of WO_MATERIAL (thirteen),
 *          which is what made every status row throw on `assignment`; the `as WoIconName` cast that
 *          hid it is gone, so the record's key type now carries the guarantee. BAR is typed with
 *          `| undefined` so the `bar &&` guard reads as live code.
 *   1.0.0  Initial W1b.
 */
import type { CSSProperties } from 'react';

import type { ProgressRow, WoRecord } from '../../api/client';
import { GLYPHS, WoIcon } from './icons';
import { SEGMENT_ITEMS, WO_STATUS_CARDS, badgeStyle, parseBadge, progressCards } from './rules';

export const VERSION = '1.0.2';

/* ------------------------------------------------------------------ WONumBadge v1.3.0 */

/** The static half lives in wo.css (.wo-badge); the three dynamic longhands come from rules.ts. */
export function WoNumBadge({ value }: { value: string | null | undefined }) {
  const { text } = parseBadge(value);
  return (
    <span className="wo-badge" style={badgeStyle(value)}>
      {text}
    </span>
  );
}

/* ------------------------------------------------------------------ WOStatus - the eight cards */

/** One 68x58 card. Lit paints from the card's own --wo-color-* value; R is the dark-text one. */
function StatusCard({
  card,
  lit,
}: {
  card: (typeof WO_STATUS_CARDS)[number];
  lit: boolean;
}) {
  const fg = lit ? (card.darkText ? '#000000' : '#FFFFFF') : '#5D6E71';
  const style: CSSProperties = lit
    ? { background: card.hex, border: `2px solid ${card.accent}`, color: fg, fontWeight: 'bold' }
    : {};
  return (
    <div className="wo-symcard" data-code={card.code} data-lit={lit} style={style} title={card.label}>
      <WoIcon colour={fg} paths={GLYPHS[card.icon]} size={20} />
      <span className="wo-symlabel">{card.label}</span>
    </div>
  );
}

/**
 * Eight cards, never nine (OD-74). A record at 'F' lights none - the oracle's own gap, kept; the
 * header still names the status through statusTitle, so the screen never goes silent about it.
 */
export function WoStatusRow({ status }: { status: string }) {
  return (
    <div aria-label="Work order status" className="wo-symrow" role="group">
      {WO_STATUS_CARDS.map((c) => (
        <StatusCard card={c} key={c.code} lit={c.code === status} />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ WOProgress - the six symbols */

const SYM_BG = { height: 22, rx: 3, ry: 3, width: 22, x: 1, y: 1 };

/** The three bar heights, straight off svgProgress25/50/75. */
const BAR: Readonly<Record<number, { y: number; height: number; text: string } | undefined>> = {
  3: { y: 17.5, height: 5.5, text: '1' },
  4: { y: 12, height: 11, text: '2' },
  5: { y: 6.5, height: 16.5, text: '3' },
};

/** The export's element arrays, one branch per symbol id. Paints follow the lit/unlit expressions. */
function ProgressSymbol({ id, lit }: { id: number; lit: boolean }) {
  const bgFill = lit ? '#FFFFFF' : '#EEF0F0';
  const bgStroke = lit ? '#FFFFFFAA' : '#8A9698';
  const ink = lit ? '#242E30' : '#5D6E71';
  const bar = BAR[id];
  return (
    <svg aria-hidden="true" focusable="false" height={24} viewBox="0 0 24 24" width={24}>
      <rect {...SYM_BG} fill={bgFill} stroke={bgStroke} strokeWidth={1} />
      {id === 1 && (
        <circle cx={12} cy={12} fill="transparent" r={5.5} stroke={ink} strokeWidth={1.5} />
      )}
      {id === 2 && (
        <path d="M7.2 5.3 L16.8 5.3 L12.5 11.5 L16.8 18.7 L7.2 18.7 L11.5 11.5 Z" fill={ink} stroke="none" />
      )}
      {bar && (
        <>
          <rect
            fill={lit ? '#3D4F52' : '#5D6E71'}
            fillOpacity={lit ? 0.5 : 0.19}
            height={bar.height}
            stroke="none"
            width={22}
            x={1}
            y={bar.y}
          />
          <text
            dominantBaseline="central"
            fill={ink}
            fontSize="13px"
            fontWeight="700"
            pointerEvents="none"
            textAnchor="middle"
            x={12}
            y={12}
          >
            {bar.text}
          </text>
        </>
      )}
      {id === 6 && (
        <path
          d="M6.5 12 L10.2 15.8 L17.5 8.2"
          fill="none"
          stroke={lit ? '#16A34A' : '#5D6E71'}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2.5}
        />
      )}
    </svg>
  );
}

/**
 * One card per active dbo.Progress row (OD-75). Ids 1-6 draw the oracle's symbol; 7 and 8 - three
 * quarters of RST's open work - draw a plain titled card rather than lighting nothing.
 * The lit background is #3D4F52 except the 100% card, which is #16A34A.
 */
export function WoProgressRow({
  prog,
  progressAll,
}: {
  prog: number;
  progressAll: ReadonlyArray<ProgressRow>;
}) {
  const cards = progressCards(progressAll);
  return (
    <div aria-label="Work order progress" className="wo-symrow" role="group">
      {cards.map((c) => {
        const lit = c.id === prog;
        const style: CSSProperties = lit
          ? {
              background: c.id === 6 ? '#16A34A' : '#3D4F52',
              border: '2px solid #242E30',
              color: '#FFFFFF',
              fontWeight: 'bold',
            }
          : {};
        return (
          <div
            className="wo-symcard"
            data-lit={lit}
            data-progress={c.id}
            key={c.id}
            style={style}
            title={c.label}
          >
            {c.symbol === null ? null : <ProgressSymbol id={c.symbol} lit={lit} />}
            <span className="wo-symlabel">{c.label}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ CompleteWithinSeg v1.8.0 */

/**
 * Read-only in W1b. Changing it is a write and `range` opens WODateRangePopup, so every segment is
 * aria-disabled with the OD-51 title and carries no handler - drawn honestly, not pretending
 * (OD-34). The track self-styles in wo.css; wm-seg-9px was dead and is dropped (OD-76).
 */
export function CompleteWithinSeg({ value }: { value: WoRecord['completeWithin'] }) {
  return (
    <div aria-label="Complete within" className="wo-seg" role="group">
      {SEGMENT_ITEMS.map((s) => (
        <span
          aria-disabled="true"
          className={`wo-seg-item${s.value === value ? ' on' : ''}`}
          data-seg={s.value}
          key={s.value}
          title="changing the schedule arrives with the write slice (OD-51)"
        >
          {s.label}
        </span>
      ))}
    </div>
  );
}
