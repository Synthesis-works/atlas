/**
 * Documentation Page — Premium documentation portal
 *
 * Large search, Quick Start grid, Architecture / Tutorials / API / Guides
 * sections with a table-of-contents sidebar.
 * Refactored to cover the full page with the watermark background,
 * implement active scroll tracking in the sidebar, and fix search focus rings.
 */

import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import { Search, BookOpen, Layers, Code, FileText, Rocket, ChevronRight } from 'lucide-react';
import { pageCrossfade, fadeUp, stagger } from '@/lib/motion';
import { PageHero } from '@/components/layout/PageHero';
import { Card, Badge } from '@/design/primitives';

const QUICK_START = [
  {
    icon: Rocket,
    title: 'Install Atlas CLI',
    description: 'Get the command-line tool and authenticate with your workspace.',
    href: '#api',
  },
  {
    icon: BookOpen,
    title: 'Run Your First Evaluation',
    description: 'Execute a benchmark against a registered model in under five minutes.',
    href: '#tutorials',
  },
  {
    icon: Layers,
    title: 'Understand the Architecture',
    description: 'Seven layers, five principles, and the adapter pattern.',
    href: '#architecture',
  },
  {
    icon: Code,
    title: 'Publish a Benchmark',
    description: 'Package and publish a versioned benchmark to the registry.',
    href: '#guides',
  },
];

const DOC_SECTIONS = [
  {
    id: 'architecture',
    title: 'Architecture',
    icon: Layers,
    items: [
      { title: 'Platform Overview', description: 'The seven-layer architecture and how components interact.' },
      { title: 'Adapter Pattern', description: 'Standardized interface to external AI systems.' },
      { title: 'Data Flow', description: 'From benchmark execution through evaluation to reporting.' },
      { title: 'Deployment Models', description: 'Self-hosted, cloud, and hybrid deployment options.' },
    ],
  },
  {
    id: 'tutorials',
    title: 'Tutorials',
    icon: BookOpen,
    items: [
      { title: 'Getting Started', description: 'Set up your workspace and run your first evaluation.' },
      { title: 'Custom Benchmarks', description: 'Author, package, and publish your own benchmarks.' },
      { title: 'Model Registration', description: 'Register models and configure adapter connections.' },
      { title: 'Report Generation', description: 'Generate and verify evaluation reports.' },
    ],
  },
  {
    id: 'api',
    title: 'API Reference',
    icon: Code,
    items: [
      { title: 'REST API', description: 'Full REST API for benchmarks, evaluations, and reports.' },
      { title: 'Webhooks', description: 'Event-driven notifications for evaluation lifecycle.' },
      { title: 'Authentication', description: 'API keys, OAuth, and workspace-scoped tokens.' },
      { title: 'Rate Limits', description: 'Usage tiers and rate limiting policies.' },
    ],
  },
  {
    id: 'guides',
    title: 'Guides',
    icon: FileText,
    items: [
      { title: 'Benchmark Schema', description: 'The atlas_benchmark.zip artifact structure.' },
      { title: 'Judge Strategies', description: 'Hidden tests, exact match, LLM-as-judge, and consensus.' },
      { title: 'Capability Taxonomy', description: 'Mapping scores to multi-dimensional profiles.' },
      { title: 'Best Practices', description: 'Reproducibility, transparency, and evidence-driven evaluation.' },
    ],
  },
];

