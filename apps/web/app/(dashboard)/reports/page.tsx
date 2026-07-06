import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../components/ui/card";
import { FileText, Download, Eye, Calendar } from "lucide-react";

const reports = [
  { id: "REP-01", name: "GPT-4o Capability Profile", type: "Detailed Analysis", benchmark: "Multiple", date: "Oct 24, 2026", size: "2.4 MB" },
  { id: "REP-02", name: "Claude 3.5 Sonnet vs GPT-4o", type: "Comparison", benchmark: "HumanEval & SWE-bench", date: "Oct 22, 2026", size: "1.8 MB" },
  { id: "REP-03", name: "Llama 3 70B Safety Audit", type: "Compliance", benchmark: "AdvBench", date: "Oct 15, 2026", size: "3.1 MB" },
  { id: "REP-04", name: "Q3 Core Models Summary", type: "Executive Summary", benchmark: "Multiple", date: "Oct 01, 2026", size: "4.5 MB" },
];

export default function ReportsPage() {
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
          <p className="text-muted-foreground mt-2 text-sm">Present evaluation results as scientific, evidence-based documents.</p>
        </div>
        <button className="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg font-medium text-sm transition-all shadow-sm">
          Generate Report
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {reports.map((report) => (
          <Card key={report.id} className="group hover:-translate-y-1 transition-all">
            <CardHeader className="pb-3">
              <div className="flex justify-between items-start">
                <div className="p-3 bg-accent/50 rounded-xl group-hover:bg-primary/10 transition-colors">
                  <FileText className="w-6 h-6 text-primary" />
                </div>
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button className="p-2 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground">
                    <Eye className="w-4 h-4" />
                  </button>
                  <button className="p-2 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground">
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <CardTitle className="text-xl mt-4">{report.name}</CardTitle>
              <CardDescription className="font-medium text-primary/80">{report.type}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm text-muted-foreground mt-2">
                <div className="flex justify-between">
                  <span className="font-medium">Benchmarks:</span>
                  <span>{report.benchmark}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> Generated:</span>
                  <span>{report.date}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
