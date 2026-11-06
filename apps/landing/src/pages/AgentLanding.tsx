/**
 * AgentLanding — the public front page for Atlas and the Atlas agent.
 *
 * Every claim on this page is checked against the code (agent limits, tools,
 * statuses, container hardening, CLI commands). Anything that is not built yet
 * lives in the dashed "Where this is going" section, not in the feature list.
 *
 * Styles are scoped under .al-root in AgentLanding.css.
 */

import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { getAuthToken } from '@/core/api/client';
import { isTokenExpired } from '@/features/auth/services/authService';
import './AgentLanding.css';

const INSTALL_COMMAND = 'pip install synthesis-atlas-cli';
// Straight quotes on purpose: people paste this into a shell, where curly quotes are not quotes.
const AGENT_COMMAND = 'atlas agent "List the available benchmarks"';

/**
 * The agent's hard limits, as enforced in apps/backend/agent/agent.py. Declared once so the hero
 * and the feature list can't disagree; the test compares them with the backend.
 */
const LIMITS = { steps: 25, toolCalls: 50, repairAttempts: 3, minutes: 10 } as const;

const GITHUB_URL = 'https://github.com/Synthesis-works/atlas';
const PYPI_URL = 'https://pypi.org/project/synthesis-atlas-cli/';

/* ------------------------------------------------------------------ */
/* Content                                                             */
/* ------------------------------------------------------------------ */

type PlanState = 'done' | 'input' | 'queued';

/** An illustrative plan. Labels match the status words the agent UI uses. */
const EXAMPLE_PLAN: ReadonlyArray<{ text: string; state: PlanState; label: string }> = [
  { text: 'Find or write a SQL benchmark', state: 'done', label: 'Done' },
  { text: 'Ask what queries may touch', state: 'input', label: 'Needs input' },
  { text: 'Check data against the schema', state: 'queued', label: 'Queued' },
  { text: 'Run 3 models on 40 prompts', state: 'queued', label: 'Queued' },
  { text: 'Score answers, write report', state: 'queued', label: 'Queued' },
];

const STEPS: ReadonlyArray<{ title: string; body: string; mark?: string }> = [
  {
    title: 'Describe the job',
    body: 'Write the goal in plain language and pick the model the agent should think with. “Compare these three models on writing safe SQL” is enough.',
  },
  {
    title: 'Answer its questions',
    body: 'If the goal is vague, the agent stops and asks instead of guessing. It asks at most twice, and your answers stay attached to the task.',
    mark: 'It stops and asks',
  },
  {
    title: 'Let it work',
    body: 'The agent writes its plan, finds or creates the datasets and benchmarks it needs, and starts the runs. If a step fails, it retries, up to three times.',
  },
  {
    title: 'Wait for the runs',
    body: 'Each run executes in its own container. The task is saved while it does, and picks up again when the run finishes, so you can close the tab.',
    mark: 'Saved while it waits',
  },
  {
    title: 'Read the report',
    body: 'The agent scores every response, compares the models and writes the report: accuracy, passed and failed counts, and a short summary. Reports have their own page.',
  },
];

const SPEC: ReadonlyArray<{ term: string; body: ReactNode }> = [
  {
    term: 'Writes a plan',
    body: 'The goal becomes numbered steps, and each step shows its status as the agent works through it.',
  },
  {
    term: 'Asks when it’s unsure',
    body: 'If the goal is vague, the agent stops and asks, for up to two rounds. Your answers stay attached to the task.',
  },
  {
    term: 'Uses real tools',
    body: 'It can search, read and create datasets and benchmarks, check a dataset against a benchmark, start runs and check on them, score the responses, compare models, and write the report.',
  },
  {
    term: 'Runs in isolation',
    body: 'Every run executes in its own container: non-root, read-only filesystem, extra capabilities dropped, limits on CPU, memory and processes. Each attempt is logged with its exit code and resource use.',
  },
  {
    term: 'Recovers from failures',
    body: 'A failed step is retried up to three times. If a model provider errors out, the agent switches to the next one in line.',
  },
  {
    term: 'Stops itself',
    body: `Hard limits per task: ${LIMITS.steps} steps, ${LIMITS.toolCalls} tool calls, ${LIMITS.repairAttempts} repair attempts and ${LIMITS.minutes} minutes of working time. At a limit it stops and tells you which one.`,
  },
  {
    term: 'Survives slow runs',
    body: 'A benchmark can take a minute or more. The task is saved while the run executes and resumes when it finishes, so you don’t have to keep the tab open.',
  },
  {
    term: 'Keeps your records',
    body: 'Tasks, plans and traces are saved to your account and visible only to you. Reports are shared with your organization. You can cancel a running task or run a finished one again.',
  },
  {
    term: 'Works from the terminal',
    body: (
      <>
        The same agent runs as <code className="al-inline">atlas agent</code> in your terminal. It’s
        a preview and may change.
      </>
    ),
  },
];

