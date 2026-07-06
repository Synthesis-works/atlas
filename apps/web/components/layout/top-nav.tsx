"use client";

import { Search, Bell, User } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function TopNav() {
  const { setTheme, theme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  return (
    <header className="h-16 border-b flex items-center justify-between px-6 bg-background">
      <div className="flex-1 flex items-center gap-4">
        {/* Breadcrumbs Placeholder */}
        <div className="text-sm font-medium text-muted-foreground hidden md:flex items-center gap-2">
          <span>Atlas</span>
          <span>/</span>
          <span className="text-foreground">Dashboard</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/50 hover:bg-muted px-3 py-1.5 rounded-md transition-colors border">
          <Search className="w-4 h-4" />
          <span>Search...</span>
          <kbd className="hidden sm:inline-flex ml-2 text-[10px] bg-background border px-1.5 py-0.5 rounded">Cmd K</kbd>
        </button>

        <button 
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="p-2 hover:bg-muted rounded-full transition-colors"
          title="Toggle theme"
        >
          {mounted && theme === 'dark' ? '☀️' : '🌙'}
        </button>

        <button className="p-2 hover:bg-muted rounded-full transition-colors relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary rounded-full"></span>
        </button>

        <div className="w-8 h-8 bg-primary/10 text-primary rounded-full flex items-center justify-center font-bold text-sm ml-2 cursor-pointer">
          U
        </div>
      </div>
    </header>
  );
}
