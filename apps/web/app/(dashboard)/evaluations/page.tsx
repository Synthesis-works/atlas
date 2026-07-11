"use client";

import { useState } from "react";
import { Card } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "../../../components/ui/dialog";
import { Input } from "../../../components/ui/input";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "../../../components/ui/dropdown-menu";
import { Play, Filter, MoreHorizontal, FileText, XCircle, RotateCw } from "lucide-react";
import { MOCK_EXECUTIONS } from "../../../lib/mock-data";
import { cn } from "../../../lib/utils";

export default function EvaluationsPage() {
  const [executions, setExecutions] = useState(MOCK_EXECUTIONS);
  const [filterStatus, setFilterStatus] = useState<string>("All");
  const [sortField, setSortField] = useState<string>("id");
  const [sortAsc, setSortAsc] = useState(false);
  const [isRunDialogOpen, setIsRunDialogOpen] = useState(false);

  const toggleSort = (field: string) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const handleStartRun = () => {
    setExecutions([
      { id: `ATL-RUN-${Math.floor(1000 + Math.random() * 9000)}`, model: "New Model", benchmark: "Selected Benchmark", version: "v1.0", status: "Running", start: "Just now", duration: "-", user: "JD" },
      ...executions
    ]);
    setIsRunDialogOpen(false);
  };

  const filteredExecutions = executions
    .filter(run => filterStatus === "All" || run.status === filterStatus)
    .sort((a, b) => {
      const aVal = (a as any)[sortField];
      const bVal = (b as any)[sortField];
      if (aVal < bVal) return sortAsc ? -1 : 1;
      if (aVal > bVal) return sortAsc ? 1 : -1;
      return 0;
    });

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Execution History</h1>
          <p className="text-muted-foreground mt-2 text-sm">Configure, trigger, and monitor benchmark runs against AI models.</p>
        </div>
        <div className="flex gap-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="shadow-sm">
                <Filter className="w-4 h-4 mr-2" /> Filter: {filterStatus}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Status</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => setFilterStatus("All")}>All</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFilterStatus("Running")}>Running</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFilterStatus("Completed")}>Completed</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFilterStatus("Failed")}>Failed</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Dialog open={isRunDialogOpen} onOpenChange={setIsRunDialogOpen}>
            <DialogTrigger asChild>
              <Button className="shadow-sm">
                <Play className="w-4 h-4 mr-2" /> New Run
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Start New Evaluation Run</DialogTitle>
                <DialogDescription>
                  Select a model and benchmark to begin evaluation.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Model</label>
                  <Input placeholder="e.g. gpt-4o, llama-3-70b" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Benchmark</label>
                  <Input placeholder="e.g. HumanEval, SWE-bench" />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsRunDialogOpen(false)}>Cancel</Button>
                <Button onClick={handleStartRun}>Start Run</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-muted-foreground bg-muted/50 border-b uppercase tracking-wider">
              <tr>
                <th className="px-6 py-4 font-semibold cursor-pointer hover:text-foreground select-none" onClick={() => toggleSort("id")}>Run ID</th>
                <th className="px-6 py-4 font-semibold cursor-pointer hover:text-foreground select-none" onClick={() => toggleSort("model")}>Model</th>
                <th className="px-6 py-4 font-semibold cursor-pointer hover:text-foreground select-none" onClick={() => toggleSort("benchmark")}>Benchmark</th>
                <th className="px-6 py-4 font-semibold cursor-pointer hover:text-foreground select-none" onClick={() => toggleSort("status")}>Status</th>
                <th className="px-6 py-4 font-semibold cursor-pointer hover:text-foreground select-none" onClick={() => toggleSort("start")}>Started</th>
                <th className="px-6 py-4 font-semibold cursor-pointer hover:text-foreground select-none" onClick={() => toggleSort("duration")}>Duration</th>
                <th className="px-6 py-4 font-semibold cursor-pointer hover:text-foreground select-none" onClick={() => toggleSort("user")}>User</th>
                <th className="px-6 py-4 font-semibold"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredExecutions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-muted-foreground">
                    No executions found matching your criteria.
                  </td>
                </tr>
              ) : filteredExecutions.map((run) => (
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
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded focus:outline-none">
                          <MoreHorizontal className="w-4 h-4" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem>
                          <FileText className="w-4 h-4 mr-2" /> View Logs
                        </DropdownMenuItem>
                        {run.status === "Running" && (
                          <DropdownMenuItem className="text-danger focus:text-danger">
                            <XCircle className="w-4 h-4 mr-2" /> Cancel Run
                          </DropdownMenuItem>
                        )}
                        {(run.status === "Failed" || run.status === "Cancelled") && (
                          <DropdownMenuItem>
                            <RotateCw className="w-4 h-4 mr-2" /> Retry Execution
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
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
