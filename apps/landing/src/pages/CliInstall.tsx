/**
 * Atlas CLI — Installation & Getting Started guide
 *
 * A dedicated, step-by-step page for normal users (not repo contributors):
 * prerequisites, install, verify, authenticate, first command, agent mode,
 * and troubleshooting. Kept separate from the concise `/cli` landing page.
 */

import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  Terminal,
  KeyRound,
  Bot,
  ArrowRight,
  ShieldCheck,
  Download,
  Package,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
} from 'lucide-react';
import { pageCrossfade, fadeUp } from '@/lib/motion';
import { PageHero } from '@/components/layout/PageHero';
import { Card, Badge } from '@/design/primitives';

interface Step {
  n: string;
  title: string;
  description: React.ReactNode;
  commands: string[];
}

function CodeBlock({ lines }: { lines: string[] }) {
  return (
    <div className="rounded-xl border border-white/5 bg-black/40 p-3.5 overflow-x-auto">
      {lines.map((line, i) => (
        <code key={i} className="block text-sm text-[#F8FAFC] font-mono whitespace-pre">
          {line}
        </code>
      ))}
    </div>
  );
}

const STEPS: Step[] = [
  {
    n: '01',
    title: 'Prerequisites',
    description: (
      <>
        Atlas CLI requires <span className="text-white/70">Python 3.11 or newer</span>. Check your
        version before installing:
      </>
    ),
    commands: ['python --version'],
  },
  {
    n: '02',
    title: 'Install',
    description: (
      <>
        Install Atlas CLI as a normal Python package. The PyPI package is{' '}
        <span className="text-white/70">synthesis-atlas-cli</span>; the command you run is{' '}
        <span className="text-white/70">atlas</span>. The wheel is fully self-contained — the Atlas
        SDK and the LLM layer ship inside it, so one command is all you need:
      </>
    ),
    commands: ['python -m pip install synthesis-atlas-cli'],
  },
  {
    n: '03',
    title: 'Verify',
    description: (
      <>
        Confirm the install. <span className="text-white/70">atlas --version</span> prints the
        installed version, and <span className="text-white/70">atlas --help</span> lists every
        command and option. If <span className="text-white/70">atlas</span> is not yet on your{' '}
        <span className="text-white/70">PATH</span>, the same CLI is available as{' '}
        <span className="text-white/70">python -m cli</span>:
      </>
    ),
    commands: ['atlas --version', 'atlas --help', 'python -m cli --version'],
  },
  {
    n: '04',
    title: 'Authenticate',
    description: (
      <>
        Atlas CLI connects to the <span className="text-white/70">hosted Atlas API</span> by default —
        no configuration needed. The access token is saved in your{' '}
        <span className="text-white/70">user profile</span> — never in the repository — and is never
        printed:
      </>
    ),
    commands: ['atlas login', 'atlas whoami'],
  },
  {
    n: '05',
    title: 'Run your first command',
    description: (
      <>
        Every deterministic command is a scriptable, reliable operation with human, JSON, and quiet
        output. This is the recommended Atlas CLI workflow. Try a health check or a leaderboard:
      </>
    ),
    commands: ['atlas health', 'atlas leaderboard model mock'],
  },
  {
    n: '06',
    title: 'Try the experimental agent (preview)',
    description: (
      <>
        Atlas CLI also embeds an <span className="text-white/70">experimental conversational
        agent</span> — an ongoing test surface, so behavior may change. Run{' '}
        <span className="text-white/70">atlas</span> bare to open an interactive conversation, or pass
        a quoted task for a one-shot run. When authenticated, the agent can use the hosted Atlas
        agent; bring-your-own-key (BYOK) provider support is also available. Set{' '}
        <span className="text-white/70">GROQ_API_KEY</span> or{' '}
        <span className="text-white/70">GEMINI_API_KEY</span> with your platform's syntax —
        PowerShell <span className="text-[#F8FAFC]/90 font-mono">$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"</span>,
        macOS/Linux/Git Bash <span className="text-[#F8FAFC]/90 font-mono">export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"</span>,
        or Colab <span className="text-[#F8FAFC]/90 font-mono">%env GEMINI_API_KEY=YOUR_GEMINI_API_KEY</span>:
      </>
    ),
    commands: ['atlas', 'atlas agent "List the available benchmarks"'],
  },
];

