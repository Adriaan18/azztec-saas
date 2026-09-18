/**
 * Azztec_SaaS_web_shell_AppShell_test_v1_0_0.tsx  ->  web/src/features/shell/AppShell.test.tsx
 * Version:  1.0.0   Date: 2026-09-16   Author: Adriaan
 * Spec:     Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md s5 . pair of AppShell.tsx 1.0.0
 *
 * Zero network. jsdom has no Fullscreen API and window.print only logs "not implemented", so both are
 * stubbed on the test document / window (spec s4 trap 4). The clock runs on fake timers with the system
 * time set through the LOCAL constructor - never an ISO string, which is UTC midnight (Landmines s.C).
 *
 * Changelog:
 *   1.0.0  Initial S1k. 6 cases.
 */
import { act, cleanup, fireEvent, render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AppShell, VERSION } from './AppShell';

export const TEST_VERSION = '1.0.0';

function must(root: HTMLElement, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

/** the Fullscreen API, absent in jsdom: a settable fullscreenElement and two resolving methods */
const requestFullscreen = vi.fn(() => Promise.resolve());
const exitFullscreen = vi.fn(() => Promise.resolve());
let fsElement: Element | null = null;

beforeEach(() => {
  fsElement = null;
  requestFullscreen.mockClear();
  exitFullscreen.mockClear();
  Object.defineProperty(document, 'fullscreenElement', { configurable: true, get: () => fsElement });
  Object.defineProperty(document.documentElement, 'requestFullscreen', { configurable: true, value: requestFullscreen });
  Object.defineProperty(document, 'exitFullscreen', { configurable: true, value: exitFullscreen });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('AppShell - header + rail around the page', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.0.0');
  });

  it('draws the header, the rail and the page in the main cell', () => {
    const { container } = render(
      <AppShell pathname="/" onPlannex={vi.fn()}>
        <p data-name="page">hello</p>
      </AppShell>,
    );
    const shell = must(container, '.wm-shell');
    expect(Array.from(shell.children).map((e) => e.className)).toEqual(['wm-hdr', 'wm-rail', 'wm-shell-main']);
    expect(must(shell, 'main.wm-shell-main [data-name="page"]').textContent).toBe('hello');
    expect(must(shell, '[data-name="BtnPlannex"]').getAttribute('data-active')).toBe('0');
  });

  it('/planner lights Plannex in the header and nothing on the rail; a click on Plannex reaches onPlannex', () => {
    const onPlannex = vi.fn();
    const { container } = render(
      <AppShell pathname="/planner" onPlannex={onPlannex}>
        <span />
      </AppShell>,
    );
    expect(must(container, '[data-name="BtnPlannex"]').getAttribute('data-active')).toBe('1');
    expect(container.querySelectorAll('.wm-rail .item[data-active="1"]').length).toBe(0);
    fireEvent.click(must(container, '[data-name="BtnPlannex"]'));
    expect(onPlannex).toHaveBeenCalledTimes(1);
  });

  it('the clock shows the local date and time, ticks once a second, and clears its timer on unmount', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 16, 13, 8, 6));
    const { container, unmount } = render(
      <AppShell pathname="/" onPlannex={vi.fn()}>
        <span />
      </AppShell>,
    );
    expect(must(container, '[data-name="dateLabel"]').textContent).toBe('Sep 16');
    expect(must(container, '[data-name="timeLabel"]').textContent).toBe('13:08:06');
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(must(container, '[data-name="timeLabel"]').textContent).toBe('13:08:07');
    act(() => {
      vi.advanceTimersByTime(53_000);
    });
    expect(must(container, '[data-name="timeLabel"]').textContent).toBe('13:09:00');
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('Print calls window.print on every page this build has (the dispatcher falls through to the browser)', () => {
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    const { container } = render(
      <AppShell pathname="/planner" onPlannex={vi.fn()}>
        <span />
      </AppShell>,
    );
    fireEvent.click(must(container, '[data-name="MenuItem_Print"]'));
    expect(print).toHaveBeenCalledTimes(1);
  });

  it('fullscreen enters when nothing is fullscreen and exits when something is', () => {
    const { container } = render(
      <AppShell pathname="/" onPlannex={vi.fn()}>
        <span />
      </AppShell>,
    );
    const fs = must(container, '[data-name="fsBtn"]');
    fireEvent.click(fs);
    expect(requestFullscreen).toHaveBeenCalledTimes(1);
    expect(exitFullscreen).not.toHaveBeenCalled();
    fsElement = document.documentElement;
    fireEvent.click(fs);
    expect(exitFullscreen).toHaveBeenCalledTimes(1);
    expect(requestFullscreen).toHaveBeenCalledTimes(1);
  });
});
