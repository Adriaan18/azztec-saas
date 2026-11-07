/**
 * Azztec_SaaS_web_planner_useWoDrag_v1_0_0.ts  ->  web/src/features/planner/useWoDrag.ts
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (useWoDrag.ts row), §7 · OD-106, OD-107
 * Oracle:   Planner_v1_8_1.html onPointerDown, onPointerMove, onPointerUp, endDrag (the WO branch; the
 *           worker branch is S4), wire (pointerdown on the grid wrap, move / up / cancel on the document)
 *
 * The oracle's pointer drag, as a controller plus a thin hook (OD-106 - no drag library). The DOM
 * contract is the one S1f/S1g already render: `.chip[data-wo]`, `.cell[data-date]`, `touch-action:none`
 * on the chip. Everything the drag paints is imperative and outside React's reconciliation: the
 * ghost is a clone of the painted chip in a layer div React renders empty (so the S1i badge colour
 * comes with it, and the scoped `.wm-planner` rules reach it); `.dragging` on the chip and `.drop` on
 * the target cell are class toggles on elements React does not re-class mid-drag. The only React
 * state is `dragging`, which the view needs for the root class and the poll pause.
 *
 * As the oracle: 6 px before a drag starts; a chip that is not movable is refused at that point
 * (onRefuse - the view toasts whyNotMovable) and never ghosts; the target is elementFromPoint ->
 * the nearest `[data-date]`, outlined unless it is the WO's own day; a drop on another day calls
 * onDrop; the click that follows a drop is swallowed for 50 ms; pointercancel and cancel() (Esc) end
 * the drag with nothing dropped. Not the oracle: `enabled` false (RO, OD-107) makes a pointerdown do
 * nothing at all, and the click suppression is a timestamp rather than a timer.
 *
 * jsdom has neither elementFromPoint nor setPointerCapture (spec §7): both are called inside try,
 * and the test stubs the first.
 *
 * Changelog:
 *   1.0.0  Initial DP3b.
 */
import { useEffect, useRef, useState } from 'react';

import type { Wo } from '../../api/client/types.gen';

export const VERSION = '1.0.0';

/** Oracle onPointerMove: |dx| and |dy| both under 6 px is still a click. */
export const DRAG_THRESHOLD_PX = 6;
/** Oracle onPointerUp: the click after a drop is ignored for 50 ms. */
export const CLICK_SUPPRESS_MS = 50;
/** Oracle onPointerDown: a press on these never starts a drag (.cap is the rail's, S4). */
export const NO_DRAG_SELECTOR = '.hrs, input, select, button';

/** What the controller reads from a pointer event - a React PointerEvent and a DOM one both fit. */
export type PointerLike = {
  button: number;
  clientX: number;
  clientY: number;
  pointerId: number;
  target: EventTarget | null;
};

export type WoDragOptions = {
  /** OD-107: false at RO - a pointerdown does nothing */
  enabled: boolean;
  /** the WO a chip's data-wo names, from the data on screen */
  woById: (id: number) => Wo | undefined;
  /** dragged past the threshold but not movable - the view toasts whyNotMovable */
  onRefuse: (wo: Wo) => void;
  /** dropped on a day other than the WO's own */
  onDrop: (wo: Wo, toIso: string) => void;
};

export type WoDragHost = WoDragOptions & {
  /** the layer the ghost goes into (inside .wm-planner); null = no ghost */
  layer: () => HTMLElement | null;
  /** true when a drag has started (past the threshold), false when it ends */
  onDragging: (on: boolean) => void;
};

export type WoDrag = {
  down: (ev: PointerLike) => void;
  cancel: () => void;
  isActive: () => boolean;
  clickSuppressed: () => boolean;
  configure: (host: WoDragHost) => void;
};

type Live = {
  wo: Wo;
  chip: HTMLElement;
  pointerId: number;
  startX: number;
  startY: number;
  offX: number;
  offY: number;
  moved: boolean;
  ghost: HTMLElement | null;
  cell: HTMLElement | null;
  target: string;
  /** aborting it removes the three document listeners */
  listening: AbortController;
};

/** Oracle: the drag starts when either axis has moved 6 px. */
export function pastThreshold(dx: number, dy: number): boolean {
  return Math.abs(dx) >= DRAG_THRESHOLD_PX || Math.abs(dy) >= DRAG_THRESHOLD_PX;
}

/** The chip a press starts a drag on, or null - nothing inside the hours badge, a control or a button. */
export function chipFor(target: EventTarget | null): HTMLElement | null {
  if (!(target instanceof Element) || target.closest(NO_DRAG_SELECTOR)) return null;
  const chip = target.closest('.chip');
  return chip instanceof HTMLElement ? chip : null;
}

/** The day cell an element sits in (oracle: closest('[data-date]')), or null. */
export function dayCellOf(el: Element | null): HTMLElement | null {
  const cell = el ? el.closest('[data-date]') : null;
  return cell instanceof HTMLElement ? cell : null;
}