const TROUBLESHOOTING = [
  {
    icon: Package,
    title: 'pip cannot find the package',
    body: `If pip reports "No matching distribution found for synthesis-atlas-cli", the package name may be
    wrong or the release may not be published to the index you are using. Atlas CLI is distributed
    as a standard PyPI package called synthesis-atlas-cli. Try \`pip install --upgrade pip\` first, then
    \`python -m pip install synthesis-atlas-cli\`.`,
  },
  {
    icon: Terminal,
    title: '"atlas" is not recognized as a command',
    body: `The \`atlas\` executable is installed into your Python "Scripts" directory (for example
    C:\\Users\\<you>\\AppData\\Local\\Python\\Python3xx\\Scripts on Windows). Typing \`atlas\` only
    works when that directory is on your PATH. To find where it was installed, run \`python -m pip
    show -f synthesis-atlas-cli\` — look for the Scripts/bin path at the bottom. To use the CLI
    without touching PATH at all, run \`python -m cli --version\` instead of \`atlas\`. To make
    \`atlas\` work everywhere, add that Scripts folder to your PATH (Windows: "Environment
    Variables" / "Edit the system environment variables" → Advanced → Environment Variables →
    User variables → Path). Atlas does not modify PATH automatically; this is normal Python
    behavior. On Windows, \`py\` instead of \`python\` may be needed.`,
  },
  {
    icon: AlertTriangle,
    title: 'Python version issues',
    body: `Atlas CLI requires Python 3.11+. If \`pip\` refuses to install, upgrade Python first, then
    create a fresh environment and try again. Check with \`python --version\` (Windows: \`py
    --version\`).`,
  },
  {
    icon: KeyRound,
    title: 'Agent says "brain unavailable" or "export is not recognized"',
    body: `On Windows PowerShell do NOT use Bash syntax like \`export GEMINI_API_KEY="..."\`. The correct
    PowerShell form is \`$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"\` (same for \`GROQ_API_KEY\`). On
    macOS/Linux/Git Bash use \`export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"\`; in Google Colab use
    \`%env GEMINI_API_KEY=YOUR_GEMINI_API_KEY\`. Create keys at console.groq.com (Groq) or
    ai.google.dev (Gemini), then retry the command.`,
  },
  {
    icon: KeyRound,
    title: 'Authentication issues',
    body: `Log in with \`atlas login\` and confirm with \`atlas whoami\`. If commands are rejected,
    make sure you are connected to the right deployment — Atlas CLI uses the hosted API by default,
    and \`ATLAS_BASE_URL\` / \`--base-url\` only need to be set for local or self-hosted deployments —
    and that your account is active. The token is stored in your user profile — delete it with
    \`atlas logout\` and log in again.`,
  },
];

