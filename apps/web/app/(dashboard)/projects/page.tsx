export default function ProjectsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-muted-foreground mt-1">Manage your workspaces and team collaborations.</p>
        </div>
        <button className="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-md font-medium text-sm transition-colors">
          New Project
        </button>
      </div>
      
      <div className="p-12 text-center rounded-xl border border-dashed border-muted-foreground/25">
        <p className="text-muted-foreground">No projects yet. Create your first project.</p>
      </div>
    </div>
  );
}
