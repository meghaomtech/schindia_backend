import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { StoreProvider } from '@/store/store';
import { CentresPage } from '@/features/centres/CentresPage';
import { SessionsPage } from '@/features/sessions/SessionsPage';
import { SchedulePage } from '@/features/schedule/SchedulePage';
import { ChildrenPage } from '@/features/children/ChildrenPage';

interface NavItem {
  to: string;
  label: string;
  icon: string;
}

const NAV: NavItem[] = [
  { to: '/centres', label: 'Centres', icon: '🏠' },
  { to: '/sessions', label: 'Sessions', icon: '🧩' },
  { to: '/schedule', label: 'Schedule', icon: '🗓️' },
  { to: '/children', label: 'Children', icon: '👶' },
];

export default function App() {
  return (
    <StoreProvider>
      <div className="flex h-full">
        <aside className="w-56 shrink-0 border-r border-border bg-bg-elev p-4 flex flex-col">
          <div className="mb-6 px-2">
            <div className="text-lg font-bold text-olive tracking-tight">
              Shichida India
            </div>
            <div className="text-xs text-text-muted">Admin portal</div>
          </div>
          <nav className="flex-1 space-y-1">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  [
                    'flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium',
                    isActive
                      ? 'bg-olive/10 text-olive'
                      : 'text-text-muted hover:bg-beige hover:text-text',
                  ].join(' ')
                }
              >
                <span>{n.icon}</span>
                <span>{n.label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="text-xs text-text-dim px-2 pt-3 border-t border-border">
            Phase 1 · v0.1
          </div>
        </aside>

        <main className="flex-1 overflow-y-auto p-6">
          <Routes>
            <Route path="/" element={<Navigate to="/centres" replace />} />
            <Route path="/centres" element={<CentresPage />} />
            <Route path="/sessions" element={<SessionsPage />} />
            <Route path="/schedule" element={<SchedulePage />} />
            <Route path="/children" element={<ChildrenPage />} />
            <Route path="*" element={<Navigate to="/centres" replace />} />
          </Routes>
        </main>
      </div>
    </StoreProvider>
  );
}
