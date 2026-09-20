/**
 * Azztec_SaaS_web_workorders_icons_v1_0_1.tsx  ->  web/src/features/workorders/icons.tsx
 * Version:  1.0.1   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §3.4 · OD-27, OD-31
 * Source:   Workmate_Material_Icons_Library_v1_1_0.svg (2026-09-16, 192 material/* icons, paths only,
 *           geometry Google Material Icons baseline) - the 13 glyphs WOMaint names that the shell's
 *           icons.tsx 1.0.0 does not already carry, COPIED BY SCRIPT, never typed (the S1k rule).
 *           Every one is paths only at viewBox 0 0 24 24, asserted when this file was generated;
 *           `schedule` is the one with two paths. Character counts were checked against the library
 *           after extraction, so a truncated path would have failed the cut, not the screen.
 *
 * `assignment` and `search` are NOT duplicated here - WOMaint uses both and the shell already holds
 * them, so they are re-exported below. One copy of each path in the tree; a geometry fix lands once.
 *
 * Google Material Icons are Apache 2.0. Inline SVG on purpose: no icon font, no CDN, nothing fetched
 * at runtime (OD-27 / OD-31, the shell's precedent).
 *
 * Changelog:
 *   1.0.1  Smoke fix, before the tag. WO_MATERIAL deliberately omits assignment and search (the shell
 *          holds them), but WO_STATUS_CARDS names `assignment` as one of its eight glyphs - so
 *          WO_MATERIAL.assignment was undefined and WoIcon threw for every status row: 24 failures.
 *          GLYPHS below is the complete fifteen, and WoGlyphName is its key type, so a glyph named
 *          in a table but absent from the record is now a COMPILE error. The re-export still means
 *          one copy of each path in the tree; only the lookup changed.
 *   1.0.0  Initial W1b.
 */
import { MATERIAL as SHELL_MATERIAL, VIEW_BOX as SHELL_VIEW_BOX } from '../shell/icons';

export const VERSION = '1.0.1';

/** the sprite's viewBox, one value for all 13 - identical to the shell's, asserted in the test */
export const VIEW_BOX = '0 0 24 24';

export type WoIconName =
  | 'block'
  | 'cancel'
  | 'check_circle'
  | 'clear_all'
  | 'close'
  | 'edit'
  | 'group_add'
  | 'local_printshop'
  | 'play_circle_filled'
  | 'save'
  | 'schedule'
  | 'thumb_up'
  | 'warning';

/** material/<name> -> the <path d> strings, in file order. Copied from the library, never typed. */
export const WO_MATERIAL: Readonly<Record<WoIconName, ReadonlyArray<string>>> = {
  block: ['M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM4 12c0-4.42 3.58-8 8-8 1.85 0 3.55.63 4.9 1.69L5.69 16.9A7.902 7.902 0 0 1 4 12zm8 8c-1.85 0-3.55-.63-4.9-1.69L18.31 7.1A7.902 7.902 0 0 1 20 12c0 4.42-3.58 8-8 8z'],
  cancel: ['M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z'],
  check_circle: ['M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z'],
  clear_all: ['M5 13h14v-2H5v2zm-2 4h14v-2H3v2zM7 7v2h14V7H7z'],
  close: ['M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z'],
  edit: ['M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a.996.996 0 0 0 0-1.41l-2.34-2.34a.996.996 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z'],
  group_add: ['M22 9V7h-2v2h-2v2h2v2h2v-2h2V9zM8 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zM8 13c-2.67 0-8 1.34-8 4v3h16v-3c0-2.66-5.33-4-8-4zM12.51 4.05C13.43 5.11 14 6.49 14 8s-.57 2.89-1.49 3.95C14.47 11.7 16 10.04 16 8s-1.53-3.7-3.49-3.95zM16.53 13.83C17.42 14.66 18 15.7 18 17v3h2v-3c0-1.45-1.59-2.51-3.47-3.17z'],
  local_printshop: ['M19 8H5c-1.66 0-3 1.34-3 3v6h4v4h12v-4h4v-6c0-1.66-1.34-3-3-3zm-3 11H8v-5h8v5zm3-7c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zm-1-9H6v4h12V3z'],
  play_circle_filled: ['M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z'],
  save: ['M17 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z'],
  schedule: ['M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z', 'M12.5 7H11v6l5.25 3.15.75-1.23-4.5-2.67z'],
  thumb_up: ['M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z'],
  warning: ['M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z'],
};

/** WOMaint's other two glyphs, already in the shell - re-exported so there is one copy in the tree. */
export const ASSIGNMENT: ReadonlyArray<string> = SHELL_MATERIAL.assignment;
export const SEARCH: ReadonlyArray<string> = SHELL_MATERIAL.search;

/** Every glyph WOMaint draws, whichever file owns the paths. Index this, never WO_MATERIAL. */
export type WoGlyphName = WoIconName | 'assignment' | 'search';

export const GLYPHS: Readonly<Record<WoGlyphName, ReadonlyArray<string>>> = {
  ...WO_MATERIAL,
  assignment: ASSIGNMENT,
  search: SEARCH,
};

/** The shell's viewBox, re-exported so the test can assert the two files agree. */
export const SHELL_VIEWBOX = SHELL_VIEW_BOX;

export interface WoIconProps {
  paths: ReadonlyArray<string>;
  size?: number;
  colour?: string;
  className?: string;
}

/** One renderer for every glyph on the page. aria-hidden: the label beside it is the accessible name. */
export function WoIcon({ paths, size = 20, colour = 'currentColor', className }: WoIconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      focusable="false"
      height={size}
      viewBox={VIEW_BOX}
      width={size}
    >
      {paths.map((d) => (
        <path d={d} fill={colour} key={d} />
      ))}
    </svg>
  );
}
