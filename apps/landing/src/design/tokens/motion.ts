export const MotionTokens = {
  durations: {
    heading: 1000,
    section: 1200,
    fast: 300,
    base: 500,
    slow: 800,
  },
  stagger: {
    fast: 50,
    base: 100,
    slow: 150,
  },
  easing: {
    default: [0.16, 1, 0.3, 1], // ease-out-expo
    bounce: [0.34, 1.56, 0.64, 1],
    smooth: [0.4, 0, 0.2, 1],
  },
  scrambleSpeed: 1,
} as const;
