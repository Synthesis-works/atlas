export type GlassVariant = 'default' | 'glass' | 'liquid';

export interface WidgetLayoutState {
  x: number;
  y: number;
  width: number;
  height: number;
  visible: boolean;
  collapsed: boolean;
  minimized: boolean;
  dragging: boolean;
  focused: boolean;
  locked: boolean;
}
