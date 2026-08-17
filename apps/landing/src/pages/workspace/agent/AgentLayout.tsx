
import { Outlet } from 'react-router-dom';
import { AgentSidebar } from './components/AgentSidebar';

export default function AgentLayout() {
  return (
    <div className="flex h-full w-full overflow-hidden">
      <AgentSidebar />
      <div className="flex-1 min-w-0 h-full bg-ink-1">
        <Outlet />
      </div>
    </div>
  );
}