export default function Documentation() {
  const [query, setQuery] = useState('');
  const [searchFocused, setSearchFocused] = useState(false);
  const [activeSectionId, setActiveSectionId] = useState('');

  const filteredSections = query.trim()
    ? DOC_SECTIONS.map((section) => ({
        ...section,
        items: section.items.filter(
          (item) =>
            item.title.toLowerCase().includes(query.toLowerCase()) ||
            item.description.toLowerCase().includes(query.toLowerCase()),
        ),
      })).filter((section) => section.items.length > 0)
    : DOC_SECTIONS;

  const TOC = filteredSections.map((s) => ({ id: s.id, label: s.title }));

  // Scroll spy active section highlighting
  useEffect(() => {
    if (filteredSections.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntry = entries.find((entry) => entry.isIntersecting);
        if (visibleEntry) {
          setActiveSectionId(visibleEntry.target.id);
        }
      },
      {
        rootMargin: '-120px 0px -55% 0px',
        threshold: 0.1,
      }
    );

    filteredSections.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [filteredSections]);

  return (
    <motion.div variants={pageCrossfade} initial="initial" animate="animate" exit="exit" className="relative min-h-screen">


      <div className="relative z-10">
        <PageHero
          eyebrow="Documentation"
          title="Everything you need"
          accent="to evaluate with Atlas."
          description="Architecture guides, tutorials, API reference, and best practices — all in one place."
        />

        {/* Search */}
        <section className="px-6 pb-16 max-w-2xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <div className={`p-1.5 flex items-center gap-3 rounded-2xl transition-all duration-300 border ${
              searchFocused 
                ? 'border-[#4F8CFF]/50 shadow-[0_0_20px_rgba(79,140,255,0.18)] bg-white/[0.05]' 
                : 'border-white/10 hover:border-white/20 bg-white/[0.02]'
            }`}>
              <Search className={`w-5 h-5 ml-3.5 shrink-0 transition-colors duration-300 ${searchFocused ? 'text-[#4F8CFF]' : 'text-white/20'}`} />
              <input
                type="search"
                placeholder="Search documentation…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onFocus={() => setSearchFocused(true)}
                onBlur={() => setSearchFocused(false)}
                className="flex-1 bg-transparent text-sm text-[#F8FAFC] placeholder:text-white/20 outline-none py-3"
              />
              {query && (
                <Badge variant="outline" className="mr-2.5">
                  {filteredSections.reduce((n, s) => n + s.items.length, 0)} results
                </Badge>
              )}
            </div>
          </motion.div>
        </section>

        {/* Quick Start */}
        <section className="px-6 pb-32 max-w-5xl mx-auto">
          <motion.h3
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: false }}
            className="text-xs tracking-[0.2em] uppercase text-white/20 mb-8 text-center"
          >
            Quick Start
          </motion.h3>

          <motion.div
            variants={stagger(0.08, 0)}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: false, margin: '-80px' }}
            className="grid grid-cols-1 md:grid-cols-2 gap-4"
          >
            {QUICK_START.map((item) => (
              <motion.a key={item.title} href={item.href} variants={fadeUp}>
                <Card hover className="flex items-start gap-4 !p-5 h-full group cursor-pointer border border-white/5 hover:border-white/15">
                  <div className="liquid-glass rounded-xl p-3 shrink-0">
                    <item.icon className="w-5 h-5 text-[#4F8CFF]/85" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-white mb-1 group-hover:text-[#4F8CFF] transition-colors">
                      {item.title}
                    </h4>
                    <p className="text-xs text-white/30 leading-relaxed">{item.description}</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-white/10 ml-auto shrink-0 mt-1 group-hover:text-white/30 transition-colors" />
                </Card>
              </motion.a>
            ))}
          </motion.div>
        </section>

        {/* Main content + TOC */}
        <section className="px-6 pb-40 max-w-6xl mx-auto">
          <div className="flex gap-12">
            {/* TOC sidebar (sticky) */}
            {filteredSections.length > 0 && (
              <aside className="hidden lg:block w-48 shrink-0 sticky top-32 self-start z-10">
                <p className="text-xs tracking-[0.2em] uppercase text-white/20 mb-4 pl-3">On this page</p>
                <nav className="flex flex-col gap-1 border-l border-white/5">
                  {TOC.map((item) => {
                    const isActive = activeSectionId === item.id;
                    return (
                      <a
                        key={item.id}
                        href={`#${item.id}`}
                        className={`text-xs transition-all duration-200 py-1.5 pl-3 border-l -ml-[1px] ${
                          isActive
                            ? 'text-white border-[#4F8CFF] font-semibold bg-white/[0.02]'
                            : 'text-white/30 border-transparent hover:text-white/60'
                        }`}
                      >
                        {item.label}
                      </a>
                    );
                  })}
                </nav>
              </aside>
            )}

            {/* Doc sections */}
            <div className="flex-1 space-y-16">
              {filteredSections.map((section) => (
                <div key={section.id} id={section.id} className="scroll-mt-24">
                  <div className="flex items-center gap-3 mb-6">
                    <section.icon className="w-5 h-5 text-[#4F8CFF]/70" />
                    <h3 className="text-lg font-semibold text-white">{section.title}</h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {section.items.map((item) => (
                      <Card key={item.title} hover className="group !p-5 cursor-pointer border border-white/5 hover:border-[#4F8CFF]/30">
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="text-sm font-medium text-white mb-1 group-hover:text-[#4F8CFF] transition-colors">
                              {item.title}
                            </h4>
                            <p className="text-xs text-white/30 leading-relaxed">{item.description}</p>
                          </div>
                          <ChevronRight className="w-4 h-4 text-white/10 shrink-0 mt-0.5 group-hover:text-white/30 transition-colors" />
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              ))}

              {filteredSections.length === 0 && (
                <Card className="!p-10 text-center border border-white/5">
                  <p className="text-sm text-white/30">No results for &ldquo;{query}&rdquo;</p>
                </Card>
              )}
            </div>
          </div>
        </section>
      </div>
    </motion.div>
  );
}
