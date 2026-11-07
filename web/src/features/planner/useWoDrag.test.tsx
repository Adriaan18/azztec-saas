/**
 * Azztec_SaaS_web_planner_useWoDrag_test_v1_0_0.tsx  ->  web/src/features/planner/useWoDrag.test.tsx
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (useWoDrag.test.tsx row), §7 · pair of
 *           useWoDrag.ts 1.0.0
 *
 * The pure helpers, then the hook on a two-cell harness that has the grid's DOM contract
 * (.chip[data-wo], .cell[data-date]) and an empty layer. jsdom has no elementFromPoint, so it is stubbed
 * to answer with whichever cell the case is "over", and no setPointerCapture, which the controller
 * already tolerates. Pointer events are built as MouseEvents with a pointerId - they carry clientX /
 * clientY / button in every jsdom, PointerEvent or not - and dispatched inside act().
 *
 * Changelog:
 *   1.0.0  Initial DP3b.
 */
import { act, cleanup, render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  CLICK_SUPPRESS_MS,
  DRAG_THRESHOLD_PX,
  VERSION,
  chipFor,
  dayCellOf,
  ghostClass,
  pastThreshold,
  useWoDrag,
} from './useWoDrag';
import { mkWo } from './range.fixture';
import type { Wo } from '../../api/client/types.gen';

export const TEST_VERSION = '1.0.0';

const WO = mkWo({ id: 101, sid: 'WO-101', start: '2026-09-14' });
const LOCKED = mkWo({ id: 102, sid: 'PM-102', start: '2026-09-14', locked: true, movable: false });

type Api = ReturnType<typeof useWoDrag>;

function Harness({
  enabled,
  onDrop,
  onRefuse,
  expose,
}: {
  enabled: boolean;
  onDrop: (wo: Wo, toIso: string) => void;
  onRefuse: (wo: Wo) => void;
  expose: (api: Api) => void;
}) {
  const byId = new Map([WO, LOCKED].map((w) => [w.id, w]));
  const d = useWoDrag({ enabled, woById: (id) => byId.get(id), onDrop, onRefuse });
  expose(d);
  return (
    <div className={d.dragging ? 'wm-planner dragging' : 'wm-planner'}>
      <div className="grid-wrap" onPointerDown={d.onPointerDown}>
        <div className="cell" data-date="2026-09-14">
          <div className="chip cat-WO mv sel" data-wo="101" data-movable="1" title="WO-101">
            <span className="sid">WO-101</span>
            <span className="hrs">3.5h</span>
          </div>
          <div className="chip cat-PM locked" data-wo="102" data-movable="0">
            <span className="sid">PM-102</span>
          </div>
        </div>
        <div className="cell" data-date="2026-09-16" />
      </div>
      <div className="drag-layer" ref={d.layerRef} />
    </div>
  );
}

function must(root: ParentNode, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

/** A pointer event every jsdom can build: a MouseEvent with the pointerId the controller matches on. */
function pointer(type: string, target: EventTarget, x: number, y: number, id = 1, button = 0) {
  const ev = new MouseEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, button });
  Object.defineProperty(ev, 'pointerId', { value: id });
  act(() => {
    target.dispatchEvent(ev);
  });
  return ev;
}

