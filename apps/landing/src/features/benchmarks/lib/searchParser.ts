import type { Benchmark } from '@/domain/benchmarks/types';

export interface FilterCriteria {
  textQuery: string;
  status?: string;
  category?: string;
  tag?: string;
  author?: string;
  minVerification?: number;
}

export function parseSearchQuery(query: string): FilterCriteria {
  const criteria: FilterCriteria = { textQuery: '' };
  const tokens = query.trim().split(/\s+/);
  const textParts: string[] = [];

  tokens.forEach((token) => {
    if (token.includes(':')) {
      const [key, val] = token.split(':');
      const lowerKey = key.toLowerCase();
      const lowerVal = val.toLowerCase();

      if (lowerKey === 'status') criteria.status = lowerVal;
      else if (lowerKey === 'category' || lowerKey === 'cat') criteria.category = lowerVal;
      else if (lowerKey === 'tag' || lowerKey === 'tags') criteria.tag = lowerVal;
      else if (lowerKey === 'author') criteria.author = lowerVal;
      else if (lowerKey === 'verified' && lowerVal === 'true') criteria.minVerification = 100;
    } else {
      textParts.push(token);
    }
  });

  criteria.textQuery = textParts.join(' ').toLowerCase();
  return criteria;
}

export function filterBenchmarksByQuery(benchmarks: Benchmark[], query: string): Benchmark[] {
  if (!query.trim()) return benchmarks;

  const criteria = parseSearchQuery(query);

  return benchmarks.filter((bm) => {
    if (criteria.status && bm.status.toLowerCase() !== criteria.status) return false;
    if (criteria.category && bm.category?.toLowerCase() !== criteria.category) return false;
    if (criteria.tag && (!bm.tags || !bm.tags.some((t) => t.toLowerCase().includes(criteria.tag!)))) return false;
    if (criteria.author && (!bm.author || !bm.author.toLowerCase().includes(criteria.author))) return false;
    if (criteria.minVerification && (bm.verificationScore === undefined || bm.verificationScore < criteria.minVerification)) return false;

    if (criteria.textQuery) {
      const matchesName = bm.name.toLowerCase().includes(criteria.textQuery);
      const matchesDesc = bm.description?.toLowerCase().includes(criteria.textQuery) ?? false;
      const matchesTag = bm.tags?.some((t) => t.toLowerCase().includes(criteria.textQuery)) ?? false;
      if (!matchesName && !matchesDesc && !matchesTag) return false;
    }

    return true;
  });
}
