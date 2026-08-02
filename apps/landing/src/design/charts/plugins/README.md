# Atlas Visualization System — Plugins Directory

This directory reserves space for v2 and v3 visualization plugins (such as Treemap, Sankey, Timeline extensions, Network Graphs, Parallel Coordinates, Violin Plots, and Chord Diagrams).

## Creating a Plugin
1. Add a subfolder under `plugins/<PluginName>/`
2. Implement your component utilizing `ChartContainer` and `ChartTheme` tokens.
3. Register the key in `src/design/charts/registry.ts`.
