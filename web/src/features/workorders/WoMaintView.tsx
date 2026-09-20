/**
 * Azztec_SaaS_web_workorders_WoMaintView_v1_0_1.tsx  ->  web/src/features/workorders/WoMaintView.tsx
 * Version:  1.0.1   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §3.11 · OD-29, OD-34, OD-51, OD-73, OD-77
 * Oracle:   WOMaint_v16_28_3 MainContent - WOListPanel | DetailPanel, the five hand-built main tabs
 *           and six sub-tabs, and the view's own seeds (woTypeFilter 'N', includeClosed 0,
 *           includeArchive 0, activeMainTab 0, activeSubTab 0).
 *
 * Split the PlannerView way (S1f's contingency, taken up front): the view is props-driven, so its
 * test renders it with no router, no route tree and no memory history and still proves the wire.
 * validateSearch lives here beside the types it guards, exactly as the planner's does - the route
 * file stays three lines of router API and exports Route only (Landmines §C).
 *
 * OD-73: type/closed/archive/q live in the URL; limit and offset do not. Paging position is not
 * something a shared link should reproduce, and `pageCount` here is the Load more state (OD-77) -
 * it resets whenever a filter changes, because a fifth page of the previous filter is meaningless.
 *
 * The four tabs W1c brings and the five sub-tabs it does not are DRAWN and inert (OD-51), so the
 * page looks like the oracle and never claims to do what it cannot (OD-34).
 *
 * The view imports wo.css, as PlannerView imports planner.css and AppShell imports shell.css - that
 * import is the only thing that puts the stylesheet in the build.
 *
 * Changelog:
 *   1.0.1  Smoke fix, before the tag. The record slot was a four-deep ternary whose last arm tested
 *          `record.data` after isPending and isError had already been ruled out - lint called it
 *          dead, correctly. It is a RecordPane with early returns now: same four states, each one
 *          readable, and the narrowing does the work the ternary was pretending to do.
 *   1.0.0  Initial W1b.
 */
import { useEffect, useState } from 'react';

import './wo.css';

import { WoDetailsTab } from './WoDetailsTab';
import { WoFiltersRow } from './WoFiltersRow';
import { WoListPanel } from './WoListPanel';
import { WoRecordCard } from './WoRecordCard';
import { PAGE_SIZE, useWoList, useWoRecord } from './useWorkorders';
import type { WoRecord } from '../../api/client';
import { SUB_TABS, mainTabs } from './rules';

export const VERSION = '1.0.1';

export type WoType = '' | 'N' | 'CP' | 'M';
export type ModeFlag = 0 | 1 | 2;

export interface WoSearch {
  type: WoType;
  closed: ModeFlag;
  archive: ModeFlag;
  q: string;
}

function isWoType(v: unknown): v is WoType {
  return v === '' || v === 'N' || v === 'CP' || v === 'M';
}

function isFlag(v: unknown): v is ModeFlag {
  return v === 0 || v === 1 || v === 2;
}

/** OD-29 / OD-73. Plain guards, no zod adapter. A junk param falls back to the view's own seed. */
export function validateSearch(search: Record<string, unknown>): WoSearch {
  const closedNum = Number(search.closed);
  const archiveNum = Number(search.archive);
  return {
    type: isWoType(search.type) ? search.type : 'N',
    closed: isFlag(closedNum) ? closedNum : 0,
    archive: isFlag(archiveNum) ? archiveNum : 0,
    q: typeof search.q === 'string' ? search.q : '',
  };
}

export type WoMaintViewProps = WoSearch & {
  /** 0 when no work order is selected - the route's $id, or nothing on /workorders */
  woId: number;
  /** the URL writer; the route passes navigate(), the test passes a spy */
  onSearch: (next: Partial<WoSearch>) => void;
  /** the selection writer; the route navigates to /workorders/$id */
  onSelect: (woId: number) => void;
};

/** The record slot's four states, one return each - the arms lint could not tell apart as a ternary. */
function RecordPane({
  woId,
  loading,
  error,
  record,
  subTab,
  onSubTab,
}: {
  woId: number;
  loading: boolean;
  error: boolean;
  record: WoRecord | undefined;
  subTab: string;
  onSubTab: (key: string) => void;
}) {
  if (woId === 0) return <p className="wo-empty">Select a work order from the list.</p>;
  if (loading) return <p className="wo-empty">Loading work order {woId}...</p>;
  if (error) return <p className="wo-error">That work order could not be loaded.</p>;
  if (!record) return null;
  return (
    <>
      <WoRecordCard record={record} />

      <div className="wo-tabrow" role="tablist">
        {SUB_TABS.map((t) =>
          t.live ? (
            <button
              aria-selected={subTab === t.key}
              className={`wo-tab wo-subtab${subTab === t.key ? ' on' : ''}`}
              data-subtab={t.key}
              key={t.key}
              onClick={() => onSubTab(t.key)}
              role="tab"
              type="button"
            >
              {t.label}
            </button>
          ) : (
            <span
              aria-disabled="true"
              className="wo-tab wo-subtab"
              data-subtab={t.key}
              key={t.key}
              role="tab"
              title="arrives with a later slice (OD-51)"
            >
              {t.label}
            </span>
          ),
        )}
      </div>

      {subTab === 'details' ? <WoDetailsTab record={record} /> : null}
    </>
  );
}

export function WoMaintView({ type, closed, archive, q, woId, onSearch, onSelect }: WoMaintViewProps) {
  const [pageCount, setPageCount] = useState(1);
  const [subTab, setSubTab] = useState('details');

  /** A filter change invalidates the paging position - page 5 of the old filter means nothing. */
  useEffect(() => {
    setPageCount(1);
  }, [type, closed, archive, q]);

  const list = useWoList({
    woType: type,
    includeClosed: closed,
    includeArchive: archive,
    search: q,
    limit: PAGE_SIZE * pageCount,
    offset: 0,
  });
  const record = useWoRecord(woId);

  const rows = list.data?.rows ?? [];
  const linkedCount = 0; // the Linked WO count arrives with W1c's /linked read
  const tabs = mainTabs(linkedCount);

  return (
    <div className="wm-wo">
      <div className="wo-main">
        <WoListPanel
          count={list.data?.count ?? 0}
          loading={list.isPending}
          more={list.data?.more ?? false}
          onLoadMore={() => setPageCount((n) => n + 1)}
          onSelect={onSelect}
          onTypeChange={(value) => onSearch({ type: value })}
          rows={rows}
          selectedId={woId}
          woType={type}
        />

        <div className="wo-detail">
          <WoFiltersRow
            includeArchive={archive}
            includeClosed={closed}
            onArchiveChange={(v) => onSearch({ archive: v })}
            onClosedChange={(v) => onSearch({ closed: v })}
            onSearchChange={(v) => onSearch({ q: v })}
            search={q}
          />

          <div className="wo-tabbox">
            <div className="wo-tabrow" role="tablist">
              {tabs.map((t) =>
                t.live ? (
                  <button
                    aria-selected="true"
                    className="wo-tab on"
                    data-tab={t.key}
                    key={t.key}
                    role="tab"
                    type="button"
                  >
                    {t.label}
                  </button>
                ) : (
                  <span
                    aria-disabled="true"
                    className="wo-tab"
                    data-tab={t.key}
                    key={t.key}
                    role="tab"
                    title="arrives with the W1c slice (OD-51)"
                  >
                    {t.label}
                  </span>
                ),
              )}
            </div>

            <RecordPane
              error={record.isError}
              loading={record.isPending}
              onSubTab={setSubTab}
              record={record.data}
              subTab={subTab}
              woId={woId}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
