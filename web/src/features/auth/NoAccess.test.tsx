/**
 * Azztec_SaaS_web_auth_NoAccess_test_v1_0_0.tsx  ->  web/src/features/auth/NoAccess.test.tsx
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6 . OD-100 . pair of NoAccess.tsx 1.0.0
 *
 * Zero network: a props-only component. Explicit cleanup(), no globals (Landmines s.C).
 *
 * Changelog:
 *   1.0.0  Initial DP2b. 3 cases.
 */
import { cleanup, render } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { NoAccess, VERSION } from './NoAccess';

export const TEST_VERSION = '1.0.0';

afterEach(() => {
  cleanup();
});

/** the heading and the two lines, in order */
function lines(root: HTMLElement) {
  const page = root.querySelector('[data-name="NoAccess"]');
  if (!page) throw new Error('no NoAccess');
  return Array.from(page.querySelectorAll('h1, p')).map((e) => e.textContent);
}

describe('NoAccess - what the main cell shows for an NA page (OD-100)', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.0.0');
  });

  it('the Planner: names the page and points at the administrator', () => {
    const { container } = render(<NoAccess page="planner" />);
    expect(lines(container)).toEqual([
      'No access',
      'Your Workmate rights do not include the Planner.',
      'Ask your Workmate administrator if you need it.',
    ]);
  });

  it('WO Maint', () => {
    const { container } = render(<NoAccess page="womaint" />);
    expect(lines(container)).toEqual([
      'No access',
      'Your Workmate rights do not include WO Maint.',
      'Ask your Workmate administrator if you need it.',
    ]);
  });
});