const PRINCIPLES: ReadonlyArray<{ title: string; body: string }> = [
  {
    title: 'Test the real task',
    body: 'A benchmark should look like the work you need done, not a quiz the model has already seen.',
  },
  {
    title: 'Show the work',
    body: 'A score without its plan, tool calls and results is just a claim. Atlas keeps all three with the task.',
  },
  {
    title: 'Don’t change the test underneath people',
    body: 'Datasets and benchmarks are versioned and immutable, so a result always names exactly what it was run against.',
  },
  {
    title: 'Stop when unsure',
    body: 'The agent asks when it can’t tell what you mean, and it halts itself at hard limits instead of looping.',
  },
  {
    title: 'No head starts',
    body: 'We won’t give any AI lab early access to the tests it will be graded on.',
  },
];

const NEXT: ReadonlyArray<{ title: string; body: string }> = [
  {
    title: 'Private test sets',
    body: 'Questions that never appear on the public internet. Results come back as a verdict and a hint, never the answer key.',
  },
  {
    title: 'Questions from the community',
    body: 'Anyone can submit one. The agent keeps it only if it actually trips models up, and the person who wrote it earns a share when it’s used.',
  },
  {
    title: 'An agent that watches the agent',
    body: 'A monitor that reads each run as it happens and flags a model that tries to reach outside its container.',
  },
  {
    title: 'Tests from your own chats',
    body: 'Paste a conversation where a model got it wrong and turn it into a repeatable test.',
  },
];

/* ------------------------------------------------------------------ */
/* Small pieces                                                        */
/* ------------------------------------------------------------------ */

function Mark() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="7.4" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M12 1.5v6.2M12 16.3v6.2M1.5 12h6.2M16.3 12h6.2"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="square"
      />
    </svg>
  );
}

/** A hand-drawn loop, like a checker circling something with a pencil. */
function Ring({ shape, tone }: { shape: 'wide' | 'round'; tone: 'hl' | 'red' }) {
  const wide = shape === 'wide';
  return (
    <svg
      className={`al-ring al-ring--${shape} al-ring--${tone}`}
      viewBox={wide ? '0 0 140 44' : '0 0 64 64'}
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        pathLength={1}
        d={
          wide
            ? 'M12 26 C 10 12, 40 4, 74 4 C 112 4, 136 11, 135 23 C 134 36, 104 41, 68 41 C 32 41, 7 35, 9 23 C 10 15, 28 9, 52 7'
            : 'M10 38 C 4 20, 18 6, 34 6 C 52 6, 60 22, 58 36 C 56 50, 42 59, 30 58 C 14 57, 5 44, 7 30 C 8 20, 16 12, 26 9'
        }
      />
    </svg>
  );
}

/** One shell command on a phone-width screen: wraps between words, never inside a hyphenated one. */
function Command({ text }: { text: string }) {
  return (
    <span>
      {text.split(' ').map((word, i) => (
        <Fragment key={i}>
          {i > 0 && ' '}
          {word.includes('-') ? <span className="al-nb">{word}</span> : word}
        </Fragment>
      ))}
    </span>
  );
}

function CopyCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard can be blocked; the command is still selectable with one click.
      setCopied(false);
    }
  };

  return (
    <div className="al-cmd">
      <code>{command}</code>
      <button type="button" onClick={copy} aria-label={`Copy command: ${command}`}>
        <span aria-live="polite">{copied ? 'Copied' : 'Copy'}</span>
      </button>
    </div>
  );
}

function PlanSheet() {
  return (
    <figure className="al-sheet" aria-labelledby="al-sheet-caption">
      <div className="al-sheet__paper">
        <div className="al-sheet__frame">
          <p className="al-sheet__goal">
            <span className="al-sheet__k">Goal</span>
            Which of three models writes safe, correct SQL for our reporting schema?
          </p>

          <ol className="al-plan" role="list">
            {EXAMPLE_PLAN.map((step, i) => (
              <li key={step.text} className="al-plan__row" data-state={step.state}>
                <span className="al-plan__n">{i + 1}</span>
                <span className="al-plan__t">{step.text}</span>
                <span className="al-plan__s">
                  {step.label}
                  {step.state === 'input' && <Ring shape="wide" tone="hl" />}
                </span>
              </li>
            ))}
          </ol>

          <div className="al-ask">
            <span className="al-sheet__k">The agent asks</span>
            <p>Read-only queries, or may the model write to the database too?</p>
          </div>

          <dl className="al-title">
            <div>
              <dt>Title</dt>
              <dd>SQL safety comparison</dd>
            </div>
            <div>
              <dt>Version</dt>
              <dd>1</dd>
            </div>
            <div>
              <dt>Drawn by</dt>
              <dd>Atlas agent</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>Needs input</dd>
            </div>
            <div className="al-title__limits">
              <dt>Hard limits</dt>
              <dd>{LIMITS.steps} steps</dd>
              <dd>{LIMITS.toolCalls} tool calls</dd>
              <dd>{LIMITS.repairAttempts} repairs</dd>
              <dd>{LIMITS.minutes} minutes</dd>
            </div>
          </dl>
        </div>
      </div>
      <figcaption id="al-sheet-caption">
        An example plan, partway through. The agent has stopped to ask a question.
      </figcaption>
    </figure>
  );
}

