# Atlas Motion System

The Atlas Motion System is a centralized, reusable animation architecture designed to make the interface feel like an intelligent operating system progressively decoding information. 

## Philosophy
The goal is **not** to add flashy or chaotic animations. 
The goal is a subtle, elegant "boot sequence" feel that introduces information systematically.

We achieve this by combining:
1. **Framer Motion**: Smooth 0 → 1 opacity fades and upward spatial movement.
2. **Anime.js (v4)**: High-performance `scrambleText` utility for the text decoding effect.

## Component Hierarchy

The system provides three primary wrappers that should be used across all pages instead of raw HTML heading tags:

- `<ScrambleHeading>` — Replaces `<h1>` (Page Hero headings). Duration: 900–1200ms.
- `<ScrambleSectionTitle>` — Replaces `<h2>`, `<h3>` (Section headings). Duration: 600–800ms.
- `<ScrambleStatus>` — Replaces `<span>`, `<div>` (Badges, stats, tight metrics). Duration: 500–700ms.

These wrappers are built on top of a low-level `<ScrambleText>` primitive, which internally uses the `useScramble` hook to orchestrate Anime.js.

## Global Staggering (`MotionProvider`)

To give pages a cohesive "booting" feel, headings should not scramble simultaneously. They should stagger.
Instead of manually hardcoding delays across disconnected components on a page, Atlas uses a `<MotionProvider>`.

Wrap your top-level layout (e.g., `WorkspaceLayout`) in `<MotionProvider>`. 
Any `Scramble*` component inside will automatically register itself and receive an incrementally increasing delay (0ms, 150ms, 300ms, etc.), guaranteeing a clean waterfall effect down the page.

## Animation Controls

Every wrapper exposes the following animation controls via props:

```tsx
interface ScrambleTextProps {
  text: string;               // The text to scramble into
  duration?: number;          // Custom duration in ms
  delay?: number;             // Override the automatic stagger delay
  speed?: number;             // Playback rate multiplier
  chars?: string;             // Custom character set
  preset?: ScramblePreset;    // 'terminal' | 'uppercase' | 'numbers' | 'binary' | 'hex' | 'default'
  once?: boolean;             // Whether to only play once (legacy prop)
  replayStrategy?: 'once' | 'replayOnRoute' | 'replayOnVisibility';
  disabled?: boolean;         // Force disable the animation
  className?: string;         // Tailwind classes
  children?: ReactNode;       // Optional React children appended after the scrambled text
}
```

## Replay Strategies
You can control when the animation retriggers:
- `once` (Default): Animates once when it scrolls into view and never again.
- `replayOnRoute`: Animates once per route. If the user navigates away and back, it replays.
- `replayOnVisibility`: Animates every time the element enters the viewport. Best for below-the-fold metrics.

## Accessibility
The system fully respects the OS-level `prefers-reduced-motion` setting. 
If reduced motion is detected:
- Anime.js scrambling is bypassed entirely.
- The text renders statically.
- Framer Motion degrades the spatial movement to a simple, instantaneous fade-in.

## Implementation Details
- **IntersectionObserver**: Animations only trigger when the component enters the viewport.
- **Client-only**: Anime.js instances are safely scoped inside `useEffect` to prevent React hydration errors during SSR.
- **Cleanup**: The `useScramble` hook guarantees Anime.js timelines are paused and Observers disconnected when the component unmounts.
