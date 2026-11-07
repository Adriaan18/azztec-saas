/**
 * Azztec_SaaS_web_planner_Toast_v1_0_0.tsx  ->  web/src/features/planner/Toast.tsx
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (Toast.tsx row) · OD-54, OD-113
 * Oracle:   Planner_v1_8_1.html toast(), the #toast markup (message, Undo button, the Ctrl+Z hint),
 *           wire (toastUndo hides the toast, then undoLast)
 *
 * The oracle's toast: one line, an Undo button and the `Ctrl+Z` hint when the line is undoable, gone
 * after 4 s - 6.5 s with Undo. Always rendered, like the oracle's element, so `.on` is the only
 * thing that changes and screen readers hear it through role=status. Absolute inside .wm-planner, not
 * fixed to the viewport (OD-54 - the shell's header and rail are not the planner's).
 *
 * useToast owns the one timer: a new toast replaces the old one and restarts it; unmount clears it.
 *
 * Changelog:
 *   1.0.0  Initial DP3b.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { TOAST_MS, UNDO_TOAST_MS } from './moves';

export const VERSION = '1.0.0';

export type ToastState = {
  msg: string;
  /** shows the Undo button and the Ctrl+Z hint, and stays 6.5 s */
  undo: boolean;
};

export function useToast() {
  const [toast, setToast] = useState<ToastState | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const hide = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    setToast(null);
  }, []);

  const show = useCallback((msg: string, undo = false) => {
    if (timer.current) clearTimeout(timer.current);
    setToast({ msg, undo });
    timer.current = setTimeout(
      () => {
        timer.current = null;
        setToast(null);
      },
      undo ? UNDO_TOAST_MS : TOAST_MS,
    );
  }, []);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  return { toast, show, hide };
}

export type ToastProps = {
  toast: ToastState | null;
  /** the toast's Undo: the view hides the toast and undoes the last move */
  onUndo: () => void;
};

export function Toast({ toast, onUndo }: ToastProps) {
  return (
    <div className={toast ? 'toast on' : 'toast'} role="status" aria-live="polite">
      <span className="msg">{toast ? toast.msg : ''}</span>
      {toast?.undo ? (
        <button type="button" onClick={onUndo}>
          Undo
        </button>
      ) : null}
      <span className="k">{toast?.undo ? 'Ctrl+Z' : ''}</span>
    </div>
  );
}

export default Toast;
