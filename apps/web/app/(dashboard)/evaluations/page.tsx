import { Card } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Play, Filter, MoreHorizontal } from "lucide-react";

const executions = [
  { id: "ATL-RUN-0921", model: "gpt-4o", benchmark: "HumanEval", version: "v1.2", status: "Running", start: "2 mins ago", duration: "-", user: "JD" },
  { id: "ATL-RUN-0920", model: "claude-3.5-sonnet", benchmark: "SWE-bench", version: "v1.0", status: "Completed", start: "1 hour ago", duration: "45m 12s", user: "JD" },
  { id: "ATL-RUN-0919", model: "llama-3-70b", benchmark: "MMLU", version: "v2.1", status: "Failed", start: "3 hours ago", duration: "1m 02s", user: "TS" },
  { id: "ATL-RUN-0918", model: "gpt-4o", benchmark: "RepoBench", version: "v1.0", status: "Completed", start: "5 hours ago", duration: "12m 40s", user: "JD" },
  { id: "ATL-RUN-0917", model: "gemini-1.5-pro", benchmark: "GSM8K", version: "v1.0", status: "Completed", start: "Yesterday", duration: "8m 15s", user: "MK" },
  { id: "ATL-RUN-0916", model: "claude-3-opus", benchmark: "AdvBench", version: "v1.1", status: "Cancelled", start: "Yesterday", duration: "0m 12s", user: "JD" },
];

export default function EvaluationsPage() {
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Execution History</h1>
          <p className="text-muted-foreground mt-2 text-sm">Configure, trigger, and monitor benchmark runs against AI models.</p>
        </div>
        <div className="flex gap-3">
          <button className="bg-muted text-foreground hover:bg-muted/80 px-4 py-2 rounded-lg font-medium text-sm transition-all border flex items-center gap-2">
            <Filter className="w-4 h-4" /> Filter
          </button>
          <button className="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg font-medium text-sm transition-all shadow-sm flex items-center gap-2">
            <Play className="w-4 h-4" /> New Run
          </button>
        </div>
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-muted-foreground bg-muted/50 border-b uppercase tracking-wider">
              <tr>
                <th className="px-6 py-4 font-semibold">Run ID</th>
                <th className="px-6 py-4 font-semibold">Model</th>
                <th className="px-6 py-4 font-semibold">Benchmark</th>
                <th className="px-6 py-4 font-semibold">Status</th>
                <th className="px-6 py-4 font-semibold">Started</th>
                <th className="px-6 py-4 font-semibold">Duration</th>
                <th className="px-6 py-4 font-semibold">User</th>
                <th className="px-6 py-4 font-semibold"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {executions.map((run) => (
                <tr key={run.id} className="bg-background hover:bg-muted/30 transition-colors">
                  <td className="px-6 py-4 font-mono font-medium text-foreground">{run.id}</td>
                  <td className="px-6 py-4 font-medium">{run.model}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-foreground">{run.benchmark}</span>
                      <span className="text-xs text-muted-foreground">{run.version}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <Badge variant={run.status === "Running" ? "default" : run.status === "Completed" ? "success" : run.status === "Failed" ? "danger" : "secondary"}>
                      {run.status}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 text-muted-foreground">{run.start}</td>
                  <td className="px-6 py-4 font-mono text-xs">{run.duration}</td>
                  <td className="px-6 py-4">
                    <div className="w-6 h-6 rounded-full bg-accent text-accent-foreground flex items-center justify-center text-[10px] font-bold">
                      {run.user}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-muted-foreground hover:text-foreground transition-colors">
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
