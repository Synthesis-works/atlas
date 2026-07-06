export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
        <p className="text-muted-foreground mt-1">Present evaluation results as scientific, evidence-based documents.</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-6 border rounded-xl shadow-sm min-h-[200px] flex items-center justify-center">Report Card Placeholder</div>
        <div className="p-6 border rounded-xl shadow-sm min-h-[200px] flex items-center justify-center">Report Card Placeholder</div>
      </div>
    </div>
  );
}
