/**
 * Cross-site links.
 *
 * Atlas (this app) and Synthesis Works (the organisation site) are separate
 * deployments on separate origins. They share no routing, no session and no
 * cookies: the only coupling is the absolute URL below, which means a visitor
 * can go straight to Atlas without ever passing through the organisation site.
 */
const DEFAULT_SYNTHESIS_WORKS_URL = 'https://synthesis-works.xyz';

export const SYNTHESIS_WORKS_URL = (
  (import.meta.env.VITE_SYNTHESIS_WORKS_URL as string | undefined) || DEFAULT_SYNTHESIS_WORKS_URL
).replace(/\/+$/, '');

/** Absolute URL on the organisation site, for links and full-page redirects. */
export function synthesisWorksUrl(path = '/'): string {
  return `${SYNTHESIS_WORKS_URL}${path.startsWith('/') ? path : `/${path}`}`;
}
