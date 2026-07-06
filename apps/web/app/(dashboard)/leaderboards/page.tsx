import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Trophy, TrendingUp, ChevronDown } from "lucide-react";

const rankings = [
  { rank: 1, model: "gpt-4o", score: 92.4, change: "+1.2", badge: "State of the Art" },
  { rank: 2, model: "claude-3.5-sonnet", score: 91.8, change: "+2.4", badge: "Top Tier" },
  { rank: 3, model: "llama-3-70b-instruct", score: 86.5, change: "0.0", badge: "Open Weights" },
  { rank: 4, model: "gemini-1.5-pro", score: 85.2, change: "-0.5" },
  { rank: 5, model: "mixtral-8x22b", score: 81.4, change: "+0.8" },
];

export default function LeaderboardsPage() {
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Leaderboards</h1>
          <p className="text-muted-foreground mt-2 text-sm">Compare models across standardized, versioned capability domains.</p>
        </div>
      </div>

      <div className="flex gap-4 border-b pb-4 overflow-x-auto">
        {["Coding", "Reasoning", "Mathematics", "Tool Use", "Safety"].map((domain, i) => (
          <button 
            key={domain} 
            className={`px-4 py-2 text-sm font-medium rounded-full transition-all whitespace-nowrap ${i === 0 ? "bg-primary text-primary-foreground shadow-sm" : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"}`}
          >
            {domain}
          </button>
        ))}
      </div>

      <Card className="border shadow-sm">
        <CardHeader className="bg-muted/30 border-b flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Trophy className="w-5 h-5 text-warning" /> Coding Capability
            </CardTitle>
            <CardDescription className="mt-1">Aggregated across HumanEval, MBPP, and SWE-bench.</CardDescription>
          </div>
          <button className="flex items-center gap-2 text-sm font-medium border px-3 py-1.5 rounded-lg bg-background hover:bg-muted transition-colors">
            Version 1.2 <ChevronDown className="w-4 h-4" />
          </button>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted-foreground bg-background border-b uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-4 font-semibold w-16 text-center">Rank</th>
                  <th className="px-6 py-4 font-semibold">Model</th>
                  <th className="px-6 py-4 font-semibold">Aggregate Score</th>
                  <th className="px-6 py-4 font-semibold">MoM Change</th>
                  <th className="px-6 py-4 font-semibold"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rankings.map((row) => (
                  <tr key={row.rank} className="bg-background hover:bg-muted/30 transition-colors">
                    <td className="px-6 py-5 text-center font-bold text-lg text-muted-foreground">
                      {row.rank === 1 ? <span className="text-warning">1</span> : row.rank}
                    </td>
                    <td className="px-6 py-5 font-semibold text-foreground text-base whitespace-nowrap">
                      {row.model}
                    </td>
                    <td className="px-6 py-5">
                      <span className="font-mono text-lg font-bold">{row.score}</span>
                    </td>
                    <td className="px-6 py-5">
                      <div className={`flex items-center gap-1 font-medium whitespace-nowrap ${row.change.startsWith('+') ? 'text-success' : row.change.startsWith('-') ? 'text-danger' : 'text-muted-foreground'}`}>
                        {row.change !== "0.0" && <TrendingUp className={`w-4 h-4 ${row.change.startsWith('-') && 'rotate-180'}`} />}
                        {row.change}
                      </div>
                    </td>
                    <td className="px-6 py-5 text-right whitespace-nowrap">
                      {row.badge && <Badge variant={row.rank === 1 ? "warning" : "default"}>{row.badge}</Badge>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
