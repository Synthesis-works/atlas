/**
 * AgentLanding — the public front page.
 *
 * Two jobs: the call-to-action must point at the right place for the visitor's
 * session, and the hard limits quoted on the page must match the ones the agent
 * actually enforces (apps/backend/agent/state.py), so the page can't quietly
 * start lying when a limit changes.
 */

/// <reference types="node" />

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import AgentLanding from '../AgentLanding';

function tokenExpiringIn(seconds: number): string {
  const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds }));
  return ['header', payload, 'signature'].join('.');
}

function renderLanding() {
  return render(
    <MemoryRouter>
      <AgentLanding />
    </MemoryRouter>,
  );
}

// The agent's hard limits, read as text from the backend source. Null when the landing app is
// checked out without the backend, and the drift check below is skipped in that case.
function readAgentSource(file: string): string | null {
  try {
    return readFileSync(resolve(import.meta.dirname, '../../../../backend/agent', file), 'utf8');
  } catch {
    return null;
  }
}
const agentStateSource = readAgentSource('state.py'); // where the limits are declared
const agentLoopSource = readAgentSource('agent.py'); // where they are enforced

function limit(source: string, name: string): number {
  const match = source.match(new RegExp(`^${name}\\s*=\\s*(\\d+)`, 'm'));
  if (!match) throw new Error(`${name} not found in agent state.py`);
  return Number(match[1]);
}

const NUMBER_WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];

// Every limit the page quotes, and the wording it quotes it in.
// MAX_MODELS_PER_RUN is declared in state.py but nothing enforces it, so the page must not quote it.
const QUOTED_LIMITS: ReadonlyArray<{ name: string; phrases: (value: number) => string[] }> = [
  { name: 'MAX_STEPS', phrases: (n) => [`${n} steps`] },
  { name: 'MAX_TOOL_CALLS', phrases: (n) => [`${n} tool calls`] },
  {
    name: 'MAX_REPAIR_ATTEMPTS',
    phrases: (n) => [`${n} repair attempts`, `retried up to ${NUMBER_WORDS[n]} times`],
  },
  { name: 'MAX_EXECUTION_TIME', phrases: (n) => [`${n / 60} minutes`] },
  { name: 'MAX_CLARIFICATION_ROUNDS', phrases: (n) => [`up to ${NUMBER_WORDS[n]} rounds`] },
];

/** "once", "twice", "three times": how the page words a count of attempts. */
function times(n: number): string {
  if (n === 1) return 'once';
  if (n === 2) return 'twice';
  return `${NUMBER_WORDS[n]} times`;
}

/** How many times `name` appears in `source`. */
function mentions(source: string, name: string): number {
  return source.split(name).length - 1;
}

describe('AgentLanding', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined); // jsdom doesn't implement it
  });
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('leads with the question the product answers', () => {
    renderLanding();
    expect(screen.getByRole('heading', { level: 1 }).textContent).toMatch(
      /which of these models can actually do my job/i,
    );
  });

  it('sends a signed-out visitor to /login', () => {
    renderLanding();
    const ctas = screen.getAllByRole('link', { name: 'Try the agent' });
    expect(ctas.length).toBeGreaterThan(0);
    for (const link of ctas) expect(link.getAttribute('href')).toBe('/login');
    expect(screen.queryByRole('link', { name: 'Open the agent' })).toBeNull();
  });

  it('sends a signed-in visitor straight to the agent', () => {
    localStorage.setItem('atlas_token', tokenExpiringIn(3600));
    renderLanding();
    const ctas = screen.getAllByRole('link', { name: 'Open the agent' });
    expect(ctas.length).toBeGreaterThan(0);
    for (const link of ctas) expect(link.getAttribute('href')).toBe('/dashboard/agent');
    expect(screen.queryByRole('link', { name: 'Sign in' })).toBeNull();
  });

  it('treats an expired token as signed out', () => {
    localStorage.setItem('atlas_token', tokenExpiringIn(-60));
    renderLanding();
    expect(screen.getAllByRole('link', { name: 'Try the agent' }).length).toBeGreaterThan(0);
  });

  it('links the CLI guide and the parent site to Synthesis Works', () => {
    renderLanding();

    // Absolute, not a route on this app: the marketing site is a separate origin.
    const install = new URL(screen.getByRole('link', { name: 'Install the CLI' }).getAttribute('href') ?? '');
    expect(install.pathname).toBe('/cli/install');

    const parent = screen.getByRole('link', { name: 'Synthesis Works' });
    expect(parent.getAttribute('href')).toBe(install.origin);
  });

  it('keeps unbuilt ideas out of the feature list', () => {
    renderLanding();
    const features = document.getElementById('does');
    const upcoming = document.getElementById('next');
    expect(features?.textContent).not.toMatch(/private test sets|watches the agent/i);
    expect(upcoming?.textContent).toMatch(/none of this exists yet/i);
  });

  it.skipIf(!agentStateSource || !agentLoopSource)(
    'quotes the same hard limits the agent enforces',
    () => {
      renderLanding();
      const text = document.getElementById('does')?.textContent ?? '';
      const state = agentStateSource as string;
      const loop = agentLoopSource as string;

      for (const { name, phrases } of QUOTED_LIMITS) {
        for (const phrase of phrases(limit(state, name))) expect(text).toContain(phrase);
        // A constant that is only declared is not a limit: the loop has to use it (the import
        // is one mention, so enforcing it means at least two).
        expect(mentions(loop, name), `${name} is not enforced in agent.py`).toBeGreaterThan(1);
      }

      // The numbers in "How a task runs" are worded differently, so check them on their own.
      const how = document.getElementById('how')?.textContent ?? '';
      expect(how).toContain(`up to ${times(limit(state, 'MAX_REPAIR_ATTEMPTS'))}`);
      expect(how).toContain(`at most ${times(limit(state, 'MAX_CLARIFICATION_ROUNDS'))}`);

      // The hero's plan sheet quotes the same limits in short form.
      const sheet = document.querySelector('.al-title__limits')?.textContent ?? '';
      expect(sheet).toContain(`${limit(state, 'MAX_STEPS')} steps`);
      expect(sheet).toContain(`${limit(state, 'MAX_TOOL_CALLS')} tool calls`);
      expect(sheet).toContain(`${limit(state, 'MAX_REPAIR_ATTEMPTS')} repairs`);
      expect(sheet).toContain(`${limit(state, 'MAX_EXECUTION_TIME') / 60} minutes`);
    },
  );
});
