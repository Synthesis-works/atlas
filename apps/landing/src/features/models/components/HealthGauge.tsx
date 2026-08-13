interface GaugeProps {
  value: number;   // 0–100
  label: string;
  color?: string;
  invert?: boolean; // for error rate — lower is better
}

function Arc({ value, color, invert }: { value: number; color: string; invert?: boolean }) {
  const r = 26;
  const cx = 32;
  const cy = 32;
  const circ = 2 * Math.PI * r;
  const pct  = invert ? (100 - value) / 100 : value / 100;
  return (
    <svg width="64" height="64" viewBox="0 0 64 64">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="5" />
      <circle
        cx={cx} cy={cy} r={r}
        fill="none"
        stroke={color}
        strokeWidth="5"
        strokeLinecap="round"
        strokeDasharray={`${circ * pct} ${circ * (1 - pct)}`}
        transform="rotate(-90 32 32)"
        style={{ transition: 'stroke-dasharray 0.8s ease' }}
      />
      <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central"
        fontSize="10" fontWeight="600" fill="white" fontFamily="Inter, sans-serif">
        {invert ? value.toFixed(1) : value.toFixed(0)}
      </text>
    </svg>
  );
}

export function HealthGauge({ value, label, color = '#6366f1', invert }: GaugeProps) {
  return (
    <div className="flex flex-col items-center gap-1.5">
      <Arc value={value} color={color} invert={invert} />
      <span className="text-xs text-white/30 text-center leading-tight">{label}</span>
    </div>
  );
}

interface ModelHealthPanelProps {
  availability: number;
  reliability: number;
  errorRate: number;
  responseQuality: number;
}

export function ModelHealthPanel({ availability, reliability, errorRate, responseQuality }: ModelHealthPanelProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <HealthGauge value={availability}     label="Availability"      color="#22c55e" />
      <HealthGauge value={reliability}      label="Reliability"       color="#6366f1" />
      <HealthGauge value={errorRate}        label="Error Rate"        color="#ef4444" invert />
      <HealthGauge value={responseQuality}  label="Response Quality"  color="#67e8f9" />
    </div>
  );
}
