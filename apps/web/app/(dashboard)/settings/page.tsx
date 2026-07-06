export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">Manage user preferences, API keys, and team access.</p>
      </div>
      <div className="flex gap-8">
        <div className="w-48 space-y-1">
          <div className="px-3 py-2 bg-muted rounded-md text-sm font-medium text-foreground cursor-pointer">Profile</div>
          <div className="px-3 py-2 hover:bg-muted/50 rounded-md text-sm font-medium text-muted-foreground cursor-pointer transition-colors">API Keys</div>
          <div className="px-3 py-2 hover:bg-muted/50 rounded-md text-sm font-medium text-muted-foreground cursor-pointer transition-colors">Organization</div>
        </div>
        <div className="flex-1 p-6 border rounded-xl shadow-sm">
          <h2 className="text-lg font-medium mb-4">Profile Settings</h2>
          <div className="space-y-4 max-w-md">
            <div className="space-y-2">
              <label className="text-sm font-medium">Full Name</label>
              <input type="text" className="w-full border rounded-md px-3 py-2 text-sm bg-background" placeholder="John Doe" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Email</label>
              <input type="email" className="w-full border rounded-md px-3 py-2 text-sm bg-background text-muted-foreground" disabled value="john@example.com" />
            </div>
            <button className="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-md font-medium text-sm transition-colors">
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
