/**
 * Platform Page — "What Atlas is"
 *
 * Explains the 7 architectural layers, 5 engineering principles, and the
 * adapter pattern. Network-forward hero; reads from domain constants.
 */

import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { pageCrossfade, fadeUp, stagger } from '@/lib/motion';
import { PageHero } from '@/components/layout/PageHero';
import { Card } from '@/design/primitives';
import { CardFlip } from '@/components/ui/CardFlip';
import { CostEstimator } from '@/components/ui/CostEstimator';

const LAYERS = [
  { name: 'Presentation', description: 'Dashboard, auth pages, benchmark browser, report viewer.', order: 1 },
  { name: 'API Layer', description: 'Gateway: validation, auth, rate limiting, routing.', order: 2 },
  { name: 'Business Logic', description: 'Benchmark / Execution / Evaluation / Reporting engines.', order: 3 },
  { name: 'Infrastructure', description: 'Configuration, audit, logging, notifications, workers.', order: 4 },
  { name: 'Data Layer', description: 'PostgreSQL, Redis, Object Storage, Dataset Registry.', order: 5 },
  { name: 'Adapter Layer', description: 'Standardized interface to external AI systems.', order: 6 },
  { name: 'External Systems', description: 'LLM runtimes, cloud inference, enterprise deployments.', order: 7 },
];

const PRINCIPLES = [
  {
    label: 'Reproducibility',
    description: 'Every evaluation is deterministic and verifiable.',
    details: 'Atlas achieves strict determinism by running benchmark containers with locked random seeds, pin-point dependency isolation, and fully serialized execution logs.',
    features: ['Fixed seed seeding', 'Immutable artifact storage', 'Execution verification hash'],
  },
  {
    label: 'Transparency',
    description: 'Full methodology visibility. No black boxes.',
    details: 'No hidden logic or proprietary score adjustments. Every grading strategy, prompt template, and evaluation trace is fully open for audit and validation.',
    features: ['Open-source source code', 'Visible judge prompts', 'Factual scoring trace audit'],
  },
  {
    label: 'Modularity',
    description: 'Every component is replaceable. No lock-in.',
    details: 'Atlas is built on clean, pluggable interfaces. You can easily swap out the dataset registry, database adapters, evaluation judges, or model endpoints.',
    features: ['Universal adapter APIs', 'Detachable DB connectors', 'Custom engine injection'],
  },
  {
    label: 'Extensibility',
    description: 'Benchmarks, judges, and adapters are pluggable.',
    details: 'Register your own benchmarks via YAML config, inject custom LLM-as-judge scoring models, and plug in custom execution runners seamlessly.',
    features: ['YAML capability mapping', 'Hot-swappable plugins', 'Custom agent runtimes'],
  },
  {
    label: 'Evidence-Driven',
    description: 'Trust is engineered through evidence, not claims.',
    details: 'Every score is supported by full execution transcripts. Rather than simple aggregates, Atlas records exact model answers, token tokens, and judge rationales.',
    features: ['Transcript audit logs', 'Granular token usage stats', 'Confidence interval scoring'],
  },
];

export default function Platform() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: false, margin: '-100px' });

  return (
    <motion.div variants={pageCrossfade} initial="initial" animate="animate" exit="exit" className="relative">
      {/* Background Watermark specifically for the Platform page hero section */}
      <div className="absolute top-0 inset-x-0 h-[65vh] overflow-hidden pointer-events-none z-0">
        <div 
          className="absolute inset-0 bg-cover bg-center mix-blend-overlay opacity-[0.24]"
          style={{ backgroundImage: `url('/platform-bg.jpg')` }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-ink-2" />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-ink-2 to-transparent" />
      </div>

      <div className="relative z-10">
        <PageHero
          eyebrow="Atlas Platform"
          title="The Operating System"
          accent="for AI Evaluation"
          description="A modular, layered architecture that treats evaluation as an engineering discipline — from benchmark authoring through execution, scoring, and reporting."
        />

        <section className="px-6 pb-24 max-w-4xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] gap-6 items-stretch rounded-2xl border border-white/[0.07] bg-white/[0.015] p-5">
            <div className="flex flex-col justify-center">
              <p className="text-xs uppercase tracking-[0.2em] text-accent/70">Platform utility</p>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight text-white">Estimate the cost of a run before it starts.</h2>
              <p className="mt-3 max-w-md text-sm leading-relaxed text-white/35">
                Adjust volume and model tier to see how Atlas keeps evaluation planning visible and measurable.
              </p>
            </div>
            <CostEstimator />
          </div>
        </section>

      {/* Architecture layers */}
      <section ref={ref} className="px-6 pb-32 max-w-4xl mx-auto">
        <motion.h3
          variants={fadeUp}
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          className="text-xs tracking-[0.2em] uppercase text-white/20 mb-12 text-center"
        >
          Seven Architectural Layers
        </motion.h3>

        <motion.div
          variants={stagger(0.08, 0)}
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          className="space-y-3"
        >
          {LAYERS.map((layer, i) => (
            <motion.div key={layer.name} variants={fadeUp}>
              <Card hover className="flex items-start gap-6 !p-5">
                <span className="text-3xl font-serif italic text-white/10 shrink-0">
                  {layer.order}
                </span>
                <div>
                  <h4 className="text-sm font-semibold text-white mb-1">{layer.name}</h4>
                  <p className="text-sm text-white/30 leading-relaxed">{layer.description}</p>
                </div>
                <div className="ml-auto shrink-0 hidden md:block">
                  <div className={`w-2 h-2 rounded-full ${i === 5 ? 'bg-accent' : 'bg-white/10'}`} />
                </div>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* Engineering principles */}
      <section className="px-6 pb-32 max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false, margin: '-80px' }}
          transition={{ duration: 0.7 }}
          className="text-center mb-16"
        >
          <h3 className="text-xs tracking-[0.2em] uppercase text-white/20 mb-4">
            Five Engineering Principles
          </h3>
          <p className="text-lg text-white/30 max-w-lg mx-auto">
            Non-negotiable constraints that shape every engineering decision in Atlas.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {PRINCIPLES.map((p, i) => (
            <motion.div
              key={p.label}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false }}
              transition={{ duration: 0.6, delay: i * 0.08 }}
            >
              <CardFlip minHeight="h-[340px]">
                <CardFlip.Front>
                  <div className="h-full p-5 text-center flex flex-col items-center justify-center">
                    <h4 className="text-sm font-semibold text-white mb-2">{p.label}</h4>
                    <p className="text-xs text-white/25 leading-relaxed">{p.description}</p>
                  </div>
                </CardFlip.Front>
                <CardFlip.Back
                  title={p.label}
                  description={p.details}
                  features={p.features}
                  actionLabel="Learn More →"
                />
              </CardFlip>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Adapter pattern */}
      <section className="px-6 pb-40 max-w-3xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false }}
          transition={{ duration: 0.7 }}
        >
          <Card className="!p-10">
            <h3 className="text-xs tracking-[0.2em] uppercase text-accent/60 mb-4">
              The Defining Feature
            </h3>
            <h4 className="text-2xl font-semibold text-white mb-4 tracking-tight">
              The Adapter Pattern
            </h4>
            <p className="text-sm text-white/30 leading-relaxed mb-6">
              Every external AI system speaks one contract:
              <code className="text-accent/60 mx-1">initialize → validate → list_models → execute → health_check → shutdown</code>
            </p>
            <p className="text-xs text-white/15">
              Execution never scores. Evaluation never executes. Raw outputs are immutable.
            </p>
          </Card>
        </motion.div>
      </section>
      </div>
    </motion.div>
  );
}
