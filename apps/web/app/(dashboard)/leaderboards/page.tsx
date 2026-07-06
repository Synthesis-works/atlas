export default function LeaderboardsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Leaderboards</h1>
        <p className="text-muted-foreground mt-1">Compare models across standardized, versioned benchmarks.</p>
      </div>
      <div className="border rounded-xl shadow-sm overflow-hidden">
        <div className="bg-muted p-4 border-b">
          <div className="flex gap-4 text-sm font-medium">
            <span className="text-primary cursor-pointer">Coding</span>
            <span className="text-muted-foreground hover:text-foreground cursor-pointer transition-colors">Reasoning</span>
            <span className="text-muted-foreground hover:text-foreground cursor-pointer transition-colors">Math</span>
          </div>
        </div>
        <div className="p-6 h-64 flex items-center justify-center">
          <p className="text-muted-foreground">Ranking Table Placeholder</p>
        </div>
      </div>
    </div>
  );
}
