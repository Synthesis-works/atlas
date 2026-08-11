/**
 * Intelligence Fabric — the KnowledgeFabric component
 *
 * Renders the Atlas Intelligence Fabric as a persistent canvas visualization.
 * Mounted once per layout; never unmounts on route change. Reads fabricMode
 * from the ExperienceController to switch between cinematic (marketing)
 * and ambient (workspace) behaviour.
 *
 * v1 = solid visual foundation (stable layout, soft glow, calm drift).
 * Physics, mouse parallax, and category accent emphasis are deferred.
 */

import { useEffect, useRef } from 'react';
import { useExperience } from '@/core/ExperienceController';
import {
  FABRIC_NODES,
  FABRIC_EDGES,
  CATEGORY_COLORS,
  CLUSTER_POSITIONS,
  type FabricNode,
} from '@/lib/networkData';

interface NodePosition {
  x: number;
  y: number;
  node: FabricNode;
}

export function KnowledgeFabric() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const positionsRef = useRef<NodePosition[]>([]);
  const animFrameRef = useRef<number>(0);
  const { fabricMode, transitionPhase, prefersReducedMotion } = useExperience();

  /* Initialise node positions within their cluster */
  useEffect(() => {
    const positions: NodePosition[] = FABRIC_NODES.map((node) => {
      const cluster = CLUSTER_POSITIONS[node.category] ?? { cx: 0.5, cy: 0.5 };
      return {
        x: cluster.cx + (Math.random() - 0.5) * 0.15,
        y: cluster.cy + (Math.random() - 0.5) * 0.15,
        node,
      };
    });
    positionsRef.current = positions;
  }, []);

  /* Canvas render loop */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let w = 0;
    let h = 0;
    const dpr = window.devicePixelRatio || 1;

    const resize = () => {
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener('resize', resize);

    const isCinematic = fabricMode === 'cinematic';
    const isTransitioning = transitionPhase !== 'idle';
    const baseAlpha = isCinematic ? 0.6 : 0.25;
    const transitionBoost = isTransitioning ? 1.4 : 1;

    let time = 0;
    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      time += prefersReducedMotion ? 0 : 0.003;

      const positions = positionsRef.current;

      /* Draw edges */
      for (const edge of FABRIC_EDGES) {
        const a = positions.find((p) => p.node.id === edge.source);
        const b = positions.find((p) => p.node.id === edge.target);
        if (!a || !b) continue;

        ctx.beginPath();
        ctx.moveTo(a.x * w, a.y * h);
        ctx.lineTo(b.x * w, b.y * h);
        ctx.strokeStyle = `rgba(255,255,255,${0.04 * transitionBoost})`;
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }

      /* Draw nodes */
      for (const pos of positions) {
        const color = CATEGORY_COLORS[pos.node.category] ?? [255, 255, 255];
        const [r, g, b] = color;

        /* Subtle drift */
        const driftX = prefersReducedMotion ? 0 : Math.sin(time * 0.5 + pos.x * 10) * 3;
        const driftY = prefersReducedMotion ? 0 : Math.cos(time * 0.4 + pos.y * 10) * 3;
        const nx = pos.x * w + driftX;
        const ny = pos.y * h + driftY;
        const radius = pos.node.radius * (isCinematic ? 1 : 0.7) * transitionBoost;

        /* Glow */
        const grad = ctx.createRadialGradient(nx, ny, 0, nx, ny, radius * 4);
        grad.addColorStop(0, `rgba(${r},${g},${b},${baseAlpha * 0.3})`);
        grad.addColorStop(1, `rgba(${r},${g},${b},0)`);
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(nx, ny, radius * 4, 0, Math.PI * 2);
        ctx.fill();

        /* Core dot */
        ctx.beginPath();
        ctx.arc(nx, ny, radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${r},${g},${b},${baseAlpha})`;
        ctx.fill();
      }

      animFrameRef.current = requestAnimationFrame(draw);
    };
    animFrameRef.current = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [fabricMode, transitionPhase, prefersReducedMotion]);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
      aria-hidden="true"
    />
  );
}
