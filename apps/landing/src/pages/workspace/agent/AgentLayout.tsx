
import { Outlet } from 'react-router-dom';
import { AgentSidebar } from './components/AgentSidebar';

export default function AgentLayout() {
  return (
    <div className="flex h-full w-full min-h-0 overflow-hidden">
      <AgentSidebar />
      <div className="flex-1 min-w-0 min-h-0 h-full bg-ink-1 flex flex-col">
        <Outlet />
      </div>
    </div>
  );
}
