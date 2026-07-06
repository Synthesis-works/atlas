"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Play, CheckCircle2, Clock, AlertCircle } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { cn } from "../../../lib/utils";

const chartData = [
  { name: 'Mon', coding: 84, reasoning: 72 },
  { name: 'Tue', coding: 85, reasoning: 74 },
  { name: 'Wed', coding: 87, reasoning: 75 },
  { name: 'Thu', coding: 89, reasoning: 79 },
  { name: 'Fri', coding: 92, reasoning: 84 },
  { name: 'Sat', coding: 91, reasoning: 85 },
  { name: 'Sun', coding: 94, reasoning: 88 },
];

const recentExecutions = [
  { id: "run-0921", model: "gpt-4o", benchmark: "HumanEval v1.2", status: "Running", time: "2m 14s", progress: 68 },
  { id: "run-0920", model: "claude-3.5-sonnet", benchmark: "SWE-bench", status: "Completed", time: "45m 12s", progress: 100 },
  { id: "run-0919", model: "llama-3-70b", benchmark: "MMLU", status: "Failed", time: "1m 02s", progress: 12 },
  { id: "run-0918", model: "gpt-4o", benchmark: "RepoBench", status: "Completed", time: "12m 40s", progress: 100 },
  { id: "run-0917", model: "claude-3.5-sonnet", benchmark: "GPQA", status: "Completed", time: "5m 22s", progress: 100 },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
          <p className="text-muted-foreground mt-2 text-sm">Monitor your evaluation pipelines and model capabilities.</p>
        </div>
        <div className="flex gap-3">
          <button className="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg font-medium text-sm transition-all shadow-sm active:scale-95">
            New Evaluation
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <div className="space-y-2">
                <p className="text-sm font-medium text-muted-foreground">Active Runs</p>
                <p className="text-3xl font-bold">12</p>
              </div>
              <div className="p-2 bg-primary/10 text-primary rounded-lg">
                <Play className="w-5 h-5" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm text-success font-medium">
              <span>+3 since yesterday</span>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <div className="space-y-2">
                <p className="text-sm font-medium text-muted-foreground">Total Reports</p>
                <p className="text-3xl font-bold">1,204</p>
              </div>
              <div className="p-2 bg-success/10 text-success rounded-lg">
                <CheckCircle2 className="w-5 h-5" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm text-success font-medium">
              <span>+142 this week</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <div className="space-y-2">
                <p className="text-sm font-medium text-muted-foreground">Avg. Latency</p>
                <p className="text-3xl font-bold">1.4s</p>
              </div>
              <div className="p-2 bg-warning/10 text-warning rounded-lg">
                <Clock className="w-5 h-5" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm text-warning font-medium">
              <span>+0.2s p95</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <div className="space-y-2">
                <p className="text-sm font-medium text-muted-foreground">Failure Rate</p>
                <p className="text-3xl font-bold">2.1%</p>
              </div>
              <div className="p-2 bg-danger/10 text-danger rounded-lg">
                <AlertCircle className="w-5 h-5" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm text-success font-medium">
              <span>-0.4% from last week</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Capability Progression</CardTitle>
            <CardDescription>Aggregate performance across primary domains over time.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[350px] w-full mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorCoding" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorReasoning" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border)" opacity={0.5} />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'var(--color-muted-foreground)', fontSize: 12 }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: 'var(--color-muted-foreground)', fontSize: 12 }} domain={[50, 100]} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)', borderRadius: '8px', color: 'var(--color-foreground)', boxShadow: 'var(--shadow-subtle)' }}
                    itemStyle={{ color: 'var(--color-foreground)' }}
                  />
                  <Area type="monotone" dataKey="coding" stroke="var(--color-primary)" strokeWidth={2} fillOpacity={1} fill="url(#colorCoding)" />
                  <Area type="monotone" dataKey="reasoning" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorReasoning)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Executions</CardTitle>
            <CardDescription>Live evaluation pipeline status.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {recentExecutions.map((run) => (
                <div key={run.id} className="flex items-start justify-between group">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold leading-none text-foreground">{run.model}</p>
                    <p className="text-xs text-muted-foreground font-medium">{run.benchmark}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <div className="w-28 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div 
                          className={cn("h-full rounded-full transition-all duration-1000", run.status === "Failed" ? "bg-danger" : "bg-primary")} 
                          style={{ width: `${run.progress}%` }} 
                        />
                      </div>
                      <span className="text-[10px] text-muted-foreground font-medium">{run.progress}%</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1.5">
                    <Badge variant={run.status === "Running" ? "default" : run.status === "Completed" ? "success" : "danger"}>
                      {run.status}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground font-mono">{run.time}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
