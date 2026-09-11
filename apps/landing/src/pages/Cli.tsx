/**
 * CLI Page — Atlas command-line interface
 *
 * A focused marketing section for `atlas-cli`: what it is, why to use it,
 * installation, deterministic commands, the agentic mode (`atlas` / `atlas
 * agent "..."`), and authentication. Links out to the GitHub repository and
 * the release/onboarding guide instead of becoming a full docs portal.
 */

import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  Terminal,
  Rocket,
  KeyRound,
  Bot,
  GitBranch,
  ArrowRight,
  Blocks,
  ShieldCheck,
  Download,
} from 'lucide-react';
import { pageCrossfade, fadeUp, stagger } from '@/lib/motion';
import { PageHero } from '@/components/layout/PageHero';
import { Card, Badge } from '@/design/primitives';

const WHY = [
  {
    icon: Blocks,
    title: 'Deterministic by design',
    description:
      'A scriptable command-line interface to the Atlas control plane, with deterministic commands for reliable benchmark workflows.',
  },
  {
    icon: ShieldCheck,
    title: 'Credential-safe by design',
    description:
      'Tokens are stored in your user profile, never in the repo or on disk in the project.',
  },
  {
    icon: Bot,
    title: 'An experimental agent, too',
    description:
      'Bare `atlas` opens an interactive agent REPL, or run a single task with `atlas agent "..."`. Preview surface — behavior may change.',
  },
];

const INSTALL_STEPS = [
  {
    command: 'python -m pip install synthesis-atlas-cli',
    caption: 'Python 3.11+ — fully self-contained, no extra SDK install required.',
  },
  {
    command: 'atlas login',
    caption: 'Authenticate once; your token is saved in your user profile.',
  },
  {
    command: 'atlas --help',
    caption: 'List every command and option before you go further.',
  },
];

const DETERMINISTIC = [
  { command: 'atlas health', description: 'Check Atlas API health.' },
  { command: 'atlas login', description: 'Authenticate against the hosted API.' },
  { command: 'atlas whoami', description: 'Confirm your identity.' },
  { command: 'atlas dashboard', description: 'Workspace dashboard summary.' },
  { command: 'atlas leaderboard', description: 'Model / benchmark leaderboards.' },
  { command: 'atlas benchmark', description: 'Benchmark operations.' },
  { command: 'atlas benchmark versions', description: 'Inspect immutable benchmark versions.' },
  { command: 'atlas model', description: 'Model operations.' },
  { command: 'atlas report', description: 'Execution reports.' },
  { command: 'atlas run', description: 'Start executions.' },
  { command: 'atlas activity', description: 'Recent platform activity.' },
];

