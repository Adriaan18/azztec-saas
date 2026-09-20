/**
 * Azztec_SaaS_web_workorders_WoFiltersRow_v1_0_0.tsx  ->  web/src/features/workorders/WoFiltersRow.tsx
 * Version:  1.0.0   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §3.8 · OD-34, OD-51, OD-52, OD-78, OD-79
 * Oracle:   WOMaint_v16_28_3 FilterRow - SearchBox (240px, placeholder 'Search work orders...'),
 *           FilterChip_Closed / FilterChip_Archive (lit = full token + glow + scale(1.1) + #FFF/700,
 *           unlit = the same colour at 0.10 and 500), then the button strip.
 *
 * OD-79 as signed: the eleven write controls are DRAWN and inert - aria-disabled, no handler, an
 * OD-51 title naming the slice that brings them. Never `disabled`: Chrome shows no hover title on a
 * disabled button, so the user would get a dead control with no explanation (the S1k lesson). Not
 * rendered at all: the Summary toggle, the three tips anchors, the AI embed, the toast bar - chrome
 * that would have to lie about what it does (OD-34, OD-52).
 *
 * The mode chips are mutually exclusive here exactly as the oracle's scripts make them: turning one
 * on zeroes the other. Both are tri-state on the wire (0/1/2) but the oracle's row only ever toggles
 * 0 and 1 - 2 is reachable from the API and the URL, not from this row.
 *
 * Changelog:
 *   1.0.0  Initial W1b.
 */
import { WO_MATERIAL, WoIcon } from './icons';
import type { WoIconName } from './icons';

export const VERSION = '1.0.0';

/** OD-51: every inert control says which slice brings it, in its own words. */
interface InertControl {
  icon: WoIconName;
  label: string;
  arrives: string;
}

export const INERT_CONTROLS: ReadonlyArray<InertControl> = [
  { icon: 'edit', label: 'Edit', arrives: 'editing arrives with the write slice (OD-51)' },
  { icon: 'save', label: 'Save', arrives: 'saving arrives with the write slice (OD-51)' },
  { icon: 'close', label: 'Cancel', arrives: 'editing arrives with the write slice (OD-51)' },
  {
    icon: 'local_printshop',
    label: 'Print',
    arrives: 'printing arrives with the print slice (OD-51)',
  },
  { icon: 'clear_all', label: 'Clone', arrives: 'cloning arrives with the write slice (OD-51)' },
  { icon: 'cancel', label: 'Delete', arrives: 'deleting arrives with the write slice (OD-51)' },
  { icon: 'group_add', label: 'Manage resp. users', arrives: 'assignment arrives with the write slice (OD-51)' },
];

export interface WoFiltersRowProps {
  search: string;
  includeClosed: 0 | 1 | 2;
  includeArchive: 0 | 1 | 2;
  onSearchChange: (value: string) => void;
  onClosedChange: (value: 0 | 1 | 2) => void;
  onArchiveChange: (value: 0 | 1 | 2) => void;
}

export function WoFiltersRow({
  search,
  includeClosed,
  includeArchive,
  onSearchChange,
  onClosedChange,
  onArchiveChange,
}: WoFiltersRowProps) {
  /** The oracle zeroes the other chip rather than allowing both - ported as one call each way. */
  function toggleClosed() {
    if (includeClosed > 0) {
      onClosedChange(0);
      return;
    }
    onArchiveChange(0);
    onClosedChange(1);
  }

  function toggleArchive() {
    if (includeArchive > 0) {
      onArchiveChange(0);
      return;
    }
    onClosedChange(0);
    onArchiveChange(1);
  }

  return (
    <div className="wo-filters" role="group" aria-label="Work order filters">
      <WoIcon colour="#5D6E71" paths={WO_MATERIAL.schedule} size={16} />
      <input
        aria-label="Search work orders"
        className="wo-search"
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search work orders..."
        type="search"
        value={search}
      />
      <button
        aria-label="Clear search"
        className="wo-btn wo-shadow-grey"
        onClick={() => onSearchChange('')}
        type="button"
      >
        <WoIcon colour="#5D6E71" paths={WO_MATERIAL.close} size={16} />
      </button>

      <span
        aria-pressed={includeClosed > 0}
        className={`wo-modechip closed${includeClosed > 0 ? ' on' : ''}`}
        data-chip="closed"
        onClick={toggleClosed}
        role="button"
        tabIndex={0}
      >
        Closed
      </span>
      <span
        aria-pressed={includeArchive > 0}
        className={`wo-modechip archive${includeArchive > 0 ? ' on' : ''}`}
        data-chip="archive"
        onClick={toggleArchive}
        role="button"
        tabIndex={0}
      >
        Archive
      </span>

      {INERT_CONTROLS.map((c) => (
        <span
          aria-disabled="true"
          aria-label={c.label}
          className="wo-btn wo-shadow-grey"
          data-inert={c.label}
          key={c.label}
          role="button"
          title={c.arrives}
        >
          <WoIcon colour="#5D6E71" paths={WO_MATERIAL[c.icon]} size={16} />
        </span>
      ))}
    </div>
  );
}
