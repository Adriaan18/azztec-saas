/**
 * Azztec_SaaS_web_shell_AppShell_v1_1_0.tsx  ->  web/src/features/shell/AppShell.tsx
 * Version:  1.1.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md s3.5 . OD-50, OD-51, OD-54;
 *           Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6
 * Oracle:   page-config: every Workmate page docks HeaderToolbar top (50) and SideMenu left (50),
 *           cornerPriority top-bottom - the header owns the corner, the rail sits under it.
 *
 * The shell around every route: header + rail + a main cell the page fills. Props-driven and router-free
 * (the PlannerView precedent) - routes/__root.tsx passes the pathname and the Plannex navigation; the
 * test passes strings and spies.
 *
 * The clock is the one thing here that touches time, through lib/dates.ts (headerClock - the only module
 * that touches Date): one read per tick, a 1000 ms interval, cleared in the effect's cleanup because
 * StrictMode mounts twice in dev (Landmines s.C). Fullscreen is KT's "Toggle Page" action on the
 * Fullscreen API; Print is what KT's dispatcher does on every page this build has - the browser's print.
 * The two popup targets (PO, WO) do nothing here: their pages do not exist yet.
 *
 * 1.1.0 (DP2b): the signed-in person's name, the page's "view only" and Sign out pass straight through
 * to the header. All three are optional, so the shell still draws bare.
 *
 * Changelog:
 *   1.1.0  DP2b: userName / viewOnly / onSignOut, passed to HeaderToolbar. Nothing else moved.
 *   1.0.0  Initial S1k.
 */
import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';

import { HeaderToolbar } from './HeaderToolbar';
import { SideMenu } from './SideMenu';
import { activeKeyFor, printTarget } from './rules';
import { headerClock } from '../../lib/dates';

import './shell.css';

export const VERSION = '1.1.0';

export type AppShellProps = {
  /** the router's current pathname */
  pathname: string;
  /** navigate to /planner with the planner's own defaults (routes/__root.tsx passes navigate) */
  onPlannex: () => void;
  /** DP2b: the signed-in person's name */
  userName?: string | undefined;
  /** DP2b: the page's right is RO */
  viewOnly?: boolean | undefined;
  /** DP2b: Sign out */
  onSignOut?: (() => void) | undefined;
  children: ReactNode;
};

/** KT's fullscreen action, type Page, action Toggle */
function toggleFullscreen(): void {
  if (document.fullscreenElement) {
    void document.exitFullscreen();
  } else {
    void document.documentElement.requestFullscreen();
  }
}

export function AppShell({ pathname, onPlannex, userName, viewOnly, onSignOut, children }: AppShellProps) {
  const activeKey = activeKeyFor(pathname);
  const [clock, setClock] = useState(headerClock);

  useEffect(() => {
    const id = window.setInterval(() => setClock(headerClock()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const onPrint = () => {
    if (printTarget(activeKey) === 'browser') window.print();
  };

  return (
    <div className="wm-shell">
      <HeaderToolbar
        activeKey={activeKey}
        dateText={clock.date}
        timeText={clock.time}
        onPlannex={onPlannex}
        onFullscreen={toggleFullscreen}
        userName={userName}
        viewOnly={viewOnly}
        onSignOut={onSignOut}
      />
      <SideMenu activeKey={activeKey} onPrint={onPrint} />
      <main className="wm-shell-main">{children}</main>
    </div>
  );
}
