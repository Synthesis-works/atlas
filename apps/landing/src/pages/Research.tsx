/**
 * Research Page — signature Atlas research experience
 *
 * Capability Genome, Atlas Evaluation Methodology flow, Benchmark Evolution
 * timeline, and Future Directions. All data from domain/research + models.
 */

import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { ArrowRight } from 'lucide-react';
import { pageCrossfade, fadeUp, stagger } from '@/lib/motion';
import { PageHero } from '@/components/layout/PageHero';
import { Card, Badge } from '@/design/primitives';
import { CardFlip } from '@/components/ui/CardFlip';
import { Heading } from '@/design/Typography';
import { AI_MODELS } from '@/domain/models/types';
import {
  AEM_STAGES,
  CAPABILITY_TAXONOMY,
  ATLAS_EVOLUTION,
  FUTURE_RESEARCH,
} from '@/domain/research/types';
import { AtlasRadarChart } from '@/components/atlas/charts';
import type { RadarSeries } from '@/components/atlas/charts';

function CapabilityRadar({ scores, name }: { scores: { domain: string; score: number }[], name: string }) {
  const series: RadarSeries[] = [
    {
      label: name,
      values: scores.reduce((acc, curr) => ({ ...acc, [curr.domain]: curr.score }), {}),
    }
  ];

  return (
    <div className="flex-1 flex items-center justify-center min-h-[300px]">
      <AtlasRadarChart 
        data={series}
        size={300}
        levels={3}
        showAxisLabels={true}
        showGridLabels={false}
        className="mx-auto"
      />
    </div>
  );
}

const STATUS_VARIANT: Record<string, 'default' | 'accent' | 'outline'> = {
  research: 'accent',
  planned: 'default',
  future: 'outline',
};

