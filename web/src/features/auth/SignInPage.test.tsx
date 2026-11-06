/**
 * Azztec_SaaS_web_auth_SignInPage_test_v1_0_0.tsx  ->  web/src/features/auth/SignInPage.test.tsx
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6 . OD-96, OD-98, traps 1 and 6 .
 *           pair of SignInPage.tsx 1.0.0
 *
 * Router-free, like the page: onSignedIn is a spy. fetch is stubbed for the whole file and answers 200
 * with the administrator's session unless a case queues a one-off reply. The generated client awaits
 * before it calls fetch, so every case that expects a request waits for the stub to have been called -
 * a one-off reply is always used by the case that queued it. The refusal bodies are DP2a's smoke output
 * (session.fixture.ts).
 *
 * Changelog:
 *   1.0.0  Initial DP2b. 8 cases.
 */
import { cleanup, fireEvent, render, waitFor } from '@testing-library/react';
import { afterAll, afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { client } from '../../api/client/client.gen';
import { SignInPage, VERSION } from './SignInPage';
import { MESSAGES } from './rules';
import { LOCKED_BODY, NO_GROUP_BODY, SIGNIN_FAILED_BODY, sessionFixture } from './session.fixture';

export const TEST_VERSION = '1.0.0';

const BASE = 'http://test.local';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

const fetchStub = vi.fn<(input: RequestInfo | URL) => Promise<Response>>(() =>
  Promise.resolve(jsonResponse(200, sessionFixture())),
);

vi.stubGlobal('fetch', fetchStub);
client.setConfig({ baseUrl: BASE });

function must(root: HTMLElement, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

function inputNamed(root: HTMLElement, name: string): HTMLInputElement {
  const el = root.querySelector(`input[name="${name}"]`);
  if (!(el instanceof HTMLInputElement)) throw new Error(`no input named ${name}`);
  return el;
}

/** the Request the generated client handed to fetch on call i */
function requestAt(i: number): Request {
  const input = fetchStub.mock.calls.at(i)?.[0];
  if (!(input instanceof Request)) throw new Error(`fetch call ${i} was not a Request`);
  return input;
}

/** a promise the case settles by hand */
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

function draw() {
  const onSignedIn = vi.fn();
  const r = render(<SignInPage onSignedIn={onSignedIn} />);
  const login = inputNamed(r.container, 'login');
  const password = inputNamed(r.container, 'password');
  const fill = (who: string, secret: string) => {
    fireEvent.change(login, { target: { value: who } });
    fireEvent.change(password, { target: { value: secret } });
  };
  return {
    ...r,
    onSignedIn,
    login,
    password,
    fill,
    form: must(r.container, 'form'),
    button: must(r.container, 'button[type="submit"]'),
    message: must(r.container, '[data-name="signinMessage"]'),
  };
}

beforeEach(() => {
  fetchStub.mockClear();
});

afterEach(() => {
  cleanup();
});

afterAll(() => {
  vi.unstubAllGlobals();
});

describe('SignInPage', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.0.0');
  });

  it('two fields a password manager understands, focus on the user name, an empty message line', () => {
    const { container, login, password, button, message } = draw();
    expect(must(container, '[data-name="SignInPage"] h1').textContent).toBe('Sign in');
    expect(login.type).toBe('text');
    expect(login.getAttribute('autocomplete')).toBe('username');
    expect(password.type).toBe('password');
    expect(password.getAttribute('autocomplete')).toBe('current-password');
    expect(document.activeElement).toBe(login);
    expect(message.getAttribute('role')).toBe('alert');
    expect(message.textContent).toBe('');
    expect(button.textContent).toBe('Sign in');
  });

  it('an empty form, a blank user name or no password: the MISSING line, and nothing is sent', () => {
    const { form, message, fill } = draw();
    fireEvent.submit(form);
    expect(message.textContent).toBe(MESSAGES.MISSING);
    fill('   ', 's3cret');
    fireEvent.submit(form);
    expect(message.textContent).toBe(MESSAGES.MISSING);
    fill('AZZ', '');
    fireEvent.submit(form);
    expect(message.textContent).toBe(MESSAGES.MISSING);
    expect(fetchStub).not.toHaveBeenCalled();
  });

  it('a session comes back: onSignedIn gets it, and the request carried exactly what was typed (trap 1)', async () => {
    const { form, fill, onSignedIn } = draw();
    fill(' AZZ ', ' s3cret ');
    fireEvent.submit(form);
    await waitFor(() => expect(onSignedIn).toHaveBeenCalledTimes(1));
    expect(onSignedIn).toHaveBeenCalledWith(sessionFixture());
    expect(new URL(requestAt(0).url).pathname).toBe('/api/v1/auth/signin');
    expect(JSON.parse(await requestAt(0).text())).toEqual({ login: ' AZZ ', password: ' s3cret ' });
  });

  it('401: the server line, the password emptied, the user name kept (trap 6)', async () => {
    fetchStub.mockImplementationOnce(() => Promise.resolve(jsonResponse(401, SIGNIN_FAILED_BODY)));
    const { form, fill, login, password, message, onSignedIn } = draw();
    fill('AZZ', 'wrong');
    fireEvent.submit(form);
    await waitFor(() => expect(message.textContent).toBe(SIGNIN_FAILED_BODY.message));
    expect(password.value).toBe('');
    expect(login.value).toBe('AZZ');
    expect(onSignedIn).not.toHaveBeenCalled();
  });

  it.each([
    ['403 no group', 403, NO_GROUP_BODY],
    ['423 locked', 423, LOCKED_BODY],
  ])('%s: the server line, word for word', async (_label, status, body) => {
    fetchStub.mockImplementationOnce(() => Promise.resolve(jsonResponse(status, body)));
    const { form, fill, message } = draw();
    fill('AZZ', 's3cret');
    fireEvent.submit(form);
    await waitFor(() => expect(message.textContent).toBe(body.message));
    expect(fetchStub).toHaveBeenCalledTimes(1);
  });

  it('busy: the button says so and is disabled, and a second submit sends nothing', async () => {
    const pending = deferred<Response>();
    fetchStub.mockImplementationOnce(() => pending.promise);
    const { form, fill, button, onSignedIn } = draw();
    fill('AZZ', 's3cret');
    fireEvent.submit(form);
    expect(button.textContent).toBe('Signing in...');
    expect(button.hasAttribute('disabled')).toBe(true);
    await waitFor(() => expect(fetchStub).toHaveBeenCalledTimes(1));
    fireEvent.submit(form);
    pending.resolve(jsonResponse(200, sessionFixture()));
    await waitFor(() => expect(onSignedIn).toHaveBeenCalledTimes(1));
    expect(button.textContent).toBe('Sign in');
    expect(button.hasAttribute('disabled')).toBe(false);
    expect(fetchStub).toHaveBeenCalledTimes(1);
  });
});