describe('useWoDrag - pure helpers', () => {
  it('carries its version and the oracle numbers', () => {
    expect(VERSION).toBe('1.0.0');
    expect(DRAG_THRESHOLD_PX).toBe(6);
    expect(CLICK_SUPPRESS_MS).toBe(50);
  });

  it('pastThreshold: either axis at 6 px starts the drag, both under it is a click', () => {
    expect(pastThreshold(5, 5)).toBe(false);
    expect(pastThreshold(-5, 0)).toBe(false);
    expect(pastThreshold(6, 0)).toBe(true);
    expect(pastThreshold(0, -6)).toBe(true);
  });

  it('chipFor: a chip or its label starts a drag; the hours badge, a button or an input never do', () => {
    document.body.innerHTML =
      '<div class="chip" data-wo="1"><span class="sid">A</span><span class="hrs">2h</span></div><button class="chip">b</button><input />';
    const chip = must(document, '.chip');
    expect(chipFor(chip)).toBe(chip);
    expect(chipFor(must(document, '.sid'))).toBe(chip);
    expect(chipFor(must(document, '.hrs'))).toBeNull();
    expect(chipFor(must(document, 'button'))).toBeNull();
    expect(chipFor(must(document, 'input'))).toBeNull();
    expect(chipFor(null)).toBeNull();
    document.body.innerHTML = '';
  });

  it('dayCellOf finds the nearest [data-date]', () => {
    document.body.innerHTML = '<div class="cell" data-date="2026-09-16"><div class="list"><i></i></div></div>';
    expect(dayCellOf(must(document, 'i'))?.getAttribute('data-date')).toBe('2026-09-16');
    expect(dayCellOf(null)).toBeNull();
    document.body.innerHTML = '';
  });

  it('ghostClass drops the selection and the fade, adds .ghost', () => {
    expect(ghostClass('chip cat-WO mv sel dragging')).toBe('chip cat-WO mv ghost');
  });
});