/** True when there is a stored token that has not expired. */
function useSignedIn(): boolean {
  return useMemo(() => {
    try {
      const token = getAuthToken();
      return Boolean(token) && !isTokenExpired(token as string);
    } catch {
      return false;
    }
  }, []);
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function AgentLanding() {
  const signedIn = useSignedIn();
  const agentHref = signedIn ? '/dashboard/agent' : '/login';
  const agentLabel = signedIn ? 'Open the agent' : 'Try the agent';

  // The app shell is dark; this page is on white. Set the page chrome while mounted
  // and put everything back on the way out.
  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;
    const previous = {
      title: document.title,
      htmlBg: html.style.backgroundColor,
      bodyBg: body.style.backgroundColor,
      bodyColor: body.style.color,
    };
    document.title = 'Atlas: find out which model can do your job';
    html.style.backgroundColor = '#ffffff';
    body.style.backgroundColor = '#ffffff';
    body.style.color = '#0b1f4d';
    if (!window.location.hash) window.scrollTo(0, 0);
    return () => {
      document.title = previous.title;
      html.style.backgroundColor = previous.htmlBg;
      body.style.backgroundColor = previous.bodyBg;
      body.style.color = previous.bodyColor;
    };
  }, []);

  return (
    <div className="al-root" id="top">
      <a className="al-skip" href="#main">
        Skip to content
      </a>

      <header className="al-header">
        <div className="al-wrap al-header__inner">
          <a className="al-brand" href="#top" aria-label="Atlas, back to top">
            <Mark />
            <span>Atlas</span>
          </a>
          <nav className="al-nav" aria-label="Sections">
            <a href="#how">How it works</a>
            <a href="#does">What it does</a>
            <a href="#start">Get started</a>
            <a href="#principles">Principles</a>
          </nav>
          <div className="al-header__cta">
            {!signedIn && (
              <Link className="al-textlink" to="/login">
                Sign in
              </Link>
            )}
            <Link className="al-btn al-btn--solid al-btn--small" to={agentHref}>
              {agentLabel}
            </Link>
          </div>
        </div>
      </header>

      <main id="main">
        {/* Hero */}
        <section className="al-wrap al-hero" aria-labelledby="al-hero-title">
          <div className="al-hero__copy">
            <h1 id="al-hero-title" className="al-h1">
              Which of these models can actually do my job?
            </h1>
            <p className="al-lead">
              Atlas is an agent that finds out. Describe the job in a sentence. It writes a plan, asks
              about anything it can’t guess, builds or finds the benchmark, runs it against the models
              you name in isolated containers, and hands you a report.
            </p>
            <div className="al-hero__actions">
              <Link className="al-btn al-btn--solid" to={agentHref}>
                {agentLabel}
              </Link>
              <CopyCommand command={INSTALL_COMMAND} />
            </div>
            <p className="al-fine">
              Tests models from Gemini, Groq, Mistral and NVIDIA NIM. Early access, so expect rough
              edges.
            </p>
          </div>
          <PlanSheet />
        </section>

        {/* What it is */}
        <section className="al-wrap al-section al-split" id="what" aria-labelledby="al-what-title">
          <h2 id="al-what-title" className="al-h2">
            Leaderboards answer a different question.
          </h2>
          <div className="al-prose">
            <p>
              A leaderboard tells you how a model did on a test somebody else wrote, usually on
              questions that have been public long enough to end up in training data. It doesn’t tell
              you whether the model can do the thing you need done.
            </p>
            <p>
              Atlas starts from your task instead. You say what the model has to do. The agent turns
              that into a benchmark, versions it so it can be rerun unchanged, runs it against the
              models you name, and scores every answer against reference checks. You get a report, and
              the agent’s whole trail, every plan step, tool call and result, stays with the task.
            </p>
          </div>
        </section>

        {/* How a task runs */}
        <section className="al-wrap al-section" id="how" aria-labelledby="al-how-title">
          <div className="al-section__head">
            <h2 id="al-how-title" className="al-h2">
              How a task runs
            </h2>
            <p>
              Here’s what happens between your sentence and the report. The red marks are the two
              places where the agent isn’t moving.
            </p>
          </div>
          <ol className="al-route" role="list">
            {STEPS.map((step, i) => (
              <li key={step.title} className="al-route__step">
                {step.mark && <span className="al-route__mark">{step.mark}</span>}
                <span className="al-route__node" aria-hidden="true">
                  {i + 1}
                </span>
                {step.mark && <Ring shape="round" tone="red" />}
                <h3 className="al-h3">{step.title}</h3>
                <p>{step.body}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* What it does today */}
        <section className="al-wrap al-section" id="does" aria-labelledby="al-does-title">
          <div className="al-section__head">
            <h2 id="al-does-title" className="al-h2">
              What the agent does today
            </h2>
            <p>Everything on this list is built and running. What isn’t is further down the page.</p>
          </div>
          <dl className="al-spec">
            {SPEC.map((row) => (
              <div key={row.term} className="al-spec__row">
                <dt>{row.term}</dt>
                <dd>{row.body}</dd>
              </div>
            ))}
          </dl>
        </section>

        {/* Get started */}
        <section className="al-wrap al-section" id="start" aria-labelledby="al-start-title">
          <div className="al-section__head">
            <h2 id="al-start-title" className="al-h2">
              Start in the browser or the terminal
            </h2>
          </div>
          <div className="al-start">
            <div className="al-panel">
              <h3 className="al-h3">In the browser</h3>
              <ol role="list">
                <li>Sign in, or create an account.</li>
                <li>Open the agent and describe the job you want a model to do.</li>
                <li>Answer its questions if it has any, then come back for the report.</li>
              </ol>
              <div>
                <Link className="al-btn al-btn--solid" to={agentHref}>
                  {agentLabel}
                </Link>
              </div>
            </div>
            <div className="al-panel">
              <h3 className="al-h3">In the terminal</h3>
              <div className="al-term">
                <Command text={INSTALL_COMMAND} />
                <Command text="atlas login" />
                <Command text={AGENT_COMMAND} />
              </div>
              <p className="al-fine">
                Needs Python 3.11 or newer. <code className="al-inline">atlas --help</code> lists
                every command. The terminal agent is a preview and may change.
              </p>
            </div>
          </div>
        </section>

        {/* Principles */}
        <section className="al-wrap al-section" id="principles" aria-labelledby="al-mission">
          <h2 id="al-mission" className="al-mission">
            Make it cheap to find out what a model can really do, and hard to fake the answer.
          </h2>
          <ul className="al-principles" role="list">
            {PRINCIPLES.map((p) => (
              <li key={p.title}>
                <h3 className="al-h3">{p.title}</h3>
                <p>{p.body}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* Not built yet */}
        <section className="al-wrap al-section" id="next" aria-labelledby="al-next-title">
          <div className="al-section__head">
            <h2 id="al-next-title" className="al-h2">
              Where this is going
            </h2>
            <p>
              None of this exists yet. It’s the direction, written down so you can hold us to it.
            </p>
          </div>
          <ul className="al-next" role="list">
            {NEXT.map((item) => (
              <li key={item.title}>
                <h3 className="al-h3">{item.title}</h3>
                <p>{item.body}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* Closing */}
        <section className="al-wrap al-section" aria-labelledby="al-close-title">
          <div className="al-close">
            <h2 id="al-close-title" className="al-h2">
              Ask it your version of that question.
            </h2>
            <Link className="al-btn al-btn--solid" to={agentHref}>
              {agentLabel}
            </Link>
          </div>
        </section>
      </main>

      <footer className="al-footer">
        <div className="al-wrap">
          <div className="al-footer__grid">
            <p>
              Atlas is built by Synthesis Works. It’s early access software, so expect rough edges.
            </p>
            <ul role="list">
              <li>
                <Link to={agentHref}>{agentLabel}</Link>
              </li>
              {!signedIn && (
                <li>
                  <Link to="/login">Sign in</Link>
                </li>
              )}
              <li>
                <Link to="/cli/install">Install the CLI</Link>
              </li>
              <li>
                <a href={GITHUB_URL} target="_blank" rel="noreferrer">
                  GitHub
                </a>
              </li>
              <li>
                <a href={PYPI_URL} target="_blank" rel="noreferrer">
                  PyPI
                </a>
              </li>
            </ul>
          </div>
          <small>© 2026 Synthesis Works</small>
        </div>
      </footer>
    </div>
  );
}