export default function Cli() {
  return (
    <motion.div variants={pageCrossfade} initial="initial" animate="animate" exit="exit" className="relative min-h-screen">
      <div className="relative z-10">
        <PageHero
          eyebrow="Atlas CLI"
          title="The control plane"
          accent="in your terminal."
          description="Atlas CLI gives you a scriptable command-line interface to the Atlas control plane, with deterministic commands for reliable benchmark workflows — plus an experimental conversational agent you can try."
          cta={
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Link
                to="/cli/install"
                className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-full text-white transition-colors duration-200"
                style={{ background: 'var(--color-accent)' }}
              >
                <Download className="w-4 h-4" />
                Install Atlas CLI
                <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="#installation"
                className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-full text-white/70 border border-white/10 hover:border-white/25 hover:text-white transition-colors duration-200"
              >
                <Terminal className="w-4 h-4" />
                Get started
              </a>
            </div>
          }
        />

        {/* Why Atlas CLI */}
        <section className="px-6 pb-24 max-w-5xl mx-auto">
          <motion.h3
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: false }}
            className="text-xs tracking-[0.2em] uppercase text-white/20 mb-8 text-center"
          >
            Why Atlas CLI
          </motion.h3>
          <motion.div
            variants={stagger(0.08, 0)}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: false, margin: '-80px' }}
            className="grid grid-cols-1 md:grid-cols-3 gap-4"
          >
            {WHY.map((item) => (
              <motion.div key={item.title} variants={fadeUp}>
                <Card hover className="h-full !p-6 border border-white/5 hover:border-white/15">
                  <div className="liquid-glass rounded-xl p-3 shrink-0 w-fit mb-4">
                    <item.icon className="w-5 h-5 text-[#4F8CFF]/85" />
                  </div>
                  <h4 className="text-sm font-semibold text-white mb-1.5">{item.title}</h4>
                  <p className="text-xs text-white/30 leading-relaxed">{item.description}</p>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        </section>

        {/* Installation */}
        <section id="installation" className="px-6 pb-24 max-w-2xl mx-auto scroll-mt-24">
          <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-80px' }} className="flex items-center gap-3 mb-8">
            <Download className="w-5 h-5 text-[#4F8CFF]/70" />
            <h3 className="text-lg font-semibold text-white">Installation & onboarding</h3>
          </motion.div>

          <div className="space-y-5">
            {INSTALL_STEPS.map((step, i) => (
              <motion.div
                key={step.command}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: false, margin: '-80px' }}
              >
                <Card className="!p-1.5 border border-white/5">
                  <div className="flex items-center gap-3 px-3 py-2.5">
                    <Badge variant="outline" className="!px-2 shrink-0">
                      0{i + 1}
                    </Badge>
                    <code className="flex-1 text-sm text-[#F8FAFC] font-mono">{step.command}</code>
                    <Terminal className="w-4 h-4 text-white/20 shrink-0" />
                  </div>
                </Card>
                <p className="text-xs text-white/30 mt-2 pl-1">{step.caption}</p>
              </motion.div>
            ))}
          </div>

          <motion.div
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: false, margin: '-80px' }}
            className="mt-8"
          >
            <Link
              to="/cli/install"
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-full text-white transition-colors duration-200"
              style={{ background: 'var(--color-accent)' }}
            >
              Read the step-by-step installation guide
              <ArrowRight className="w-4 h-4" />
            </Link>
          </motion.div>
        </section>

        {/* Two modes */}
        <section className="px-6 pb-24 max-w-5xl mx-auto">
          <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-80px' }} className="flex items-center gap-3 mb-8">
            <GitBranch className="w-5 h-5 text-[#4F8CFF]/70" />
            <h3 className="text-lg font-semibold text-white">Two ways to use Atlas CLI</h3>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Deterministic */}
            <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-80px' }}>
              <Card hover className="h-full !p-6 border border-white/5 hover:border-white/15">
                <div className="flex items-center justify-between mb-4">
                  <div className="liquid-glass rounded-xl p-3 shrink-0">
                    <Blocks className="w-5 h-5 text-[#4F8CFF]/85" />
                  </div>
                  <Badge variant="default">Recommended</Badge>
                </div>
                <h4 className="text-sm font-semibold text-white mb-1">Deterministic commands</h4>
                <p className="text-xs text-white/30 leading-relaxed mb-5">
                  The primary Atlas CLI workflow. One-shot operations ideal for scripts, pipelines, and quick inspection. Human, JSON, and quiet output modes.
                </p>
                <ul className="space-y-1.5">
                  {DETERMINISTIC.map((item) => (
                    <li key={item.command} className="flex items-baseline gap-2">
                      <code className="text-xs text-[#4F8CFF]/80 font-mono shrink-0">{item.command}</code>
                      <span className="text-[11px] text-white/25 leading-snug">{item.description}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            </motion.div>

            {/* Agentic */}
            <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-80px' }}>
              <Card hover className="h-full !p-6 border border-white/5 hover:border-white/15">
                <div className="flex items-center justify-between mb-4">
                  <div className="liquid-glass rounded-xl p-3 shrink-0">
                    <Bot className="w-5 h-5 text-[#4F8CFF]/85" />
                  </div>
                  <Badge variant="outline">Experimental</Badge>
                </div>
                <h4 className="text-sm font-semibold text-white mb-1">Conversational agent (preview)</h4>
                <p className="text-xs text-white/30 leading-relaxed mb-5">
                  An experimental LLM-powered agent inside the CLI. Interactive conversation in your terminal, or a one-shot task run — an ongoing test surface.
                </p>
                <div className="space-y-2.5">
                  <div className="rounded-xl border border-white/5 bg-black/40 p-3.5">
                    <p className="text-[11px] text-white/25 font-mono mb-2"># Interactive agent — bare `atlas`</p>
                    <code className="text-sm text-[#F8FAFC] font-mono">{'atlas'}</code>
                  </div>
                  <div className="rounded-xl border border-white/5 bg-black/40 p-3.5">
                    <p className="text-[11px] text-white/25 font-mono mb-2"># One-shot task</p>
                    <code className="text-sm text-[#F8FAFC] font-mono">{'atlas agent "List the available benchmarks"'}</code>
                  </div>
                </div>
                <p className="text-[11px] text-white/25 leading-relaxed mt-4">
                  The conversational agent is an experimental surface under active development. For predictable benchmark workflows, use the deterministic CLI commands.
                </p>
              </Card>
            </motion.div>
          </div>
        </section>

        {/* Auth / config */}
        <section className="px-6 pb-40 max-w-2xl mx-auto">
          <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-80px' }} className="flex items-center gap-3 mb-8">
            <KeyRound className="w-5 h-5 text-[#4F8CFF]/70" />
            <h3 className="text-lg font-semibold text-white">Authentication & configuration</h3>
          </motion.div>

          <div className="space-y-4">
            <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-80px' }}>
              <Card className="!p-5 border border-white/5">
                <p className="text-xs text-white/30 leading-relaxed">
                  Authenticate with{' '}
                  <code className="text-[#4F8CFF]/80 font-mono">atlas login</code>{' '}
                  — the access token is saved in your user profile and is never printed. Atlas CLI uses
                  the hosted Atlas API by default; point it at a local or self-hosted deployment with
                  the <code className="text-[#4F8CFF]/80 font-mono">ATLAS_BASE_URL</code> environment
                  variable or <code className="text-[#4F8CFF]/80 font-mono">--base-url</code>. Verify
                  with <code className="text-[#4F8CFF]/80 font-mono">atlas whoami</code>.
                </p>
              </Card>
            </motion.div>

            <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-80px' }}>
              <Card className="!p-5 border border-white/5">
                <p className="text-xs text-white/30 leading-relaxed mb-3">
                  The agent brain runs on a provider key. With none configured, the agent refuses to start and
                  prints the exact setup command for your platform:
                </p>
                <div className="rounded-xl border border-white/5 bg-black/40 p-3.5 space-y-1">
                  <p className="text-[11px] text-white/25 font-mono"># Windows PowerShell</p>
                  <code className="block text-xs text-[#F8FAFC] font-mono">
                    {'$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"'}
                  </code>
                  <p className="text-[11px] text-white/25 font-mono pt-1"># macOS / Linux / Git Bash</p>
                  <code className="block text-xs text-[#F8FAFC] font-mono">
                    {'export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"'}
                  </code>
                  <p className="text-[11px] text-white/25 font-mono pt-1"># Google Colab</p>
                  <code className="block text-xs text-[#F8FAFC] font-mono">
                    {'%env GEMINI_API_KEY=YOUR_GEMINI_API_KEY'}
                  </code>
                  <p className="text-[11px] text-white/25 pt-1">
                    # Groq: use GROQ_API_KEY / YOUR_GROQ_API_KEY instead
                  </p>
                </div>
              </Card>
            </motion.div>

            <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: false, margin: '-80px' }} className="text-center pt-4">
              <p className="text-xs text-white/30 mb-3">More details, release process, and validation workflow:</p>
              <a
                href="https://github.com/Synthesis-works/atlas"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 text-xs text-[#4F8CFF] hover:text-white transition-colors duration-200"
              >
                <Rocket className="w-3.5 h-3.5" />
                Atlas GitHub repository
                <ArrowRight className="w-3.5 h-3.5" />
              </a>
            </motion.div>
          </div>
        </section>
      </div>
    </motion.div>
  );
}