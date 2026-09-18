/**
 * Azztec_SaaS_web_shell_SideMenu_v1_0_0.tsx  ->  web/src/features/shell/SideMenu.tsx
 * Version:  1.0.0   Date: 2026-09-16   Author: Adriaan
 * Spec:     Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md s3.4 . OD-50, OD-51, OD-52
 * Oracle:   Workmate/Navigation/SideMenu v4.20 (docs/reference/SideMenu_2026-09-16_view.json)
 *
 * NavContainer (grow) holds the twelve items this session can show - VisualX is rights-gated at KT and
 * not rendered here (OD-52) - with Divider1 after Home; BottomContainer holds Divider2 and Print, so
 * Print sits at the foot as it does in the oracle. Every item is inert except Print (OD-51): the
 * oracle's dispatcher falls through to the browser's print on any page this build has.
 *
 * The left border is the one inline style, because the oracle binds it: 4px solid <activeColour> when
 * the active key is one of the item's keys, else 4px solid transparent - the width is reserved so
 * nothing shifts when an item lights. Print's border is a static 3px transparent in the view; parity.
 *
 * Changelog:
 *   1.0.0  Initial S1k.
 */
import { Fragment } from 'react';

import { Glyph, MATERIAL } from './icons';
import { PRINT_ITEM, RAIL_ITEMS, gateOpen, inertTitle, railBorder } from './rules';

export const VERSION = '1.0.0';

export type SideMenuProps = {
  /** the oracle's session.custom.activePage, derived from the router path (rules.activeKeyFor) */
  activeKey: string;
  onPrint: () => void;
};

export function SideMenu({ activeKey, onPrint }: SideMenuProps) {
  return (
    <nav className="wm-rail" data-name="SideMenu_v4_20">
      <div className="nav" data-name="NavContainer">
        {RAIL_ITEMS.filter((r) => gateOpen(r.gate)).map((r) => {
          const on = r.keys.includes(activeKey);
          return (
            <Fragment key={r.name}>
              <span
                className="item inert"
                data-name={r.name}
                data-active={on ? '1' : '0'}
                style={{ borderLeft: railBorder(r.activeColour, on) }}
                title={inertTitle(r.label)}
                aria-disabled="true"
              >
                <Glyph className="ico" paths={MATERIAL[r.icon]} colour={r.colour} px={19} />
                <span className="lbl">{r.label}</span>
              </span>
              {r.dividerAfter && <span className="divider" data-name="Divider1" />}
            </Fragment>
          );
        })}
      </div>
      <div className="bottom" data-name="BottomContainer">
        <span className="divider" data-name="Divider2" />
        <button type="button" className="item print" data-name={PRINT_ITEM.name} title="Print" onClick={onPrint}>
          <Glyph className="ico" paths={MATERIAL[PRINT_ITEM.icon]} colour={PRINT_ITEM.colour} px={19} />
          <span className="lbl">{PRINT_ITEM.label}</span>
        </button>
      </div>
    </nav>
  );
}
