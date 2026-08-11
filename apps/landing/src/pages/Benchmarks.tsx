/**
 * Benchmarks Page
 *
 * Registry grid (from domain/benchmarks) + Benchmark Schema + Capability Taxonomy.
 * Page hero communicates purpose immediately.
 */

import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { ArrowUpRight } from 'lucide-react';
import { pageCrossfade, fadeUp, stagger } from '@/lib/motion';
import { PageHero } from '@/components/layout/PageHero';
import { Card, Badge } from '@/design/primitives';
import { CardFlip } from '@/components/ui/CardFlip';
import { MOCK_BENCHMARKS as BENCHMARKS } from '@/domain/benchmarks/mock';
import { BENCHMARK_CATEGORIES } from '@/domain/benchmarks/constants';
import type { Benchmark } from '@/domain/benchmarks/types';
import { CapabilitySelector } from '@/components/ui/CapabilitySelector';

const SCHEMA_STEPS = [
  { label: 'metadata.yaml', description: 'Identity, author, version, license' },
  { label: 'benchmark.json', description: 'Task definitions, evaluation strategy' },
  { label: 'tasks/', description: 'Individual task files' },
  { label: 'datasets/', description: 'Associated datasets' },
  { label: 'hidden_tests/', description: 'Immutable hidden test cases' },
  { label: 'evaluation/', description: 'Judge configurations' },
  { label: 'documentation/', description: 'Methodology notes' },
  { label: 'changelog.md', description: 'Version history (semver)' },
];

export default function Benchmarks() {
  const gridRef = useRef(null);
  const capabilityBoundsRef = useRef<HTMLDivElement>(null);
  const gridInView = useInView(gridRef, { once: false, margin: '-80px' });
  const schemaRef = useRef(null);
  const schemaInView = useInView(schemaRef, { once: false, margin: '-80px' });

  return (
    <motion.div variants={pageCrossfade} initial="initial" animate="animate" exit="exit" className="relative">
      <PageHero
        eyebrow="Benchmark Registry"
        title="Every benchmark,"
        accent="versioned and verified."
        description="A curated, version-controlled collection. Every benchmark is an immutable artifact with structured metadata, hidden tests, and reproducible evaluation strategies."
      />

      <section className="px-6 pb-24 max-w-6xl mx-auto">
        <div
          ref={capabilityBoundsRef}
          className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_360px] gap-5 items-stretch rounded-2xl border border-white/[0.07] bg-white/[0.015] p-4 sm:p-5 overflow-hidden"
        >
          <div className="flex flex-col justify-center px-2 sm:px-4 py-4">
            <p className="text-xs uppercase tracking-[0.2em] text-accent/70">Benchmark tools</p>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-white">Compare capability signals in context.</h2>
            <p className="mt-3 max-w-lg text-sm leading-relaxed text-white/35">
              Use the bounded selector to inspect how model strengths move across the same benchmark families.
            </p>
          </div>
          <CapabilitySelector boundsRef={capabilityBoundsRef} />
        </div>
      </section>

      {/* Registry Grid */}
      <section ref={gridRef} className="px-6 pb-32 max-w-6xl mx-auto">
        <motion.div
          variants={stagger(0.06, 0)}
          initial="hidden"
          animate={gridInView ? 'visible' : 'hidden'}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          {BENCHMARKS.map((bm: Benchmark) => {
            const cat = BENCHMARK_CATEGORIES[bm.category];
            return (
              <motion.div key={bm.id} variants={fadeUp}>
                <CardFlip minHeight="h-[350px]">
                  <CardFlip.Front>
                    <div className="group h-full p-6 flex flex-col justify-between">
                      <div>
                        <div className="flex items-start justify-between mb-3">
                          <span className={`text-xs uppercase tracking-widest ${cat?.color || 'text-white/60'}`}>
                            {cat?.label || bm.category}
                          </span>
                          <div className="liquid-glass rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                            <ArrowUpRight className="w-3.5 h-3.5 text-white/50" />
                          </div>
                        </div>
                        <h3 className="text-lg font-semibold text-white mb-2">{bm.name}</h3>
                        <p className="text-xs text-white/30 leading-relaxed mb-4">{bm.description}</p>
                      </div>
                      <div>
                        <div className="flex flex-wrap gap-1.5 mb-4">
                          {bm.tags.map((tag: string) => (
                            <Badge key={tag}>{tag}</Badge>
                          ))}
                        </div>
                        <div className="flex items-center gap-4 text-xs text-white/15">
                          <span>v{bm.version}</span>
                          <span>{bm.tasksCount.toLocaleString()} tasks</span>
                          <span>{bm.estimatedRuntime}</span>
                        </div>
                      </div>
                    </div>
                  </CardFlip.Front>
                  <CardFlip.Back
                    title={bm.name}
                    description={bm.details}
                    features={bm.methodology}
                    actionLabel="Explore Benchmark →"
                  />
                </CardFlip>
              </motion.div>
            );
          })}
        </motion.div>
      </section>

      {/* Benchmark Schema */}
      <section ref={schemaRef} className="px-6 pb-32 max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={schemaInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
          className="text-center mb-12"
        >
          <h3 className="text-xs tracking-[0.2em] uppercase text-white/20 mb-3">
            Atlas Benchmark Schema
          </h3>
          <p className="text-sm text-white/30 max-w-lg mx-auto">
            A benchmark is not a single file — it is a structured, versioned artifact.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={schemaInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.15 }}
        >
          <Card className="!p-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {SCHEMA_STEPS.map((step, i) => (
                <div key={step.label} className="flex items-start gap-3">
                  <span className="text-xs text-white/10 font-mono shrink-0">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <div>
                    <code className="text-xs text-accent/60">{step.label}</code>
                    <p className="text-xs text-white/20 mt-0.5">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6 pt-4 border-t border-white/[0.04]">
              <p className="text-xs text-white/10">
                Packed as <code className="text-accent/40">atlas_benchmark.zip</code> with manifest
                (schema_version, benchmark_version, artifact_hash, dataset_hashes, signature).
                Published versions are immutable.
              </p>
            </div>
          </Card>
        </motion.div>
      </section>
    </motion.div>
  );
}
