/**
 * Azztec_SaaS_web_workorders_WoListPanel_v1_0_0.tsx  ->  web/src/features/workorders/WoListPanel.tsx
 * Version:  1.0.0   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §3.7 · OD-73, OD-77
 * Oracle:   WOMaint_v16_28_3 WOListPanel - WOListHeader (gradient + gold border), TypeToggle (4 chips),
 *           WOListTable (5 columns, WO_ID hidden, WO_IdStyled through WONumBadge at 130px),
 *           WOListFooter ('No of Records: ' + count).
 *
 * Presentational and controlled: every filter and the selection live in the URL (OD-73), so this
 * component holds no state and the route is the single source of truth for what the list shows.
 * The oracle's client-side 100-row pager is replaced by Load more (OD-77) - paging by offset against
 * the API's `more` flag, never a COUNT over 620k archived rows.
 *
 * Changelog:
 *   1.0.0  Initial W1b.
 */
import type { WoListRow } from '../../api/client';
import { TYPE_CHIPS, listTitle, recordCount } from './rules';
import { WoNumBadge } from './symbols';

export const VERSION = '1.0.0';

export interface WoListPanelProps {
  rows: ReadonlyArray<WoListRow>;
  count: number;
  more: boolean;
  woType: '' | 'N' | 'CP' | 'M';
  selectedId: number;
  loading: boolean;
  onTypeChange: (value: '' | 'N' | 'CP' | 'M') => void;
  onSelect: (woId: number) => void;
  onLoadMore: () => void;
}

export function WoListPanel({
  rows,
  count,
  more,
  woType,
  selectedId,
  loading,
  onTypeChange,
  onSelect,
  onLoadMore,
}: WoListPanelProps) {
  return (
    <section aria-label="Work order list" className="wo-list">
      <header className="wo-list-head">
        <span className="wo-list-title">{listTitle(woType)}</span>
        <div className="wo-typechips" role="group">
          {TYPE_CHIPS.map((c) => (
            <button
              aria-pressed={c.value === woType}
              className={`wo-chip${c.value === woType ? ' on' : ''}`}
              data-type={c.value === '' ? 'ALL' : c.value}
              key={c.label}
              onClick={() => onTypeChange(c.value)}
              type="button"
            >
              {c.label}
            </button>
          ))}
        </div>
      </header>

      <div className="wo-list-scroll">
        <table className="wo-table">
          <thead>
            <tr>
              <th scope="col">WO Number</th>
              <th scope="col">Title</th>
              <th scope="col">Asset</th>
              <th scope="col">Location</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                aria-selected={r.id === selectedId}
                className={r.id === selectedId ? 'on' : undefined}
                data-wo={r.id}
                key={r.id}
                onClick={() => onSelect(r.id)}
              >
                <td>
                  <WoNumBadge value={r.badge} />
                </td>
                <td>{r.title}</td>
                <td>{r.asset}</td>
                <td>{r.loc}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && !loading ? (
          <p className="wo-empty">No work orders match these filters.</p>
        ) : null}
        {more ? (
          <button className="wo-loadmore" onClick={onLoadMore} type="button">
            Load more
          </button>
        ) : null}
      </div>

      <footer className="wo-foot">{recordCount(count, more)}</footer>
    </section>
  );
}
