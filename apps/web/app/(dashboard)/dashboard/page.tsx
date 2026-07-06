export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">Welcome to Atlas. Here is an overview of your recent evaluations.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-xl border bg-card text-card-foreground shadow-sm">
          <h3 className="text-sm font-medium text-muted-foreground">Active Runs</h3>
          <p className="text-3xl font-bold mt-2">3</p>
        </div>
        <div className="p-6 rounded-xl border bg-card text-card-foreground shadow-sm">
          <h3 className="text-sm font-medium text-muted-foreground">Total Reports</h3>
          <p className="text-3xl font-bold mt-2">42</p>
        </div>
        <div className="p-6 rounded-xl border bg-card text-card-foreground shadow-sm">
          <h3 className="text-sm font-medium text-muted-foreground">Avg. Latency</h3>
          <p className="text-3xl font-bold mt-2">2s</p>
        </div>
      </div>

      <div className="p-6 rounded-xl border bg-card text-card-foreground shadow-sm min-h-[300px] flex items-center justify-center">
        <p className="text-muted-foreground">Recent Executions Table Placeholder</p>
      </div>
    </div>
  );
}
