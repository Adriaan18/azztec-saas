/**
 * Azztec_SaaS_web_auth_NoAccess_v1_0_0.tsx  ->  web/src/features/auth/NoAccess.tsx
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6 . OD-100
 *
 * What the main cell shows instead of a page whose right is NA. routes/__root.tsx decides; the page
 * never mounts, so it never asks the API for something the API would refuse with a 403 anyway.
 *
 * At RST nobody who can sign in has NA on the Planner or WO Maint - NA means no security group, and a
 * person with no group is refused at sign-in (OD-98 rule 5). The page exists for the client whose
 * groups say otherwise.
 *
 * Changelog:
 *   1.0.0  Initial DP2b.
 */
import { PAGE_LABEL } from './rules';
import type { Page } from './rules';

import './auth.css';

export const VERSION = '1.0.0';

export type NoAccessProps = {
  page: Page;
};

export function NoAccess({ page }: NoAccessProps) {
  return (
    <div className="wm-noaccess" data-name="NoAccess">
      <h1>No access</h1>
      <p>{`Your Workmate rights do not include ${PAGE_LABEL[page]}.`}</p>
      <p>Ask your Workmate administrator if you need it.</p>
    </div>
  );
}
