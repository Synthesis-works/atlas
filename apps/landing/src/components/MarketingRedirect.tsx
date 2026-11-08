/**
 * Marketing pages moved to the Synthesis Works organisation site.
 *
 * Old links and bookmarks (and the retired in-app marketing navbar) still point
 * at these paths, so forward them to the same page on the other origin instead
 * of leaving the visitor on a loader. A full page navigation is correct here:
 * the two sites share no routing.
 */

import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { PageLoader } from '@/components/layout/PageLoader';
import { synthesisWorksUrl } from '@/config/site';

export function MarketingRedirect() {
  const { pathname, search, hash } = useLocation();

  useEffect(() => {
    window.location.replace(synthesisWorksUrl(`${pathname}${search}${hash}`));
  }, [pathname, search, hash]);

  return <PageLoader />;
}
