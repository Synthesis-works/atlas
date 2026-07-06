import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Star, GitBranch, Plus } from "lucide-react";

const benchmarks = [
  { id: "human-eval", name: "HumanEval v1.2", category: "Coding", desc: "Python coding tasks evaluating functional correctness.", difficulty: "Medium", datasets: 1 },
  { id: "mmlu", name: "MMLU", category: "Knowledge", desc: "Massive Multitask Language Understanding across 57 subjects.", difficulty: "Hard", datasets: 4 },
  { id: "swe-bench", name: "SWE-bench", category: "Coding", desc: "Resolving real-world GitHub issues in Python repositories.", difficulty: "Expert", datasets: 1 },
  { id: "gsm8k", name: "GSM8K", category: "Mathematics", desc: "Grade school math word problems requiring multi-step reasoning.", difficulty: "Medium", datasets: 1 },
  { id: "arc", name: "AI2 Reasoning Challenge", category: "Reasoning", desc: "Grade-school science questions requiring logic and knowledge.", difficulty: "Medium", datasets: 2 },
  { id: "advbench", name: "AdvBench", category: "Safety", desc: "Adversarial prompts testing alignment and safety guardrails.", difficulty: "Hard", datasets: 1 },
];

export default function BenchmarksPage() {
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Benchmarks Directory</h1>
          <p className="text-muted-foreground mt-2 text-sm">Discover, view, and construct standardized evaluation tasks.</p>
        </div>
        <button className="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg font-medium text-sm transition-all shadow-sm active:scale-95 flex items-center gap-2">
          <Plus className="w-4 h-4" /> New Benchmark
        </button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {benchmarks.map((bm) => (
          <Card key={bm.id} className="group cursor-pointer flex flex-col justify-between hover:-translate-y-1">
            <CardHeader>
              <div className="flex justify-between items-start mb-3">
                <Badge variant="outline" className="bg-background/50 backdrop-blur-sm">{bm.category}</Badge>
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Star className="w-4 h-4 hover:text-warning transition-colors" />
                </div>
              </div>
              <CardTitle className="text-lg">{bm.name}</CardTitle>
              <CardDescription className="line-clamp-2 mt-1">{bm.desc}</CardDescription>
            </CardHeader>
            <CardContent className="mt-auto">
              <div className="flex justify-between items-center pt-4 border-t">
                <div className="flex items-center gap-2 text-xs text-muted-foreground font-medium">
                  <GitBranch className="w-3.5 h-3.5" />
                  <span>{bm.datasets} Dataset{bm.datasets > 1 ? 's' : ''}</span>
                </div>
                <Badge variant={bm.difficulty === "Expert" ? "danger" : bm.difficulty === "Hard" ? "warning" : "secondary"} className="shadow-sm">
                  {bm.difficulty}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
