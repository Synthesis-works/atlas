"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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
import { cn } from "../../lib/utils";

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { section: "Core", items: [
      { name: "Dashboard", href: "/dashboard", icon: Home },
      { name: "Projects", href: "/projects", icon: Folder },
    ]},
    { section: "Evaluation", items: [
      { name: "Benchmarks", href: "/benchmarks", icon: Library },
      { name: "Datasets", href: "/datasets", icon: Database },
      { name: "Executions", href: "/evaluations", icon: Play },
    ]},
    { section: "Insights", items: [
      { name: "Reports", href: "/reports", icon: BarChart },
      { name: "Leaderboards", href: "/leaderboards", icon: Trophy },
    ]}
  ];

  return (
    <aside className="w-64 border-r bg-background/50 backdrop-blur-sm h-screen flex flex-col transition-all duration-300">
      <div className="h-16 flex items-center px-6 border-b font-semibold text-lg tracking-tight hover:text-primary transition-colors cursor-pointer">
        <div className="w-6 h-6 rounded bg-primary text-primary-foreground flex items-center justify-center mr-3 text-sm font-bold shadow-glow">
          A
        </div>
        Atlas
      </div>
      
      <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-6">
        {navItems.map((group) => (
          <div key={group.section}>
            <p className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 select-none">
              {group.section}
            </p>
            <div className="space-y-1">
              {group.items.map((item) => {
                const isActive = pathname.startsWith(item.href) && (item.href !== "/" || pathname === "/");
                return (
                  <Link 
                    key={item.href} 
                    href={item.href} 
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group relative",
                      isActive 
                        ? "bg-accent/80 text-foreground" 
                        : "text-muted-foreground hover:bg-accent/40 hover:text-foreground hover:translate-x-1"
                    )}
                  >
                    {isActive && (
                      <span className="absolute left-0 w-1 h-5 bg-primary rounded-r-full" />
                    )}
                    <item.icon className={cn("w-4 h-4 transition-colors", isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground")} /> 
                    {item.name}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="p-4 border-t space-y-1 bg-background/80">
        <Link href="/settings" className={cn(
          "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
          pathname.startsWith("/settings") ? "bg-accent/80 text-foreground" : "text-muted-foreground hover:bg-accent/40 hover:text-foreground hover:translate-x-1"
        )}>
          <Settings className="w-4 h-4" /> Settings
        </Link>
        <a href="#" className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 text-muted-foreground hover:bg-accent/40 hover:text-foreground hover:translate-x-1">
          <Book className="w-4 h-4" /> Documentation
        </a>
      </div>
    </aside>
  );
}
