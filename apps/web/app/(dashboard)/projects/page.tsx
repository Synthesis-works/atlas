"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "../../../components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "../../../components/ui/dropdown-menu";
import { Users, LayoutGrid, Activity, MoreVertical, Plus, Search, Filter, Trash, Edit, PauseCircle } from "lucide-react";
import { MOCK_PROJECTS } from "../../../lib/mock-data";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

const projectSchema = z.object({
  name: z.string().min(2, "Name is required"),
  description: z.string().min(10, "Provide a better description"),
});

export default function ProjectsPage() {
  const [projects, setProjects] = useState(MOCK_PROJECTS);
  const [search, setSearch] = useState("");
  const [sortOrder, setSortOrder] = useState<"newest" | "runs">("newest");
  const [filterStatus, setFilterStatus] = useState<"All" | "Active" | "Paused">("All");
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<z.infer<typeof projectSchema>>({
    resolver: zodResolver(projectSchema),
  });

  const onSubmit = (values: z.infer<typeof projectSchema>) => {
    setProjects([
      {
        id: `proj-${Date.now()}`,
        name: values.name,
        description: values.description,
        runs: 0,
        team: 1,
        status: "Active",
        lastActive: "Just now",
      },
      ...projects,
    ]);
    reset();
    setIsDialogOpen(false);
  };

  const filteredProjects = projects
    .filter(p => filterStatus === "All" || p.status === filterStatus)
    .filter(p => p.name.toLowerCase().includes(search.toLowerCase()) || p.description.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      if (sortOrder === "runs") return b.runs - a.runs;
      return 0;
    });

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground mt-2 text-sm">Manage your evaluation workspaces and collaborate with your team.</p>
        </div>
        
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="shadow-sm">
              <Plus className="w-4 h-4 mr-2" /> New Project
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Project</DialogTitle>
              <DialogDescription>
                Set up a new workspace for your evaluations.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Project Name</label>
                <Input placeholder="e.g. Safety Alignment Team" {...register("name")} />
                {errors.name && <p className="text-sm text-danger">{errors.name.message}</p>}
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Description</label>
                <Input placeholder="What is the focus of this project?" {...register("description")} />
                {errors.description && <p className="text-sm text-danger">{errors.description.message}</p>}
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
                <Button type="submit">Create Workspace</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>
      
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search projects..." 
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="w-full sm:w-auto">
                <Filter className="w-4 h-4 mr-2" /> Filter: {filterStatus}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Status</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => setFilterStatus("All")}>All</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFilterStatus("Active")}>Active</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFilterStatus("Paused")}>Paused</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuLabel>Sort By</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => setSortOrder("newest")}>Recently Active</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setSortOrder("runs")}>Most Runs</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredProjects.map((project) => (
          <Card key={project.id} className="group cursor-pointer hover:-translate-y-1">
            <CardHeader className="pb-4">
              <div className="flex justify-between items-start">
                <div className="p-2.5 bg-accent/50 rounded-lg group-hover:bg-primary/5 transition-colors">
                  <LayoutGrid className="w-5 h-5 text-primary" />
                </div>
                
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button className="text-muted-foreground hover:text-foreground p-1 rounded transition-colors focus:outline-none">
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem>
                      <Edit className="w-4 h-4 mr-2" /> Edit Project
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      <PauseCircle className="w-4 h-4 mr-2" /> Pause Executions
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem className="text-danger focus:text-danger" onClick={() => setProjects(projects.filter(p => p.id !== project.id))}>
                      <Trash className="w-4 h-4 mr-2" /> Delete Project
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

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

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <button className="rounded-xl border-2 border-dashed border-muted-foreground/25 hover:border-primary/50 hover:bg-accent/30 transition-all flex flex-col items-center justify-center min-h-[250px] text-muted-foreground hover:text-foreground bg-transparent w-full">
              <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4 transition-transform group-hover:scale-110">
                <Plus className="w-6 h-6" />
              </div>
              <span className="font-semibold tracking-tight">Create New Workspace</span>
            </button>
          </DialogTrigger>
        </Dialog>
      </div>
    </div>
  );
}
