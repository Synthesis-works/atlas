import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Users, LayoutGrid, Activity, MoreVertical, Plus } from "lucide-react";

const projects = [
  { id: "proj-1", name: "Core Models Evaluation", description: "Evaluating foundation models across coding and reasoning domains.", runs: 142, team: 4, status: "Active", lastActive: "2 hours ago" },
  { id: "proj-2", name: "Safety Alignment Checks", description: "Adversarial testing against Llama 3 70B to ensure compliance.", runs: 38, team: 2, status: "Active", lastActive: "1 day ago" },
  { id: "proj-3", name: "RAG Pipeline v2", description: "Retrieval augmented generation latency and accuracy tests.", runs: 12, team: 5, status: "Paused", lastActive: "1 week ago" },
];

export default function ProjectsPage() {
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground mt-2 text-sm">Manage your evaluation workspaces and collaborate with your team.</p>
        </div>
        <button className="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg font-medium text-sm transition-all shadow-sm active:scale-95 flex items-center gap-2">
          <Plus className="w-4 h-4" /> New Project
        </button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {projects.map((project) => (
          <Card key={project.id} className="group cursor-pointer">
            <CardHeader className="pb-4">
              <div className="flex justify-between items-start">
                <div className="p-2.5 bg-accent/50 rounded-lg group-hover:bg-primary/5 transition-colors">
                  <LayoutGrid className="w-5 h-5 text-primary" />
                </div>
                <button className="text-muted-foreground hover:text-foreground p-1 rounded transition-colors">
                  <MoreVertical className="w-4 h-4" />
                </button>
              </div>
              <CardTitle className="mt-4 text-xl">{project.name}</CardTitle>
              <CardDescription className="line-clamp-2 mt-1">{project.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-6 text-sm text-muted-foreground border-t pt-4">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4" />
                  <span className="font-medium">{project.runs} runs</span>
                </div>
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  <span className="font-medium">{project.team} members</span>
                </div>
              </div>
              <div className="flex justify-between items-center mt-4">
                <Badge variant={project.status === "Active" ? "success" : "secondary"}>
                  {project.status}
                </Badge>
                <span className="text-xs text-muted-foreground font-medium">{project.lastActive}</span>
              </div>
            </CardContent>
          </Card>
        ))}

        <button className="rounded-xl border-2 border-dashed border-muted-foreground/25 hover:border-primary/50 hover:bg-accent/30 transition-all flex flex-col items-center justify-center min-h-[250px] text-muted-foreground hover:text-foreground bg-transparent">
          <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4 transition-transform group-hover:scale-110">
            <Plus className="w-6 h-6" />
          </div>
          <span className="font-semibold tracking-tight">Create New Workspace</span>
        </button>
      </div>
    </div>
  );
}
