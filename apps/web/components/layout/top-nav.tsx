"use client";

import { Search, Bell, Command, Sun, Moon } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "../ui/dropdown-menu";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { Input } from "../ui/input";
import { Button } from "../ui/button";

export function TopNav() {
  const { setTheme, theme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setSearchOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

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
        <Dialog open={searchOpen} onOpenChange={setSearchOpen}>
          <DialogTrigger asChild>
            <button className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/30 hover:bg-muted/80 px-3 py-1.5 rounded-full transition-all border shadow-sm group">
              <Search className="w-4 h-4 group-hover:text-foreground transition-colors" />
              <span className="group-hover:text-foreground transition-colors">Search resources...</span>
              <kbd className="hidden sm:inline-flex items-center gap-1 ml-4 text-[10px] bg-background border px-1.5 py-0.5 rounded font-mono text-muted-foreground shadow-sm">
                <Command className="w-3 h-3" /> K
              </kbd>
            </button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px] p-0 overflow-hidden">
            <div className="flex items-center border-b px-4">
              <Search className="w-5 h-5 text-muted-foreground mr-2" />
              <input 
                autoFocus
                placeholder="Type a command or search..." 
                className="flex h-14 w-full bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground"
              />
            </div>
            <div className="p-4 text-center text-sm text-muted-foreground">
              No recent searches. Try looking for a benchmark or project.
            </div>
          </DialogContent>
        </Dialog>

        <button 
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="p-2 text-muted-foreground hover:bg-accent hover:text-foreground rounded-full transition-colors"
          title="Toggle theme"
        >
          {mounted && theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="p-2 text-muted-foreground hover:bg-accent hover:text-foreground rounded-full transition-colors relative focus:outline-none">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-primary rounded-full shadow-glow border-2 border-background"></span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64">
            <DropdownMenuLabel>Notifications</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <div className="p-4 text-center text-sm text-muted-foreground">
              No new notifications.
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <div className="w-8 h-8 bg-gradient-to-tr from-primary to-primary/60 text-primary-foreground rounded-full flex items-center justify-center font-bold text-sm ml-2 cursor-pointer shadow-sm hover:scale-105 transition-transform select-none">
              JD
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">John Doe</p>
                <p className="text-xs leading-none text-muted-foreground">john.doe@example.com</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Profile Settings</DropdownMenuItem>
            <DropdownMenuItem>Organization</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-danger focus:text-danger">Log out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
