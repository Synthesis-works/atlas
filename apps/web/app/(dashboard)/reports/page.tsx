"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "../../../components/ui/dialog";
import { Input } from "../../../components/ui/input";
import { FileText, Download, Eye, Calendar, Plus, CheckSquare } from "lucide-react";
import { MOCK_REPORTS } from "../../../lib/mock-data";
import { cn } from "../../../lib/utils";

export default function ReportsPage() {
  const [reports, setReports] = useState(MOCK_REPORTS);
  const [isGenerateDialogOpen, setIsGenerateDialogOpen] = useState(false);
  const [isCompareMode, setIsCompareMode] = useState(false);
  const [selectedReports, setSelectedReports] = useState<string[]>([]);

  const handleGenerateReport = () => {
    setReports([
      { id: `REP-0${reports.length + 1}`, name: "New Evaluation Report", type: "Detailed Analysis", benchmark: "Selected", date: "Just now", size: "1.2 MB" },
      ...reports
    ]);
    setIsGenerateDialogOpen(false);
  };

  const toggleSelection = (id: string) => {
    if (selectedReports.includes(id)) {
      setSelectedReports(selectedReports.filter(r => r !== id));
    } else {
      setSelectedReports([...selectedReports, id]);
    }
  };

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    alert("Mock: Downloading PDF report...");
  };

  const handleView = (e: React.MouseEvent) => {
    e.stopPropagation();
    alert("Mock: Opening report viewer...");
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
          <p className="text-muted-foreground mt-2 text-sm">Present evaluation results as scientific, evidence-based documents.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant={isCompareMode ? "secondary" : "outline"} className="shadow-sm" onClick={() => {
            setIsCompareMode(!isCompareMode);
            if (isCompareMode) setSelectedReports([]);
          }}>
            {isCompareMode ? "Cancel Compare" : "Compare Reports"}
          </Button>

          {isCompareMode && selectedReports.length > 0 && (
            <Button variant="default" className="shadow-sm animate-in fade-in zoom-in duration-200">
              Compare Selected ({selectedReports.length})
            </Button>
          )}

          <Dialog open={isGenerateDialogOpen} onOpenChange={setIsGenerateDialogOpen}>
            <DialogTrigger asChild>
              <Button className="shadow-sm">
                <Plus className="w-4 h-4 mr-2" /> Generate Report
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Generate Report</DialogTitle>
                <DialogDescription>
                  Compile evaluation results into a shareable document.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Evaluation Run ID</label>
                  <Input placeholder="e.g. ATL-RUN-0921" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Report Title</label>
                  <Input placeholder="e.g. GPT-4o Capability Profile" />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsGenerateDialogOpen(false)}>Cancel</Button>
                <Button onClick={handleGenerateReport}>Generate PDF</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {reports.map((report) => {
          const isSelected = selectedReports.includes(report.id);
          return (
            <Card 
              key={report.id} 
              className={cn(
                "group transition-all duration-200", 
                isCompareMode ? "cursor-pointer hover:border-primary/50" : "hover:-translate-y-1",
                isSelected ? "border-primary ring-1 ring-primary/20 bg-primary/5" : ""
              )}
              onClick={() => {
                if (isCompareMode) toggleSelection(report.id);
              }}
            >
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start">
                  <div className="p-3 bg-accent/50 rounded-xl group-hover:bg-primary/10 transition-colors">
                    {isCompareMode && isSelected ? (
                      <CheckSquare className="w-6 h-6 text-primary" />
                    ) : (
                      <FileText className={cn("w-6 h-6 text-primary transition-opacity", isCompareMode && "opacity-50 group-hover:opacity-100")} />
                    )}
                  </div>
                  {!isCompareMode && (
                    <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-2 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground transition-colors" onClick={handleView}>
                        <Eye className="w-4 h-4" />
                      </button>
                      <button className="p-2 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground transition-colors" onClick={handleDownload}>
                        <Download className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>
                <CardTitle className="text-xl mt-4">{report.name}</CardTitle>
                <CardDescription className="font-medium text-primary/80">{report.type}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm text-muted-foreground mt-2">
                  <div className="flex justify-between">
                    <span className="font-medium">Benchmarks:</span>
                    <span className="truncate ml-4">{report.benchmark}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> Generated:</span>
                    <span>{report.date}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
