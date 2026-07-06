import Link from "next/link";
import { 
  Home, 
  Folder, 
  Library, 
  Database, 
  Play, 
  BarChart, 
  Trophy, 
  Settings, 
  Book 
} from "lucide-react";

export function Sidebar() {
  return (
    <aside className="w-64 border-r bg-muted/40 h-screen flex flex-col">
      <div className="h-16 flex items-center px-6 border-b font-bold text-lg tracking-tight">
        Atlas
      </div>
      
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        <div className="mb-4">
          <p className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Core</p>
          <Link href="/" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted text-sm font-medium transition-colors">
            <Home className="w-4 h-4" /> Dashboard
          </Link>
          <Link href="/projects" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted text-sm font-medium transition-colors">
            <Folder className="w-4 h-4" /> Projects
          </Link>
        </div>

        <div className="mb-4">
          <p className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Evaluation</p>
          <Link href="/benchmarks" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted text-sm font-medium transition-colors">
            <Library className="w-4 h-4" /> Benchmarks
          </Link>
          <Link href="/datasets" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted text-sm font-medium transition-colors">
            <Database className="w-4 h-4" /> Datasets
          </Link>
          <Link href="/evaluations" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted text-sm font-medium transition-colors">
            <Play className="w-4 h-4" /> Executions
          </Link>
        </div>

        <div className="mb-4">
          <p className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Insights</p>
          <Link href="/reports" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted text-sm font-medium transition-colors">
            <BarChart className="w-4 h-4" /> Reports
          </Link>
          <Link href="/leaderboards" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted text-sm font-medium transition-colors">
            <Trophy className="w-4 h-4" /> Leaderboards
          </Link>
        </div>
      </nav>

      <div className="p-4 border-t space-y-1">
        <Link href="/settings" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted text-sm font-medium transition-colors">
          <Settings className="w-4 h-4" /> Settings
        </Link>
        <a href="#" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted text-sm font-medium transition-colors text-muted-foreground">
          <Book className="w-4 h-4" /> Documentation
        </a>
      </div>
    </aside>
  );
}
