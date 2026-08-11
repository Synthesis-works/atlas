/**
 * Open Source Page
 *
 * Atlas open-source philosophy, repositories, contribution guide,
 * and community resources.
 */

import { motion } from 'framer-motion';
import { GitBranch, Star, ExternalLink, Heart, FolderGit } from 'lucide-react';
import { pageCrossfade, fadeUp, stagger } from '@/lib/motion';
import { PageHero } from '@/components/layout/PageHero';
import { Card, Badge } from '@/design/primitives';
import { CardFlip } from '@/components/ui/CardFlip';

const REPOSITORIES = [
  {
    name: 'atlas-core',
    description: 'The core evaluation engine — benchmark execution, scoring, and reporting.',
    stars: 2847,
    language: 'Python',
    license: 'Apache-2.0',
    tags: ['core', 'engine'],
    details: 'The core computation engine orchestrating test sandboxes, capturing raw model answers, and computing statistical scoring metrics.',
    bullets: ['Isolated Docker execution', 'Rule-based & LLM judges', 'Verified score outputs'],
  },
  {
    name: 'atlas-benchmarks',
    description: 'Official benchmark registry — MMLU, HumanEval, GSM8K, and community benchmarks.',
    stars: 1203,
    language: 'YAML',
    license: 'MIT',
    tags: ['benchmarks', 'registry'],
    details: 'The official public index of standard benchmark configurations, prompts, and evaluation datasets, all defined declaratively.',
    bullets: ['MMLU, HumanEval, GSM8K', 'Custom YAML authoring', 'Public pull requests welcomed'],
  },
  {
    name: 'atlas-cli',
    description: 'Command-line interface for running evaluations, publishing benchmarks, and managing workspaces.',
    stars: 891,
    language: 'Go',
    license: 'Apache-2.0',
    tags: ['cli', 'tooling'],
    details: 'A fast command-line helper for running offline evaluations, local debugging, and publishing benchmarks from CI/CD pipelines.',
    bullets: ['Zero-dependency binary', 'Pre-flight prompt testing', 'Local JSON reporting'],
  },
  {
    name: 'atlas-sdk',
    description: 'Client SDKs for Python and TypeScript — integrate Atlas into your pipeline.',
    stars: 654,
    language: 'TypeScript',
    license: 'MIT',
    tags: ['sdk', 'integration'],
    details: 'Clean client SDKs to easily integrate evaluation runs, custom scoring, and dataset fetching into your python or JS codebases.',
    bullets: ['Async API calls', 'Typing safety', 'Automatic prompt hydration'],
  },
  {
    name: 'atlas-adapters',
    description: 'Reference adapter implementations for OpenAI, Anthropic, Google, and local runtimes.',
    stars: 432,
    language: 'Python',
    license: 'Apache-2.0',
    tags: ['adapters', 'integrations'],
    details: 'Pluggable routing adapters that translate standard model inputs and outputs across all major cloud providers and local engines.',
    bullets: ['OpenAI & Anthropic APIs', 'Ollama & vLLM routing', 'Rate limit & retry handling'],
  },
  {
    name: 'atlas-ui',
    description: 'The Atlas Workspace UI — React components and design system.',
    stars: 318,
    language: 'TypeScript',
    license: 'MIT',
    tags: ['ui', 'design-system'],
    details: 'A gorgeous, responsive React-based admin control center for browsing evaluations, editing datasets, and viewing reports.',
    bullets: ['Tailwind CSS styled', 'Lucide icon integration', 'Interactive chart visualizer'],
  },
];

const PRINCIPLES = [
  {
    title: 'Open by Default',
    description: 'Core evaluation infrastructure is open source. Transparency is not optional.',
    details: 'We believe model evaluation must be public science. The entire execution scheduler, test orchestrator, and scoring judges are available to inspect, run, and self-host.',
    bullets: ['Apache-2.0 core license', 'Self-hostable runtimes', 'Public pull request review'],
  },
  {
    title: 'Community Benchmarks',
    description: 'Anyone can publish versioned benchmarks. The registry grows with the community.',
    details: 'No single centralized lab owns the benchmark standard. Anyone can author, version, and submit a test set via a simple YAML schema, making it live on the global registry.',
    bullets: ['YAML benchmark schema', 'Semantic versioning support', 'Federated registry system'],
  },
  {
    title: 'Reproducible Science',
    description: 'Every evaluation artifact is inspectable. Hidden tests stay hidden; methodology does not.',
    details: 'Every score published on Atlas can be validated locally. We generate cryptographic verification checksums and preserve all raw model answers and prompt templates.',
    bullets: ['Verification hashes', 'Immutable response archives', 'Auditable judge templates'],
  },
  {
    title: 'No Lock-In',
    description: 'Adapters are pluggable. Models, judges, and storage backends are replaceable.',
    details: 'Never get stuck with a single vendor. You can plug in local models, configure private database storage, and swap out scoring judge strategies in a few lines of code.',
    bullets: ['Universal adapter APIs', 'SQL & Redis backends', 'Pluggable judge layers'],
  },
];

