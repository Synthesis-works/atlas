# Atlas Liquid Glass System v1.0 — Governance Contract

## Philosophy
Glass communicates hierarchy, state, and interaction depth. It should never be used as pure decoration.

---

## 1. Visual Hierarchy Usage Rules
| Component | Appropriate Usage |
| :--- | :--- |
| `GlassSurface(variant="default")` | Basic content panels, grids, and dashboard content outlines. |
| `GlassSurface(variant="glass")` | KPI cards, analytics dashboard elements, sidebars, and normal drawers. |
| `GlassSurface(variant="liquid")` | Interactive floating panels, context menus, command palettes, and custom popovers. |
| `LiquidGlassCard` | Strictly floating, user-draggable workspace widgets. Never apply to standard charts, grids, or static layout panels. |
| `GlassGlow` | Highlight sweeps triggered by asynchronous events (e.g. run completed, new assistant messages). |

---

## 2. Animation & Interaction States
Every glass component should align with the following unified interaction states:
`Idle` ➔ `Hover` (specular glare tracks cursor, subtle 1.01x scale lift) ➔ `Focused` (visible ring indicator, keyboard positioning ready) ➔ `Pressed` (slight scale depress) ➔ `Dragging` (lift scaling, soft shadow expansion, squash/stretch deformation) ➔ `Settling` (spring velocity decay, grid snapping) ➔ `Idle`.

---

## 3. Performance Budgets
* **Draggables Limit**: Max 6 active `LiquidGlassCard` elements on screen.
* **Active RAF loops**: Max 1 loop per active draggable widget. All RAF loops are paused when `document.visibilityState === "hidden"`.
* **Backdrop Blur Limit**: Max `32px` to prevent GPU rendering degradation.
* **Shadow Layers**: Max 4 layered inset/outset shadows to preserve frame rendering speeds.

---

## 4. Implementation Rules for Developers and AI Coding Agents
* **Do Not** bypass `GlassSurface` to build custom styled glass elements.
* **Do Not** duplicate glare tracking code; reuse the `useGlassGlare` hook.
* **Do Not** hardcode colors, blurs, or shadows; resolve them from `tokens.ts` and Tailwind configurations.
* **Do Not** inject arbitrary requestAnimationFrame loops outside `LiquidGlassCard`.
* **Do** respect layout coordinates and synchronize positions via `workspaceStore.tsx`.
* **Do** respect the `prefers-reduced-motion` settings in all physics equations.
