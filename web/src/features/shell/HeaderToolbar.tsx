/**
 * Azztec_SaaS_web_shell_HeaderToolbar_v1_1_0.tsx  ->  web/src/features/shell/HeaderToolbar.tsx
 * Version:  1.1.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md s3.3 . OD-50, OD-51, OD-52, OD-53 (AZZTEC only);
 *           Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6 (the name, view only, Sign out)
 * Oracle:   Workmate/Navigation/HeaderToolbar v16.47 (docs/reference/HeaderToolbar_2026-09-16_view.json)
 *
 * One element per oracle component, in the view's order, each carrying data-name="<meta.name>" so
 * DevTools, the screenshot and the JSON line up. Props-driven and router-free (the PlannerView
 * precedent): the active key, the brand, the clock strings and the callbacks come in; nothing here
 * imports a router or reads a URL.
 *
 * Not rendered, exactly as the oracle hides them on this session: the WORKMATE brand parts
 * (WorkmateLogo, AMMSSpine, lblBrandName - cut, OD-53: the logo PNG did not arrive and a missing image
 * is not a port), VXSearchPill and userCoord (OD-52 - KT gates them on roles this build does not
 * carry). Drawn and inert (OD-51 / OD-34): the two logos, the three menus, every module button but
 * Plannex, the tips toggle - cursor default, aria-disabled, a title that says what they wait for, no
 * handler. Live: Plannex (click / Enter -> onPlannex), fsBtn (-> onFullscreen), and the clock.
 *
 * 1.1.0 (DP2b) - three optional props, so the header still draws exactly as before when they are absent:
 *   - userName: the signed-in person, first in RightControls (data-name userLabel - not KT's userCoord,
 *     which is an administrator's tool and stays unrendered).
 *   - viewOnly: the page's right is RO - a quiet gold "view only" under the name.
 *   - onSignOut: the logout button goes live (title "Sign out"); without it, it stays drawn and inert.
 *
 * Inline style only where the oracle BINDS a style (the underlines); every static value is in shell.css.
 *
 * Changelog:
 *   1.1.0  DP2b: userName / viewOnly / onSignOut. Nothing else moved.
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

export const VERSION = '1.1.0';

/** the live logout button's hover title (DP2b); the inert one keeps LOGOUT_TITLE */
export const SIGN_OUT_TITLE = 'Sign out';

export type HeaderToolbarProps = {
  /** the oracle's session.custom.activePage, derived from the router path (rules.activeKeyFor) */
  activeKey: string;
  /** dateFormat(now(), "MMM d") */
  dateText: string;
  /** dateFormat(now(), "HH:mm:ss") */
  timeText: string;
  onPlannex: () => void;
  onFullscreen: () => void;
  /** DP2b: the signed-in person's name; absent or '' -> no label */
  userName?: string | undefined;
  /** DP2b: the active page's right is RO */
  viewOnly?: boolean | undefined;
  /** DP2b: Sign out; absent -> the logout button stays drawn and inert */
  onSignOut?: (() => void) | undefined;
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
  userName = '',
  viewOnly = false,
  onSignOut,
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
        {userName !== '' ? (
          <span
            className="who"
            data-name="userLabel"
            title={viewOnly ? `${userName} - view only on this page` : userName}
          >
            <span className="nm">{userName}</span>
            {viewOnly ? (
              <span className="ro" data-name="viewOnly">
                view only
              </span>
            ) : null}
          </span>
        ) : null}
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
              {onSignOut ? (
                <button
                  type="button"
                  className="sq"
                  data-name="logoutBtn"
                  title={SIGN_OUT_TITLE}
                  aria-label="sign out"
                  onClick={onSignOut}
                >
                  <Glyph paths={LOGOUT} colour="#1F1F1F" px={14} />
                </button>
              ) : (
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
              )}
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
