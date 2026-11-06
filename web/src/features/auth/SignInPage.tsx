/**
 * Azztec_SaaS_web_auth_SignInPage_v1_0_0.tsx  ->  web/src/features/auth/SignInPage.tsx
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6 . OD-96, OD-98, traps 1 and 6
 *
 * User name, password, one message line, one button. Props-driven and router-free (the PlannerView
 * precedent): routes/signin.tsx stores the session and navigates; the test passes a spy.
 *
 * The message line shows what session.signIn returns - the server's own words for a refusal, so an
 * unknown login and a wrong password read the same (trap 6). After any failure the password field
 * empties and the user name stays. The password is sent exactly as typed; only the user name is checked
 * for being blank (trap 1: a password may be spaces).
 *
 * Changelog:
 *   1.0.0  Initial DP2b.
 */
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';

import { AZZTEC_LOGO_URI } from '../shell/icons';
import { MESSAGES } from './rules';
import { signIn } from './session';
import type { SessionInfo } from '../../api/client';

import './auth.css';

export const VERSION = '1.0.0';

export type SignInPageProps = {
  /** a session came back; the route remembers it and navigates to ?next= */
  onSignedIn: (session: SessionInfo) => void;
};

export function SignInPage({ onSignedIn }: SignInPageProps) {
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const loginRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loginRef.current?.focus();
  }, []);

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (busy) return;
    if (login.trim() === '' || password === '') {
      setMessage(MESSAGES.MISSING);
      return;
    }
    setBusy(true);
    setMessage('');
    const result = await signIn(login, password);
    setBusy(false);
    if (result.ok) {
      onSignedIn(result.session);
      return;
    }
    setPassword('');
    setMessage(result.message);
  };

  return (
    <div className="wm-signin" data-name="SignInPage">
      <form className="card" noValidate onSubmit={(e) => void submit(e)}>
        <div className="brand">
          <img alt="" height={40} src={AZZTEC_LOGO_URI} width={40} />
          <span className="wordmark">Azztec</span>
        </div>
        <h1>Sign in</h1>
        <p className="hint">Use your Workmate user name and password.</p>
        <label className="field">
          <span>User name</span>
          <input
            autoCapitalize="none"
            autoComplete="username"
            maxLength={100}
            name="login"
            onChange={(e) => setLogin(e.target.value)}
            ref={loginRef}
            spellCheck={false}
            type="text"
            value={login}
          />
        </label>
        <label className="field">
          <span>Password</span>
          <input
            autoComplete="current-password"
            maxLength={200}
            name="password"
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            value={password}
          />
        </label>
        <p className="msg" data-name="signinMessage" role="alert">
          {message}
        </p>
        <button disabled={busy} type="submit">
          {busy ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}
