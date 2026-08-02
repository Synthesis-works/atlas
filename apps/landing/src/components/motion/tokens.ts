export const MotionTokens = {
  durations: {
    heading: 1000,       // 900-1200ms
    sectionTitle: 700,   // 600-800ms
    status: 600,         // 500-700ms
    fade: 0.5,           // seconds for framer-motion
  },
  spacing: {
    yOffset: 8,          // Move upward 8px
  },
  stagger: {
    baseDelayMs: 150,    // 150ms between staggered items
  },
  presets: {
    default: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#@$%&*',
    terminal: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_></\\',
    uppercase: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    numbers: '0123456789',
    binary: '01',
    hex: '0123456789ABCDEF',
  }
};

export type ScramblePreset = keyof typeof MotionTokens.presets | 'custom';
export type ReplayStrategy = 'once' | 'replayOnRoute' | 'replayOnVisibility';
