export default function EvaluationsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Executions</h1>
          <p className="text-muted-foreground mt-1">Configure, trigger, and monitor benchmark runs against AI models.</p>
        </div>
        <button className="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-md font-medium text-sm transition-colors">
          New Run
        </button>
      </div>
      <div className="p-6 rounded-xl border bg-card shadow-sm h-64 flex items-center justify-center">
        <p className="text-muted-foreground">Execution History Placeholder</p>
      </div>
    </div>
  );
}
