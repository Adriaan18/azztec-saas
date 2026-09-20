/**
 * Azztec_SaaS_web_workorders_WoRecordCard_v1_0_0.tsx  ->  web/src/features/workorders/WoRecordCard.tsx
 * Version:  1.0.0   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §3.9 · OD-34, OD-51, OD-65, OD-74, OD-79
 * Oracle:   WOMaint_v16_28_3 - WOHeaderCard (minHeight 130, pad 14/18, the ID pill at 220x36 and the
 *           two symbol rows right-aligned), ScheduleAssignmentRow (wrap, gap 6; Schedule and
 *           Assignment at flex 0.9, AllResources at flex 1), tblAllResources (7 columns, last five
 *           right-aligned), lblAllResourcesValue (basis 538, 10px bold, right, ellipsis).
 *
 * Read-only. Every value arrives formatted from the API or from rules.ts - this file decides no
 * colours and parses no dates. The oracle hides each symbol row when its value is empty or 0; ported
 * as the same condition, so a record with no progress shows no progress row rather than eight unlit
 * cards pretending to be a control (OD-34).
 *
 * detailsMissing (OD-65) is the seven live headers with no WO_N_Details row: the schedule numbers
 * are genuinely absent, not zero, so the card says so instead of printing 0.0 six times.
 *
 * Changelog:
 *   1.0.0  Initial W1b.
 */
import type { ReactNode } from 'react';

import type { WoRecord } from '../../api/client';
import { WO_MATERIAL, WoIcon } from './icons';
import { displayDateTime, displayStamp, idPillStyle, numText, respUsersLine } from './rules';
import { CompleteWithinSeg, WoProgressRow, WoStatusRow } from './symbols';

export const VERSION = '1.0.0';

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="wo-frow">
      <span className="wo-flabel">{label}</span>
      {children}
    </div>
  );
}

function ReadOnly({ value, className = '' }: { value: string; className?: string }) {
  return <span className={`wo-val ro ${className}`.trim()}>{value}</span>;
}

export function WoRecordCard({ record }: { record: WoRecord }) {
  const r = record;
  return (
    <>
      <section aria-label="Work order header" className="wo-card head">
        <div className="wo-frow" style={{ alignItems: 'flex-start' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Field label="Work Order ID :">
              <span className="wo-idpill" style={idPillStyle(r.status)}>
                {r.sid}
              </span>
              <span className="wo-titlefield">{r.title}</span>
            </Field>
            <Field label="Asset :">
              <ReadOnly value={r.asset} />
              <span className="wo-small">{r.assetTitle}</span>
            </Field>
            <Field label="Location :">
              <ReadOnly value={r.loc} />
              <span className="wo-small">{r.hierarchy}</span>
            </Field>
          </div>

          <div className="wo-symbols">
            {r.prog > 0 ? <WoProgressRow prog={r.prog} progressAll={r.progressAll} /> : null}
            {r.status === '' ? null : <WoStatusRow status={r.status} />}
          </div>
        </div>
      </section>

      <div className="wo-schedrow">
        <section aria-label="Schedule" className="wo-card sched">
          <h3 className="wo-cardtitle">Schedule</h3>
          {r.detailsMissing ? (
            <p className="wo-empty">
              This work order has no detail record, so it carries no schedule, cost or progress
              figures.
            </p>
          ) : (
            <>
              <Field label="Complete within :">
                <CompleteWithinSeg value={r.completeWithin} />
              </Field>
              <Field label="Start Date :">
                <ReadOnly value={displayDateTime(r.start, r.startTime)} />
              </Field>
              <Field label="End Date :">
                <ReadOnly value={displayDateTime(r.end, r.endTime)} />
              </Field>
              <Field label="Logged Date :">
                <ReadOnly value={displayStamp(r.logged)} />
              </Field>
              <Field label="Duration (hrs) :">
                <ReadOnly value={numText(r.durationHrs)} />
              </Field>
              <Field label="Est. Cost :">
                <ReadOnly value={numText(r.estCost)} />
              </Field>
              <Field label="Down Time :">
                <ReadOnly value={numText(r.downTime)} />
              </Field>
              <Field label="Week No :">
                <ReadOnly value={numText(r.weekNo)} />
              </Field>
            </>
          )}
        </section>

        <section aria-label="Assignment" className="wo-card sched">
          <h3 className="wo-cardtitle">Assignment</h3>
          <Field label="Priority :">
            <ReadOnly value={r.priTitle} />
          </Field>
          <Field label="Person Resp. :">
            <ReadOnly value={r.respUserName} />
          </Field>
          <Field label="Charge To :">
            <ReadOnly value={r.chargeToName} />
            <span className="wo-desc">{r.chargeToShort}</span>
          </Field>
          <Field label="Responsibility :">
            <ReadOnly value={r.respSupplierName} />
            <span className="wo-desc">{r.respSupplierShort}</span>
          </Field>
          <Field label="Resp. Users :">
            <span className="wo-val ro resp">{respUsersLine(r.respUsers)}</span>
            <span
              aria-disabled="true"
              aria-label="Manage responsible users"
              className="wo-btn wo-shadow-grey"
              data-inert="Manage resp. users"
              role="button"
              title="assignment arrives with the write slice (OD-51)"
            >
              <WoIcon colour="#5D6E71" paths={WO_MATERIAL.group_add} size={16} />
            </span>
          </Field>
        </section>

        <section aria-label="All resources" className="wo-card res">
          <h3 className="wo-cardtitle">All Resources</h3>
          <table className="wo-table">
            <thead>
              <tr>
                <th scope="col">Type</th>
                <th scope="col">Item</th>
                <th scope="col" style={{ textAlign: 'right' }}>
                  Plan Qty
                </th>
                <th scope="col" style={{ textAlign: 'right' }}>
                  Plan $
                </th>
                <th scope="col" style={{ textAlign: 'right' }}>
                  Act Qty
                </th>
                <th scope="col" style={{ textAlign: 'right' }}>
                  Act $
                </th>
                <th scope="col" style={{ textAlign: 'right' }}>
                  Diff $
                </th>
              </tr>
            </thead>
            <tbody>
              {r.resources.rows.map((row, i) => (
                <tr key={`${row.type}-${row.item}-${i}`}>
                  <td>{row.type}</td>
                  <td>{row.item}</td>
                  <td style={{ textAlign: 'right' }}>{numText(row.planQty)}</td>
                  <td style={{ textAlign: 'right' }}>{numText(row.planCost)}</td>
                  <td style={{ textAlign: 'right' }}>{numText(row.actQty)}</td>
                  <td style={{ textAlign: 'right' }}>{numText(row.actCost)}</td>
                  <td style={{ textAlign: 'right' }}>{numText(row.delta)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {/* the API composes this string; printed byte-for-byte, never rebuilt here */}
          <p className="wo-resline">{r.resources.line}</p>
        </section>
      </div>
    </>
  );
}
