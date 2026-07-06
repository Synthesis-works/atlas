import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../components/ui/card";
import { User, Key, Shield, Building2, Bell, Cpu } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-2 text-sm">Manage user preferences, API keys, and platform configuration.</p>
      </div>
      
      <div className="flex flex-col lg:flex-row gap-8">
        <aside className="lg:w-64 space-y-1">
          <button className="w-full flex items-center gap-3 px-3 py-2.5 bg-accent/80 rounded-lg text-sm font-medium text-foreground transition-all">
            <User className="w-4 h-4" /> Profile
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-accent/40 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground transition-all">
            <Building2 className="w-4 h-4" /> Organization
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-accent/40 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground transition-all">
            <Key className="w-4 h-4" /> API Keys
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-accent/40 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground transition-all">
            <Shield className="w-4 h-4" /> Roles & Permissions
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-accent/40 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground transition-all">
            <Cpu className="w-4 h-4" /> Adapters Config
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-accent/40 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground transition-all">
            <Bell className="w-4 h-4" /> Notifications
          </button>
        </aside>

        <div className="flex-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Profile Details</CardTitle>
              <CardDescription>Update your personal information and email address.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center gap-6">
                <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-primary to-primary/50 flex items-center justify-center text-primary-foreground font-bold text-2xl shadow-lg select-none">
                  JD
                </div>
                <button className="border px-4 py-2 rounded-lg text-sm font-medium hover:bg-muted transition-colors">
                  Change Avatar
                </button>
              </div>

              <div className="grid gap-4 max-w-md">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Full Name</label>
                  <input type="text" className="w-full border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all" defaultValue="John Doe" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Email Address</label>
                  <input type="email" className="w-full border rounded-lg px-3 py-2 text-sm bg-muted text-muted-foreground cursor-not-allowed" disabled defaultValue="john.doe@example.com" />
                  <p className="text-xs text-muted-foreground">To change your email, please contact an administrator.</p>
                </div>
                <div className="pt-2">
                  <button className="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg font-medium text-sm transition-all shadow-sm active:scale-95">
                    Save Changes
                  </button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
