/**
 * Azztec_SaaS_web_planner_Toast_test_v1_0_0.tsx  ->  web/src/features/planner/Toast.test.tsx
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (Toast.test.tsx row) · pair of Toast.tsx 1.0.0
 *
 * The toast as markup (always rendered, `.on` when it says something, Undo and the Ctrl+Z hint only
 * when undoable) and useToast's one timer under fake timers: 4 s, 6.5 s with Undo, a new toast restarts
 * the clock, hide() is immediate. Fake timers are this file's only global, restored in afterEach.
 *
 * Changelog:
 *   1.0.0  Initial DP3b.
 */
import { act, cleanup, fireEvent, render, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { TOAST_MS, UNDO_TOAST_MS } from './moves';
import { Toast, VERSION, useToast } from './Toast';

export const TEST_VERSION = '1.0.0';

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

function must(root: ParentNode, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

describe('Toast - the markup', () => {
  it('carries its version; with nothing to say it is there but off', () => {
    expect(VERSION).toBe('1.0.0');
    const { container } = render(<Toast toast={null} onUndo={vi.fn()} />);
    expect(must(container, '.toast').className).toBe('toast');
    expect(must(container, '.toast').getAttribute('role')).toBe('status');
    expect(container.querySelector('.toast button')).toBeNull();
  });

  it('a plain toast: the line, no Undo, no hint', () => {
    const { container } = render(
      <Toast toast={{ msg: 'WO-104 is closed - it does not move', undo: false }} onUndo={vi.fn()} />,
    );
    expect(must(container, '.toast').className).toBe('toast on');
    expect(must(container, '.toast .msg').textContent).toBe('WO-104 is closed - it does not move');
    expect(container.querySelector('.toast button')).toBeNull();
    expect(must(container, '.toast .k').textContent).toBe('');
  });

  it('an undoable toast has Undo and the Ctrl+Z hint; Undo calls onUndo', () => {
    const onUndo = vi.fn();
    const { container } = render(<Toast toast={{ msg: 'Moved WO-101', undo: true }} onUndo={onUndo} />);
    expect(must(container, '.toast .k').textContent).toBe('Ctrl+Z');
    fireEvent.click(must(container, '.toast button'));
    expect(onUndo).toHaveBeenCalledTimes(1);
  });
});

describe('Toast - useToast, the one timer', () => {
  it('a plain toast goes after 4 s', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.show('hello');
    });
    expect(result.current.toast).toEqual({ msg: 'hello', undo: false });
    act(() => {
      vi.advanceTimersByTime(TOAST_MS - 1);
    });
    expect(result.current.toast).not.toBeNull();
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current.toast).toBeNull();
  });

  it('an Undo toast stays 6.5 s', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.show('Moved WO-101', true);
    });
    act(() => {
      vi.advanceTimersByTime(TOAST_MS + 1);
    });
    expect(result.current.toast).toEqual({ msg: 'Moved WO-101', undo: true });
    act(() => {
      vi.advanceTimersByTime(UNDO_TOAST_MS - TOAST_MS);
    });
    expect(result.current.toast).toBeNull();
  });

  it('a new toast replaces the old one and restarts the clock; hide() is immediate', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.show('first');
    });
    act(() => {
      vi.advanceTimersByTime(TOAST_MS - 100);
    });
    act(() => {
      result.current.show('second');
    });
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(result.current.toast?.msg).toBe('second');
    act(() => {
      result.current.hide();
    });
    expect(result.current.toast).toBeNull();
  });
});
