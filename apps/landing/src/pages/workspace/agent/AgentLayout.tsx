
import { Outlet } from 'react-router-dom';
import { AgentSidebar } from './components/AgentSidebar';

export default function AgentLayout() {
  return (
    <div className="flex flex-1 w-full min-h-0 overflow-hidden">
      <AgentSidebar />
      <div className="flex-1 min-w-0 min-h-0 bg-ink-1 flex flex-col overflow-hidden">
        <Outlet />
      </div>
    </div>
  );
}