export default function CliInstall() {
  return (
    <motion.div
      variants={pageCrossfade}
      initial="initial"
      animate="animate"
      exit="exit"
      className="relative min-h-screen"
    >
      <div className="relative z-10">
        <PageHero
          eyebrow="Atlas CLI"
          title="Installation guide"
          accent="Get started in minutes."
          description="Install Atlas CLI once and control the whole evaluation platform from the command line — deterministic commands for reliable benchmark workflows, plus an experimental conversational agent you can try. No source code required."
          cta={
            <div className="flex flex-wrap items-center justify-center gap-3">
              <a
                href="https://github.com/Synthesis-works/atlas/tree/main/cli"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-full text-white transition-colors duration-200"
                style={{ background: 'var(--color-accent)' }}
              >
                View CLI source
                <ArrowRight className="w-4 h-4" />
              </a>
              <Link
                to="/cli"
                className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-full text-white/70 border border-white/10 hover:border-white/25 hover:text-white transition-colors duration-200"
              >
                <Terminal className="w-4 h-4" />
                Back to the CLI overview
              </Link>
            </div>
          }
        />

        {/* Prerequisites */}
        <section className="px-6 pb-20 max-w-3xl mx-auto">
          <motion.div
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: false, margin: '-80px' }}
            className="rounded-xl border border-white/5 bg-white/[0.02] p-5 flex items-start gap-3"
          >
            <ShieldCheck className="w-5 h-5 text-[#4F8CFF]/85 shrink-0 mt-0.5" />
            <p className="text-xs text-white/40 leading-relaxed">
              <span className="text-white/70">You only need Python and pip.</span> You do not need
              the Atlas repository, an SDK install, or any other package —{' '}
              <span className="text-white/70">synthesis-atlas-cli</span> bundles everything it needs.
            </p>
          </motion.div>
        </section>

        {/* Steps */}
        <section className="px-6 pb-24 max-w-3xl mx-auto">
          <motion.div
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: false, margin: '-80px' }}
            className="flex items-center gap-3 mb-10"
          >
            <Download className="w-5 h-5 text-[#4F8CFF]/70" />
            <h3 className="text-lg font-semibold text-white">Step-by-step</h3>
          </motion.div>

          <div className="space-y-8">
            {STEPS.map((step) => (
              <motion.div
                key={step.n}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: false, margin: '-80px' }}
              >
                <Card className="!p-5 border border-white/5">
                  <div className="flex items-center gap-3 mb-4">
                    <Badge variant="outline" className="!px-2 shrink-0">
                      {step.n}
                    </Badge>
                    <h4 className="text-sm font-semibold text-white">{step.title}</h4>
                  </div>
                  <p className="text-xs text-white/30 leading-relaxed mb-4">{step.description}</p>
                  <CodeBlock lines={step.commands} />
                </Card>
              </motion.div>
            ))}
          </div>

          <motion.div
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: false, margin: '-80px' }}
            className="mt-8 rounded-xl border border-white/5 bg-white/[0.02] p-5"
          >
            <h4 className="text-sm font-semibold text-white mb-2">Connecting elsewhere</h4>
            <p className="text-xs text-white/30 leading-relaxed">
              Atlas CLI uses the hosted Atlas API by default. To connect to a local or self-hosted
              deployment, set the <span className="text-white/70">ATLAS_BASE_URL</span> environment
              variable or pass <span className="text-white/70">--base-url</span> — for example{' '}
              <span className="text-white/70">atlas --base-url http://localhost:8000 health</span>.
            </p>
          </motion.div>
        </section>

        {/* Troubleshooting */}
        <section className="px-6 pb-24 max-w-3xl mx-auto">
          <motion.div
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: false, margin: '-80px' }}
            className="flex items-center gap-3 mb-8"
          >
            <Sparkles className="w-5 h-5 text-[#4F8CFF]/70" />
            <h3 className="text-lg font-semibold text-white">Troubleshooting</h3>
          </motion.div>

          <div className="space-y-4">
            {TROUBLESHOOTING.map((item) => (
              <motion.div
                key={item.title}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: false, margin: '-80px' }}
              >
                <Card className="!p-5 border border-white/5">
                  <div className="flex items-center gap-3 mb-2">
                    <item.icon className="w-4 h-4 text-[#4F8CFF]/70 shrink-0" />
                    <h4 className="text-sm font-semibold text-white">{item.title}</h4>
                  </div>
                  <p className="text-xs text-white/30 leading-relaxed whitespace-pre-line">{item.body}</p>
                </Card>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Bottom CTA */}
        <section className="px-6 pb-40 max-w-3xl mx-auto">
          <motion.div
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: false, margin: '-80px' }}
            className="text-center"
          >
            <Bot className="w-6 h-6 text-[#4F8CFF]/70 mx-auto mb-3" />
            <p className="text-sm text-white/70 mb-1 font-medium">Ready when you are</p>
            <p className="text-xs text-white/30 mb-6">
              Authenticate, run your first deterministic command, then try the experimental conversational agent when you're ready.
            </p>
            <Link
              to="/cli"
              className="inline-flex items-center gap-2 px-6 py-2.5 text-sm font-medium rounded-full text-white transition-colors duration-200"
              style={{ background: 'var(--color-accent)' }}
            >
              <CheckCircle2 className="w-4 h-4" />
              Verify your install on the CLI page
            </Link>
          </motion.div>
        </section>
      </div>
    </motion.div>
  );
}