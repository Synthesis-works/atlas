"use client";

import { Search, Bell, Command } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { cn } from "../../lib/utils";

export function TopNav() {
  const { setTheme, theme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  return (
    <header className="h-16 border-b flex items-center justify-between px-6 bg-background/80 backdrop-blur-md sticky top-0 z-50 transition-colors">
      <div className="flex-1 flex items-center gap-4">
        <div className="text-sm font-medium text-muted-foreground hidden md:flex items-center gap-2 select-none">
          <span className="hover:text-foreground cursor-pointer transition-colors">Atlas</span>
          <span>/</span>
          <span className="text-foreground font-semibold">Dashboard</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/30 hover:bg-muted/80 px-3 py-1.5 rounded-full transition-all border shadow-sm group">
          <Search className="w-4 h-4 group-hover:text-foreground transition-colors" />
          <span className="group-hover:text-foreground transition-colors">Search resources...</span>
          <kbd className="hidden sm:inline-flex items-center gap-1 ml-4 text-[10px] bg-background border px-1.5 py-0.5 rounded font-mono text-muted-foreground shadow-sm">
            <Command className="w-3 h-3" /> K
          </kbd>
        </button>

        <button 
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="p-2 text-muted-foreground hover:bg-accent hover:text-foreground rounded-full transition-colors"
          title="Toggle theme"
        >
          {mounted && theme === 'dark' ? '☀️' : '🌙'}
        </button>

        <button className="p-2 text-muted-foreground hover:bg-accent hover:text-foreground rounded-full transition-colors relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-primary rounded-full shadow-glow border-2 border-background"></span>
        </button>

        <div className="w-8 h-8 bg-gradient-to-tr from-primary to-primary/60 text-primary-foreground rounded-full flex items-center justify-center font-bold text-sm ml-2 cursor-pointer shadow-sm hover:scale-105 transition-transform select-none">
          JD
        </div>
      </div>
    </header>
  );
}
