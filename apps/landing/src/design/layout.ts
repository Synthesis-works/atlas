/**
 * Spacing, padding, and container tokens for the workspace layout engine.
 * Ensures consistent grid layouts, padding, and floating dock safe zones.
 */
export const LayoutTokens = {
  // Page container max width and padding
  // No py/pb here; vertical spacing is handled at the page/layout level
  container: 'w-full max-w-container-max mx-auto px-page-mobile md:px-page-tablet xl:px-page-desktop',

  // Vertical spacing between blocks (Workspace Header -> Hero -> Analytics -> Operations)
  sectionGap: 'space-y-section',

  // Core grid system (4 col mobile, 8 col tablet, 12 col desktop)
  grid: 'grid grid-cols-4 md:grid-cols-8 xl:grid-cols-12',

  // Spacing between cards inside dynamic grid rows (12-column grid gutters)
  gridGap: 'gap-4 md:gap-5 xl:gap-6', // Tailwind map to 16px, 20px, 24px

  // Standard inner padding for cards and sections
  cardPadding: 'p-6',

  // Standard gap for KPI groups
  kpiGap: 'gap-6',

  // Spacing for control toolbars
  toolbarGap: 'gap-3',
};
