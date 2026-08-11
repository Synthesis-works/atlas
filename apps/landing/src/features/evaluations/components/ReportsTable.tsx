import React, { memo } from 'react';
import { Database, FileText, Download, FileCode, FileSpreadsheet } from 'lucide-react';
import type { EvaluationReport } from '@/domain/evaluations/types';

interface Props { reports: EvaluationReport[]; }

const FORMAT_COLORS: Record<string, string> = {
  pdf: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
  json: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  csv: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
};

const FORMAT_ICONS: Record<string, React.ReactNode> = {
  pdf: <FileText className="w-3.5 h-3.5 text-rose-400" aria-hidden="true" />,
  json: <FileCode className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />,
  csv: <FileSpreadsheet className="w-3.5 h-3.5 text-blue-400" aria-hidden="true" />,
};

export const ReportsTableComponent: React.FC<Props> = ({ reports }) => (
  <section className="liquid-glass-card rounded-2xl border border-white/10 p-5 space-y-4 flex flex-col flex-1 min-h-0" aria-label="Generated Evaluation Reports Registry">
    {/* Header */}
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
      <div>
        <div className="flex items-center gap-1.5 font-mono text-xs text-white/40 uppercase tracking-wider mb-0.5">
          <Database className="w-3.5 h-3.5 text-accent" aria-hidden="true" />
          <span>Step 5: Manage — Generated Run & Report Registry</span>
        </div>
        <h3 className="text-sm font-semibold text-white tracking-tight">Exported Evaluation Artifacts & Reports</h3>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs font-mono text-white/30">
          {reports.length} total report assets
        </span>
        <button className="text-xs font-mono text-accent hover:underline cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent">
          View Full Archive →
        </button>
      </div>
    </div>

    {/* Table Surface — Notion-style Graphite aesthetic */}
    <div className="max-h-[440px] overflow-y-auto border border-white/[0.08] rounded-xl bg-white/[0.015] backdrop-blur-sm scrollbar-thin scrollbar-thumb-white/10">
      <table className="w-full text-xs font-mono border-collapse" role="table" aria-label="Reports Registry Table">
        <thead className="sticky top-0 z-10 bg-zinc-950/90 backdrop-blur-md border-b border-white/[0.08]">
          <tr className="text-left">
            {['Evaluation Suite', 'Report Type', 'Generated At', 'File Size', 'Checksum (SHA-256)', 'Format', 'Action'].map(h => (
              <th key={h} className="py-2.5 px-3 text-[10px] uppercase tracking-wider text-white/40 font-semibold select-none">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/[0.03]">
          {reports.slice(0, 15).map(r => (
            <tr key={r.id} className="hover:bg-white/[0.035] transition-colors group">
              <td className="py-2.5 px-3">
                <div className="text-white/90 font-medium truncate max-w-xs group-hover:text-accent transition-colors">{r.evaluationName}</div>
                <div className="text-[10px] text-white/30 mt-0.5">{r.model} · {r.benchmark}</div>
              </td>
              <td className="py-2.5 px-3">
                <div className="flex items-center gap-2">
                  {FORMAT_ICONS[r.format] ?? <FileText className="w-3.5 h-3.5 text-white/40" />}
                  <span className="text-white/70">{r.type}</span>
                </div>
              </td>
              <td className="py-2.5 px-3 text-white/40 whitespace-nowrap">
                {new Date(r.generatedAt).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
              </td>
              <td className="py-2.5 px-3 text-white/50">{r.size}</td>
              <td className="py-2.5 px-3 text-white/30 text-[10px] font-mono whitespace-nowrap">
                sha256:{r.id.slice(0, 7)}...
              </td>
              <td className="py-2.5 px-3">
                <span className={`inline-flex px-2 py-0.5 rounded-md border text-[10px] uppercase tracking-wider font-semibold ${FORMAT_COLORS[r.format] ?? 'text-white/40 border-white/10'}`}>
                  {r.format}
                </span>
              </td>
              <td className="py-2.5 px-3">
                <button
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-white/10 bg-white/5 text-[10px] font-mono text-white/70 hover:text-white hover:bg-white/10 transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  title={`Download ${r.evaluationName} (${r.format.toUpperCase()})`}
                >
                  <Download className="w-3 h-3 text-white/50" aria-hidden="true" />
                  Download
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </section>
);

export const ReportsTable = memo(ReportsTableComponent);
export default ReportsTable;
