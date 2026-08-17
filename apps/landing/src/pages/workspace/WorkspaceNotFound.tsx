import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { AlertCircle, ArrowLeft, LayoutDashboard } from 'lucide-react';
import { Button } from '@/components/ui/button';

export const WorkspaceNotFound: React.FC = () => {
  const location = useLocation();

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] p-8 text-center">
      <div className="w-16 h-16 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-6">
        <AlertCircle className="w-8 h-8 text-amber-400" />
      </div>

      <h1 className="text-2xl font-bold text-white tracking-tight mb-2">
        Workspace View Not Found
      </h1>

      <p className="text-white/60 max-w-md text-sm mb-6">
        The requested path <code className="bg-white/10 px-2 py-0.5 rounded text-amber-300 font-mono text-xs">{location.pathname}</code> does not match any active workspace module.
      </p>

      <div className="flex items-center gap-3">
        <Link to="/dashboard">
          <Button variant="outline" className="gap-2 border-white/10 text-white hover:bg-white/10">
            <LayoutDashboard className="w-4 h-4" />
            Return to Dashboard
          </Button>
        </Link>
        <Link to="/dashboard/evaluations">
          <Button className="gap-2 bg-emerald-500 text-black hover:bg-emerald-400 font-medium">
            <ArrowLeft className="w-4 h-4" />
            View Evaluations
          </Button>
        </Link>
      </div>
    </div>
  );
};

export default WorkspaceNotFound;