export default function OpenSource() {
  return (
    <motion.div variants={pageCrossfade} initial="initial" animate="animate" exit="exit">
      <PageHero
        eyebrow="Open Source"
        title="Built in the open,"
        accent="for the community."
        description="Atlas core infrastructure, benchmark registry, CLI, SDK, and adapters — all open source. Evaluation should be a public good."
        cta={
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 mt-8 px-6 py-3 rounded-full liquid-glass text-sm text-white/70 hover:text-white transition-colors"
          >
            <FolderGit className="w-4 h-4" />
            View on GitHub
            <ExternalLink className="w-3 h-3 text-white/30" />
          </a>
        }
      />

      {/* Principles */}
      <section className="px-6 pb-32 max-w-5xl mx-auto">
        <motion.h3
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: false }}
          className="text-xs tracking-[0.2em] uppercase text-white/20 mb-8 text-center"
        >
          Open Source Principles
        </motion.h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {PRINCIPLES.map((p, i) => (
            <motion.div
              key={p.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
            >
              <CardFlip minHeight="h-[340px]">
                <CardFlip.Front>
                  <div className="h-full p-5 text-center flex flex-col items-center justify-center">
                    <Heart className="w-5 h-5 text-accent/60 mx-auto mb-3" />
                    <h4 className="text-sm font-semibold text-white mb-2">{p.title}</h4>
                    <p className="text-xs text-white/25 leading-relaxed">{p.description}</p>
                  </div>
                </CardFlip.Front>
                <CardFlip.Back
                  title={p.title}
                  description={p.details}
                  features={p.bullets}
                  actionLabel="Learn More →"
                />
              </CardFlip>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Repositories */}
      <section className="px-6 pb-32 max-w-5xl mx-auto">
        <motion.h3
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: false }}
          className="text-xs tracking-[0.2em] uppercase text-white/20 mb-8 text-center"
        >
          Repositories
        </motion.h3>

        <motion.div
          variants={stagger(0.06, 0)}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: false, margin: '-80px' }}
          className="grid grid-cols-1 md:grid-cols-2 gap-4"
        >
          {REPOSITORIES.map((repo) => (
            <motion.div key={repo.name} variants={fadeUp}>
              <CardFlip minHeight="h-[350px]">
                <CardFlip.Front>
                  <div className="group h-full p-6 cursor-pointer flex flex-col justify-between">
                    <div>
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <FolderGit className="w-4 h-4 text-white/30" />
                          <h4 className="text-sm font-semibold text-white group-hover:text-accent-hover transition-colors">
                            {repo.name}
                          </h4>
                        </div>
                        <ExternalLink className="w-3.5 h-3.5 text-white/10 group-hover:text-white/30 transition-colors" />
                      </div>
                      <p className="text-xs text-white/30 leading-relaxed mb-4">{repo.description}</p>
                    </div>
                    <div>
                      <div className="flex flex-wrap gap-1.5 mb-4">
                        {repo.tags.map((tag) => (
                          <Badge key={tag}>{tag}</Badge>
                        ))}
                      </div>
                      <div className="flex items-center gap-4 text-xs text-white/15">
                        <span className="flex items-center gap-1">
                          <Star className="w-3 h-3" />
                          {repo.stars.toLocaleString()}
                        </span>
                        <span className="flex items-center gap-1">
                          <GitBranch className="w-3 h-3" />
                          {repo.language}
                        </span>
                        <span>{repo.license}</span>
                      </div>
                    </div>
                  </div>
                </CardFlip.Front>
                <CardFlip.Back
                  title={repo.name}
                  description={repo.details}
                  features={repo.bullets}
                  actionLabel="View Repository →"
                />
              </CardFlip>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* Contribute */}
      <section className="px-6 pb-40 max-w-3xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false }}
          transition={{ duration: 0.7 }}
        >
          <Card className="!p-10">
            <h3 className="text-xs tracking-[0.2em] uppercase text-accent/60 mb-4">
              Contribute
            </h3>
            <h4 className="text-2xl font-semibold text-white mb-4 tracking-tight">
              Join the evaluation revolution
            </h4>
            <p className="text-sm text-white/30 leading-relaxed mb-6 max-w-md mx-auto">
              Publish benchmarks, improve judges, build adapters, or enhance the core engine.
              Every contribution makes AI evaluation more transparent and reproducible.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Badge variant="accent">Good First Issues</Badge>
              <Badge variant="outline">Benchmark Authors</Badge>
              <Badge variant="outline">Adapter Developers</Badge>
            </div>
          </Card>
        </motion.div>
      </section>
    </motion.div>
  );
}
