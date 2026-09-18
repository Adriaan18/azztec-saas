/**
 * Azztec_SaaS_web_shell_HeaderToolbar_v1_0_0.tsx  ->  web/src/features/shell/HeaderToolbar.tsx
 * Version:  1.0.0   Date: 2026-09-16   Author: Adriaan
 * Spec:     Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md s3.3 . OD-50, OD-51, OD-52, OD-53 (AZZTEC only)
 * Oracle:   Workmate/Navigation/HeaderToolbar v16.47 (docs/reference/HeaderToolbar_2026-09-16_view.json)
 *
 * One element per oracle component, in the view's order, each carrying data-name="<meta.name>" so
 * DevTools, the screenshot and the JSON line up. Props-driven and router-free (the PlannerView
 * precedent): the active key, the brand, the clock strings and two callbacks come in; nothing here
 * imports a router or reads a URL.
 *
 * Not rendered, exactly as the oracle hides them on this session: the WORKMATE brand parts
 * (WorkmateLogo, AMMSSpine, lblBrandName - cut, OD-53: the logo PNG did not arrive and a missing image
 * is not a port), VXSearchPill and userCoord (OD-52 - rights and roles do not exist yet). Drawn and inert (OD-51 / OD-34): the two
 * logos, the three menus, every module button but Plannex, the tips toggle, logout - cursor default,
 * aria-disabled, a title that says what they wait for, no handler. Live: Plannex (click / Enter ->
 * onPlannex), fsBtn (-> onFullscreen), and the clock.
 *
 * Inline style only where the oracle BINDS a style (the underlines); every static value is in shell.css.
 *
 * Changelog:
 *   1.0.0  Initial S1k.
 */
import type { KeyboardEvent } from 'react';

import { AZZTEC_LOGO_URI, Glyph, LOGOUT, MATERIAL } from './icons';
import {
  HUB_TITLE,
  LOGOUT_TITLE,
  MENU_GROUPS,
  MODULE_BUTTONS,
  TIPS_TITLE,
  inertTitle,
  menuActive,
  menuUnderline,
  underline,
} from './rules';

export const VERSION = '1.0.0';

export type HeaderToolbarProps = {
  /** the oracle's session.custom.activePage, derived from the router path (rules.activeKeyFor) */
  activeKey: string;
  /** dateFormat(now(), "MMM d") */
  dateText: string;
  /** dateFormat(now(), "HH:mm:ss") */
  timeText: string;
  onPlannex: () => void;
  onFullscreen: () => void;
};

/** click or Enter on a role=link element */
function onEnter(fn: () => void) {
  return (e: KeyboardEvent<HTMLElement>) => {
    if (e.key === 'Enter') fn();
  };
}

export function HeaderToolbar({
  activeKey,
  dateText,
  timeText,
  onPlannex,
  onFullscreen,
}: HeaderToolbarProps) {
  return (
    <header className="wm-hdr" data-name="HeaderToolbar_v16_47">
      {/* logos: the oracle shows AzztecLogo or WorkmateLogo on session.custom.wmBrandMode; the WORKMATE
          pair (WorkmateLogo, AMMSSpine, lblBrandName) is cut - its PNG did not arrive (OD-53) */}
      <img
        className="logo inert"
        data-name="AzztecLogo"
        src={AZZTEC_LOGO_URI}
        alt="Azztec"
        width={48}
        height={48}
        title={HUB_TITLE}
        aria-disabled="true"
      />

      <div className="brand" data-name="BrandBlock">
        <span className="wordmark" data-name="lblBrandNameAzztec">
          Azztec
        </span>
      </div>

      {MENU_GROUPS.map((g) => (
        <span
          key={g.name}
          className="menu inert"
          data-name={g.name}
          style={{ borderBottom: menuUnderline(menuActive(g.pipes, activeKey)) }}
          title={inertTitle(`the ${g.label} menu`)}
          aria-disabled="true"
        >
          {g.label}
        </span>
      ))}

      <span className="sep" data-name="SepMenuNav" />

      {MODULE_BUTTONS.map((b) => {
        const on = b.underline && activeKey === b.key;
        const common = {
          'data-name': b.name,
          'data-active': on ? '1' : '0',
          style: b.underline ? { borderBottom: underline(b.colour, on) } : undefined,
        };
        const body = (
          <>
            <Glyph className="ico" paths={MATERIAL[b.icon]} colour={b.colour} px={13} />
            <span className="lbl" style={{ flexBasis: b.labelBasis }}>
              {b.label}
            </span>
          </>
        );
        return b.live ? (
          <span
            key={b.name}
            {...common}
            className="mbtn live"
            role="link"
            tabIndex={0}
            onClick={onPlannex}
            onKeyDown={onEnter(onPlannex)}
          >
            {body}
          </span>
        ) : (
          <span key={b.name} {...common} className="mbtn inert" title={inertTitle(b.label)} aria-disabled="true">
            {body}
          </span>
        );
      })}

      <span className="spacer" data-name="Spacer" />

      <div className="right" data-name="RightControls">
        {/* VXSearchPill: not rendered - rights-gated at KT (OD-52) */}
        <span className="tips on inert" data-name="TipsToggle" title={TIPS_TITLE} aria-disabled="true">
          <Glyph paths={MATERIAL.help_outline} colour="#FFFFFF" px={16} />
        </span>
        <div className="stack" data-name="ControlStack">
          <div className="row" data-name="topRow">
            <span className="coord" data-name="fsCoord">
              <button
                type="button"
                className="sq"
                data-name="fsBtn"
                title="fullscreen"
                aria-label="fullscreen"
                onClick={onFullscreen}
              >
                <Glyph paths={MATERIAL.fullscreen} colour="#1F1F1F" px={16} />
              </button>
            </span>
            <span className="coord" data-name="logoutCoord">
              <button
                type="button"
                className="sq inert"
                data-name="logoutBtn"
                title={LOGOUT_TITLE}
                aria-label="logout"
                aria-disabled="true"
              >
                <Glyph paths={LOGOUT} colour="#1F1F1F" px={14} />
              </button>
            </span>
            <span className="clk" data-name="dateLabel">
              {dateText}
            </span>
          </div>
          <div className="row" data-name="bottomRow">
            {/* userCoord / userBtn: not rendered - hasRole("Administrator") at KT (OD-52) */}
            <span className="clk" data-name="timeLabel">
              {timeText}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
