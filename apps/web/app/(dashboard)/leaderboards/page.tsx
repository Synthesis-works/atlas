"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "../../../components/ui/dropdown-menu";
import { Tabs, TabsList, TabsTrigger } from "../../../components/ui/tabs";
import { Trophy, TrendingUp, ChevronDown } from "lucide-react";
import { MOCK_RANKINGS } from "../../../lib/mock-data";

export default function LeaderboardsPage() {
  const [activeDomain, setActiveDomain] = useState("Coding");
  const [version, setVersion] = useState("Version 1.2");
  const [sortField, setSortField] = useState<string>("rank");
  const [sortAsc, setSortAsc] = useState(true);

  const domains = Object.keys(MOCK_RANKINGS);
  const rankings = MOCK_RANKINGS[activeDomain] || [];

  const toggleSort = (field: string) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const sortedRankings = [...rankings].sort((a, b) => {
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
          <h1 className="text-3xl font-bold tracking-tight">Leaderboards</h1>
          <p className="text-muted-foreground mt-2 text-sm">Compare models across standardized, versioned capability domains.</p>
        </div>
      </div>

      <Tabs value={activeDomain} onValueChange={setActiveDomain} className="w-full">
        <TabsList className="flex w-max mb-4">
          {domains.map(domain => (
            <TabsTrigger key={domain} value={domain}>{domain}</TabsTrigger>
          ))}
        </TabsList>

        <Card className="border shadow-sm">
          <CardHeader className="bg-muted/30 border-b flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Trophy className="w-5 h-5 text-warning" /> {activeDomain} Capability
              </CardTitle>
              <CardDescription className="mt-1">Aggregated scores for {activeDomain} benchmarks.</CardDescription>
            </div>
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="shadow-sm">
                  {version} <ChevronDown className="w-4 h-4 ml-2" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Taxonomy Version</DropdownMenuLabel>
                <DropdownMenuItem onClick={() => setVersion("Version 1.2")}>Version 1.2 (Latest)</DropdownMenuItem>
                <DropdownMenuItem onClick={() => setVersion("Version 1.1")}>Version 1.1</DropdownMenuItem>
                <DropdownMenuItem onClick={() => setVersion("Version 1.0")}>Version 1.0</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-muted-foreground bg-background border-b uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-4 font-semibold w-16 text-center cursor-pointer hover:text-foreground select-none" onClick={() => toggleSort("rank")}>Rank</th>
                    <th className="px-6 py-4 font-semibold cursor-pointer hover:text-foreground select-none" onClick={() => toggleSort("model")}>Model</th>
                    <th className="px-6 py-4 font-semibold cursor-pointer hover:text-foreground select-none" onClick={() => toggleSort("score")}>Aggregate Score</th>
                    <th className="px-6 py-4 font-semibold">MoM Change</th>
                    <th className="px-6 py-4 font-semibold"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {sortedRankings.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-12 text-center text-muted-foreground">
                        No ranking data available for this domain.
                      </td>
                    </tr>
                  ) : sortedRankings.map((row) => (
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
      </Tabs>
    </div>
  );
}