/** The ghost keeps the chip's look minus the selection and the drag fade, plus `.ghost`. */
export function ghostClass(chipClass: string): string {
  return chipClass
    .split(/\s+/)
    .filter((c) => c !== '' && c !== 'sel' && c !== 'dragging')
    .concat('ghost')
    .join(' ');
}

function elementAt(x: number, y: number): Element | null {
  try {
    return document.elementFromPoint(x, y);
  } catch {
    return null;
  }
}

export function createWoDrag(initial: WoDragHost): WoDrag {
  let host = initial;
  let live: Live | null = null;
  let suppressUntil = 0;

  /** Ends any drag: the document listeners go with the drag's AbortController, the paint is undone. */
  function end(): void {
    const d = live;
    if (!d) return;
    live = null;
    d.listening.abort();
    d.ghost?.remove();
    d.chip.classList.remove('dragging');
    d.cell?.classList.remove('drop');
    if (d.moved) host.onDragging(false);
  }

  /** Past the threshold: refuse a chip that cannot move, otherwise ghost it. False when refused. */
  function begin(d: Live, pointerId: number): boolean {
    if (!d.wo.movable) {
      end();
      host.onRefuse(d.wo);
      return false;
    }
    d.moved = true;
    const r = d.chip.getBoundingClientRect();
    d.offX = d.startX - r.left;
    d.offY = d.startY - r.top;
    const layer = host.layer();
    if (layer) {
      const g = d.chip.cloneNode(true) as HTMLElement;
      g.className = ghostClass(d.chip.className);
      g.removeAttribute('data-wo');
      g.removeAttribute('data-movable');
      g.removeAttribute('title');
      g.style.width = `${r.width}px`;
      layer.appendChild(g);
      d.ghost = g;
    }
    d.chip.classList.add('dragging');
    host.onDragging(true);
    try {
      d.chip.setPointerCapture(pointerId);
    } catch {
      // jsdom has no pointer capture; the document listeners still see every event
    }
    return true;
  }

  function onMove(ev: PointerEvent): void {
    const d = live;
    if (!d || ev.pointerId !== d.pointerId) return;
    if (!d.moved) {
      if (!pastThreshold(ev.clientX - d.startX, ev.clientY - d.startY)) return;
      if (!begin(d, ev.pointerId)) return;
    }
    if (d.ghost) {
      d.ghost.style.left = `${ev.clientX - d.offX}px`;
      d.ghost.style.top = `${ev.clientY - d.offY}px`;
    }
    const cell = dayCellOf(elementAt(ev.clientX, ev.clientY));
    if (cell !== d.cell) {
      d.cell?.classList.remove('drop');
      d.cell = cell;
      d.target = cell ? (cell.getAttribute('data-date') ?? '') : '';
      if (cell && d.target !== d.wo.start) cell.classList.add('drop');
    }
    ev.preventDefault();
  }

  function onUp(ev: PointerEvent): void {
    const d = live;
    if (!d || ev.pointerId !== d.pointerId) return;
    const { moved, wo, target } = d;
    end();
    if (!moved) return;
    suppressUntil = Date.now() + CLICK_SUPPRESS_MS;
    if (target && target !== wo.start) host.onDrop(wo, target);
  }

  function down(ev: PointerLike): void {
    if (!host.enabled || live || ev.button !== 0) return;
    const chip = chipFor(ev.target);
    if (!chip) return;
    const wo = host.woById(Number(chip.getAttribute('data-wo')));
    if (!wo) return;
    const listening = new AbortController();
    live = {
      wo,
      chip,
      pointerId: ev.pointerId,
      startX: ev.clientX,
      startY: ev.clientY,
      offX: 0,
      offY: 0,
      moved: false,
      ghost: null,
      cell: null,
      target: '',
      listening,
    };
    document.addEventListener('pointermove', onMove, { signal: listening.signal });
    document.addEventListener('pointerup', onUp, { signal: listening.signal });
    document.addEventListener('pointercancel', end, { signal: listening.signal });
  }

  return {
    down,
    cancel: end,
    isActive: () => live !== null,
    clickSuppressed: () => Date.now() < suppressUntil,
    configure: (next) => {
      host = next;
    },
  };
}

/**
 * The hook PlannerView uses: put onPointerDown on the grid wrap and layerRef on an empty div inside
 * .wm-planner. `dragging` is true from the 6 px mark to the end of the drag.
 */
export function useWoDrag(opts: WoDragOptions) {
  const layerRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);
  const [ctl] = useState(() => createWoDrag({ ...opts, layer: () => layerRef.current, onDragging: setDragging }));

  // The controller's listeners outlive a render, so they read the latest options through configure().
  useEffect(() => {
    ctl.configure({ ...opts, layer: () => layerRef.current, onDragging: setDragging });
  });

  // An unmount mid-drag takes the ghost and the document listeners with it.
  useEffect(
    () => () => {
      ctl.cancel();
    },
    [ctl],
  );

  return {
    layerRef,
    dragging,
    onPointerDown: ctl.down,
    cancel: ctl.cancel,
    isActive: ctl.isActive,
    clickSuppressed: ctl.clickSuppressed,
  };
}