export default function Research() {
  const genomeRef = useRef(null);
  const genomeInView = useInView(genomeRef, { once: false, margin: '-80px' });
  const aemRef = useRef(null);
  const aemInView = useInView(aemRef, { once: false, margin: '-80px' });
  const evolutionRef = useRef(null);
  const evolutionInView = useInView(evolutionRef, { once: false, margin: '-80px' });

  return (
    <motion.div variants={pageCrossfade} initial="initial" animate="animate" exit="exit">
      <PageHero
        eyebrow="Atlas Research"
        title="Evidence-driven"
        accent="evaluation science."
        description="The Atlas Evaluation Methodology, Capability Genome, and the research agenda shaping how we measure AI systems."
      />

      {/* Capability Genome */}
      <section ref={genomeRef} className="px-6 pb-32 max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={genomeInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
          className="text-center mb-16"
        >
          <Heading as="h3" accent="Genome">
            Capability
          </Heading>
          <p className="mt-4 text-sm text-white/30 max-w-lg mx-auto">
            Multi-dimensional capability profiles — the fingerprint of every model in the Atlas registry.
          </p>
        </motion.div>

        <motion.div
          variants={stagger(0.08, 0)}
          initial="hidden"
          animate={genomeInView ? 'visible' : 'hidden'}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          {AI_MODELS.slice(0, 3).map((model) => (
            <motion.div key={model.id} variants={fadeUp}>
              <Card hover className="!p-6 h-full">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h4 className="text-sm font-semibold text-white">{model.name}</h4>
                    <p className="text-xs text-white/25">{model.provider}</p>
                  </div>
                  <Badge variant="outline">v{model.profile.profileVersion}</Badge>
                </div>
                <CapabilityRadar scores={model.profile.capabilities} name={model.name} />
                <div className="mt-4 grid grid-cols-2 gap-1">
                  {model.profile.capabilities.slice(0, 4).map((cap) => (
                    <div key={cap.domain} className="flex justify-between text-xs">
                      <span className="text-white/25">{cap.domain}</span>
                      <span className="text-white/50">{cap.score.toFixed(1)}</span>
                    </div>
                  ))}
                </div>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* AEM Flow */}
      <section ref={aemRef} className="px-6 pb-32 max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={aemInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
          className="text-center mb-12"
        >
          <h3 className="text-xs tracking-[0.2em] uppercase text-white/20 mb-3">
            Atlas Evaluation Methodology
          </h3>
          <p className="text-sm text-white/30 max-w-lg mx-auto">
            Four stages from raw execution to verified capability reporting.
          </p>
        </motion.div>

        <motion.div
          variants={stagger(0.1, 0)}
          initial="hidden"
          animate={aemInView ? 'visible' : 'hidden'}
          className="space-y-3"
        >
          {AEM_STAGES.map((stage, i) => (
            <motion.div key={stage.id} variants={fadeUp}>
              <Card className="flex items-start gap-6 !p-5">
                <span className="text-3xl font-serif italic text-white/10 shrink-0">
                  {stage.order}
                </span>
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-white mb-1">{stage.name}</h4>
                  <p className="text-sm text-white/30 leading-relaxed">{stage.description}</p>
                </div>
                {i < AEM_STAGES.length - 1 && (
                  <ArrowRight className="w-4 h-4 text-white/10 shrink-0 hidden md:block mt-1" />
                )}
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* Capability Taxonomy */}
      <section className="px-6 pb-32 max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false, margin: '-80px' }}
          transition={{ duration: 0.7 }}
          className="text-center mb-12"
        >
          <h3 className="text-xs tracking-[0.2em] uppercase text-white/20 mb-3">
            Capability Taxonomy
          </h3>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {CAPABILITY_TAXONOMY.map((level, i) => (
            <motion.div
              key={level.domain}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false }}
              transition={{ duration: 0.5, delay: i * 0.05 }}
            >
              <CardFlip minHeight="h-[340px]">
                <CardFlip.Front>
                  <div className="h-full p-5 flex flex-col justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-white mb-2">{level.domain}</h4>
                      <p className="text-xs text-white/25 mb-4 leading-relaxed">{level.description}</p>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-auto">
                      {level.capabilities.map((cap) => (
                        <Badge key={cap}>{cap}</Badge>
                      ))}
                    </div>
                  </div>
                </CardFlip.Front>
                <CardFlip.Back
                  title={level.domain}
                  description={level.details}
                  features={level.benchmarks}
                  actionLabel="Explore Domain →"
                />
              </CardFlip>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Benchmark Evolution */}
      <section ref={evolutionRef} className="px-6 pb-32 max-w-3xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={evolutionInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
          className="text-center mb-12"
        >
          <h3 className="text-xs tracking-[0.2em] uppercase text-white/20 mb-3">
            Benchmark Evolution
          </h3>
          <p className="text-sm text-white/30">The Atlas platform roadmap.</p>
        </motion.div>

        <div className="relative pl-8 border-l border-white/[0.06] space-y-8">
          {ATLAS_EVOLUTION.map((phase, i) => (
            <motion.div
              key={phase.version}
              initial={{ opacity: 0, x: -20 }}
              animate={evolutionInView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="relative"
            >
              <div className="absolute -left-[calc(2rem+1px)] top-1 w-3 h-3 rounded-full border-2 border-white/[0.04]" style={{ background: 'var(--color-accent)', opacity: 0.6 }} />
              <Card className="!p-5">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-xs font-mono text-accent/60">v{phase.version}</span>
                  <span className="text-sm font-semibold text-white">{phase.name}</span>
                  <Badge variant="outline">{phase.focus}</Badge>
                </div>
                <p className="text-xs text-white/30 leading-relaxed">{phase.description}</p>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Future Directions */}
      <section className="px-6 pb-40 max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false }}
          transition={{ duration: 0.7 }}
          className="text-center mb-12"
        >
          <Heading as="h3" accent="Directions">
            Future Research
          </Heading>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {FUTURE_RESEARCH.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false }}
              transition={{ duration: 0.5, delay: i * 0.06 }}
            >
              <CardFlip minHeight="h-[340px]">
                <CardFlip.Front>
                  <div className="group h-full p-5 flex flex-col justify-between">
                    <div>
                      <div className="flex items-start justify-between mb-3">
                        <h4 className="text-sm font-semibold text-white">{item.title}</h4>
                        <Badge variant={STATUS_VARIANT[item.status]}>{item.status}</Badge>
                      </div>
                      <p className="text-xs text-white/30 leading-relaxed">{item.description}</p>
                    </div>
                  </div>
                </CardFlip.Front>
                <CardFlip.Back
                  title={item.title}
                  description={item.details}
                  features={item.milestones}
                  actionLabel="Read Research →"
                />
              </CardFlip>
            </motion.div>
          ))}
        </div>
      </section>
    </motion.div>
  );
}