describe('useWoDrag - the hook', () => {
  let over: Element | null = null;
  const realElementFromPoint = Object.getOwnPropertyDescriptor(document, 'elementFromPoint');

  beforeEach(() => {
    over = null;
    Object.defineProperty(document, 'elementFromPoint', { configurable: true, value: () => over });
  });
  afterEach(() => {
    cleanup();
    if (realElementFromPoint) Object.defineProperty(document, 'elementFromPoint', realElementFromPoint);
    else Reflect.deleteProperty(document, 'elementFromPoint');
  });

  function setup(enabled = true) {
    const onDrop = vi.fn();
    const onRefuse = vi.fn();
    const api: { current: Api | null } = { current: null };
    const r = render(
      <Harness
        enabled={enabled}
        onDrop={onDrop}
        onRefuse={onRefuse}
        expose={(a) => {
          api.current = a;
        }}
      />,
    );
    const chip = must(r.container, '[data-wo="101"]');
    const target = must(r.container, '[data-date="2026-09-16"]');
    const home = must(r.container, '[data-date="2026-09-14"]');
    return { ...r, onDrop, onRefuse, api, chip, target, home };
  }

  it('a press that moves less than 6 px is a click: nothing ghosts, nothing drops', () => {
    const s = setup();
    pointer('pointerdown', s.chip, 100, 100);
    pointer('pointermove', document, 104, 103);
    pointer('pointerup', document, 104, 103);
    expect(s.container.querySelector('.ghost')).toBeNull();
    expect(s.onDrop).not.toHaveBeenCalled();
    expect(s.api.current?.clickSuppressed()).toBe(false);
  });

  it('a drag onto another day ghosts the chip, outlines the cell and drops there', () => {
    const s = setup();
    pointer('pointerdown', s.chip, 100, 100);
    over = s.target;
    pointer('pointermove', document, 140, 100);
    const ghost = must(s.container, '.drag-layer .ghost');
    expect(ghost.className).toBe('chip cat-WO mv ghost');
    expect(ghost.hasAttribute('data-wo')).toBe(false);
    expect(s.chip.classList.contains('dragging')).toBe(true);
    expect(s.target.classList.contains('drop')).toBe(true);
    expect(must(s.container, '.wm-planner').className).toBe('wm-planner dragging');
    expect(s.api.current?.isActive()).toBe(true);

    pointer('pointerup', document, 140, 100);
    expect(s.onDrop).toHaveBeenCalledTimes(1);
    expect(s.onDrop).toHaveBeenCalledWith(WO, '2026-09-16');
    expect(s.container.querySelector('.ghost')).toBeNull();
    expect(s.chip.classList.contains('dragging')).toBe(false);
    expect(s.target.classList.contains('drop')).toBe(false);
    expect(must(s.container, '.wm-planner').className).toBe('wm-planner');
    expect(s.api.current?.isActive()).toBe(false);
    expect(s.api.current?.clickSuppressed()).toBe(true);
  });

  it('the click suppression lasts 50 ms', () => {
    const t0 = Date.now();
    const now = vi.spyOn(Date, 'now').mockReturnValue(t0);
    try {
      const s = setup();
      pointer('pointerdown', s.chip, 100, 100);
      over = s.target;
      pointer('pointermove', document, 140, 100);
      pointer('pointerup', document, 140, 100);
      now.mockReturnValue(t0 + CLICK_SUPPRESS_MS - 1);
      expect(s.api.current?.clickSuppressed()).toBe(true);
      now.mockReturnValue(t0 + CLICK_SUPPRESS_MS);
      expect(s.api.current?.clickSuppressed()).toBe(false);
    } finally {
      now.mockRestore();
    }
  });

  it('a drop back on the WO own day is no move and is never outlined', () => {
    const s = setup();
    pointer('pointerdown', s.chip, 100, 100);
    over = s.home;
    pointer('pointermove', document, 100, 120);
    expect(s.home.classList.contains('drop')).toBe(false);
    pointer('pointerup', document, 100, 120);
    expect(s.onDrop).not.toHaveBeenCalled();
  });

  it('a chip that cannot move is refused at the threshold and never ghosts', () => {
    const s = setup();
    pointer('pointerdown', must(s.container, '[data-wo="102"]'), 100, 100);
    over = s.target;
    pointer('pointermove', document, 140, 100);
    expect(s.onRefuse).toHaveBeenCalledWith(LOCKED);
    expect(s.container.querySelector('.ghost')).toBeNull();
    pointer('pointerup', document, 140, 100);
    expect(s.onDrop).not.toHaveBeenCalled();
  });

  it('cancel() (Esc) mid-drag ends it with nothing dropped', () => {
    const s = setup();
    pointer('pointerdown', s.chip, 100, 100);
    over = s.target;
    pointer('pointermove', document, 140, 100);
    act(() => {
      s.api.current?.cancel();
    });
    expect(s.container.querySelector('.ghost')).toBeNull();
    expect(s.target.classList.contains('drop')).toBe(false);
    pointer('pointerup', document, 140, 100);
    expect(s.onDrop).not.toHaveBeenCalled();
  });

  it('pointercancel ends the drag too', () => {
    const s = setup();
    pointer('pointerdown', s.chip, 100, 100);
    over = s.target;
    pointer('pointermove', document, 140, 100);
    pointer('pointercancel', document, 140, 100);
    expect(s.container.querySelector('.ghost')).toBeNull();
    pointer('pointerup', document, 140, 100);
    expect(s.onDrop).not.toHaveBeenCalled();
  });

  it('another pointer, the hours badge or a right button never drive the drag', () => {
    const s = setup();
    pointer('pointerdown', must(s.container, '.hrs'), 100, 100);
    pointer('pointerdown', s.chip, 100, 100, 1, 2);
    expect(s.api.current?.isActive()).toBe(false);
    pointer('pointerdown', s.chip, 100, 100, 7);
    over = s.target;
    pointer('pointermove', document, 140, 100, 8);
    expect(s.container.querySelector('.ghost')).toBeNull();
    pointer('pointerup', document, 140, 100, 7);
    expect(s.onDrop).not.toHaveBeenCalled();
  });

  it('disabled (RO, OD-107): a press does nothing at all', () => {
    const s = setup(false);
    pointer('pointerdown', s.chip, 100, 100);
    over = s.target;
    pointer('pointermove', document, 140, 100);
    pointer('pointerup', document, 140, 100);
    expect(s.api.current?.isActive()).toBe(false);
    expect(s.container.querySelector('.ghost')).toBeNull();
    expect(s.onDrop).not.toHaveBeenCalled();
    expect(s.onRefuse).not.toHaveBeenCalled();
  });
});
