/**
 * Azztec_SaaS_web_workorders_record_fixture_v1_0_0.ts  ->  web/src/features/workorders/record.fixture.ts
 * Version:  1.0.0   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md - flagged as the 25th card at cut time
 *           (the range.fixture.ts precedent: four test files need one record, so it lives once).
 * Values:   WO 662704 as the W1a smoke read it on RST (log 2026-09-19 1.2.0 §4c) - sid 3CL-260826-010,
 *           V / prog 6 / week / weekNo 2026.35, the five-title hierarchy, the resources line - so a
 *           component test renders the same record the live smoke measured.
 *
 * Test helper only - never imported by src code. The one frontend file that constructs a WoRecord
 * literal, so a contract change on WoRecord lands here first (the range.fixture rule).
 *
 * Changelog:
 *   1.0.0  Initial W1b.
 */
import type { ProgressRow, WoRecord } from '../../api/client';

export const VERSION = '1.0.0';

/** RST's eight active dbo.Progress rows (nine minus the inactive '9 Machining') - OD-67's shape. */
export const PROGRESS_ALL_RST: ReadonlyArray<ProgressRow> = [
  { id: 1, title: 'No Progress', short: 'NONE' },
  { id: 2, title: 'Waiting Parts', short: 'WAIT' },
  { id: 3, title: '25% complete', short: '25' },
  { id: 4, title: '50% complete', short: '50' },
  { id: 5, title: '75% complete', short: '75' },
  { id: 6, title: '100% Complete', short: '100' },
  { id: 7, title: 'Scheduled', short: 'SCHED' },
  { id: 8, title: 'Assigned', short: 'ASSIGN' },
];

const HIERARCHY_RAW =
  '{(1)(RST-00)(Red Stag Timber Waipa)}{(6586)(3-00)(3 Secondary Processing)}{(67)(3CL-00)(08 Coastal)}' +
  '{(407)(3CL-090)(090 Viking Bins)}{(1963)(3CL-090.170)(170 Bin 16)}';

const BASE: WoRecord = {
  // envelope (OD-14)
  ok: true,
  apiVersion: '1.0.0',
  actor: 21,
  ms: 122,
  // identity + status
  id: 662704,
  sid: '3CL-260826-010',
  title: 'Check bin 16 level PE',
  status: 'V',
  statusTitle: 'Active',
  type: 'N',
  overDue: false,
  weekNo: 2026.35,
  start: '2026-08-26',
  startTime: '19:17',
  end: '2026-09-02',
  endTime: '19:17',
  logged: '2026-08-26 19:17:09',
  // company / asset / location
  companyId: 1,
  companyTitle: 'Red Stag Timber',
  assetId: 4021,
  asset: '3CL-090.170.PE1',
  assetTitle: 'Bin 16 Level PE',
  locId: 1963,
  loc: '3CL-090.170',
  locTitle: '170 Bin 16',
  hierarchy: 'Red Stag Timber Waipa > 3 Secondary Processing > 08 Coastal > 090 Viking Bins > 170 Bin 16',
  hierarchyRaw: HIERARCHY_RAW,
  // schedule numbers
  durationHrs: 0,
  estCost: 0,
  downTime: 0,
  // references, resolved server-side (OD-66)
  priId: 1,
  priShort: 'P2',
  priTitle: 'Priority 2',
  groupId: 3,
  groupShort: 'MAINT',
  groupTitle: 'Maintenance',
  reasonId: 2,
  reasonTitle: 'Electrical Fault',
  faultId: 4,
  faultTitle: 'Calibration',
  costCenterId: 652,
  costCenterTitle: '652 KPP Plant',
  accountId: 627,
  accountTitle: '627 Outfeed',
  chargeToId: 11,
  chargeToShort: 'TM-MAINT',
  chargeToName: 'Maintenance Team',
  respSupplierId: 12,
  respSupplierShort: 'TM-ELEC',
  respSupplierName: 'Electrical Team',
  woc1Id: 0,
  woc1Title: '',
  woc2Id: 0,
  woc2Title: '',
  woc3Id: 0,
  woc3Title: '',
  ref1: '',
  ref2: '',
  // progress + notes
  prog: 6,
  progTitle: '100% Complete',
  notes: 'Last few bins are causing issues. Monitor to try and isolate problems.',
  // people + misc detail columns
  requestedById: 113,
  respUserId: 0,
  respUserName: '',
  conditionId: 0,
  generatedFrom: 0,
  intrusive: false,
  intrusiveComplete: false,
  intrusiveCompleteDate: '',
  firstActivity: '',
  lastActivity: '',
  meterId: 0,
  meterReading: 0,
  printed: false,
  progressDate: '2026-08-26 19:19:04',
  // the six stamp rows
  createdBy: 'KF',
  ackBy: '',
  ackDate: '',
  approvedBy: '',
  approvedDate: '',
  closedBy: '',
  closedDate: '',
  cancelledBy: '',
  cancelledDate: '',
  lastSaveBy: 'KF',
  lastSaveDate: '2026-08-26 19:19:04',
  // derived (rules.py)
  completeWithin: 'week',
  detailsMissing: false,
  respUsers: [],
  resources: {
    rows: [
      {
        type: 'Labour',
        item: 'E1',
        planQty: null,
        planCost: null,
        actQty: 1,
        actCost: 36.52,
        delta: 36.52,
      },
    ],
    planned: 0,
    actual: 36.52,
    diff: 36.52,
    line: 'Planned $0.00  |  Actual $36.52  |  Diff +$36.52',
  },
  progressAll: [...PROGRESS_ALL_RST],
  filtersFor: { woType: 'N', includeClosed: 0, includeArchive: 0, search: '', limit: 200, offset: 0 },
};

/** WO 662704, overridable per test. Spread-shallow: replace respUsers/resources whole when overriding. */
export function recordFixture(overrides: Partial<WoRecord> = {}): WoRecord {
  return { ...BASE, ...overrides };
}
