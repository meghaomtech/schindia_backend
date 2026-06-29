import {
  NavLink,
  Navigate,
  Route,
  Routes,
  useMatch,
} from 'react-router-dom';
import { StoreProvider, useStore } from '@/store/store';
import { LandingPage } from '@/features/landing/LandingPage';
import { CentresPage } from '@/features/centres/CentresPage';
import { CentreLayout } from '@/features/centres/CentreLayout';
import { CentreOverview } from '@/features/centres/CentreOverview';
import { CentreSessionsRoute } from '@/features/centres/CentreSessionsRoute';
import { CentreTimetableRoute } from '@/features/centres/CentreTimetableRoute';
import { CentreChildrenRoute } from '@/features/centres/CentreChildrenRoute';
import { CentreRolesRoute } from '@/features/centres/CentreRolesRoute';
import { InfoPage } from '@/features/info/InfoPage';
import { InvoiceGeneratorPage } from '@/features/invoice-generator/InvoiceGeneratorPage';
import {
  CentresIcon,
  ChildrenIcon,
  InfoIcon,
  ReceiptIcon,
  RolesIcon,
  SessionsIcon,
  TimetableIcon,
} from '@/components/ui/icons';
import type { ComponentType, SVGProps } from 'react';

type IconType = ComponentType<SVGProps<SVGSVGElement>>;

const CENTRE_SUBNAV: { to: (id: string) => string; label: string; Icon: IconType }[] = [
  { to: (id) => `/admin/centres/${id}/sessions`, label: 'Sessions', Icon: SessionsIcon },
  { to: (id) => `/admin/centres/${id}/timetable`, label: 'Timetable', Icon: TimetableIcon },
  { to: (id) => `/admin/centres/${id}/children`, label: 'Children', Icon: ChildrenIcon },
  { to: (id) => `/admin/centres/${id}/roles`, label: 'Roles', Icon: RolesIcon },
];

function Sidebar() {
  const centreMatch = useMatch('/admin/centres/:centreId/*');
  const openCentreId = centreMatch?.params.centreId ?? null;
  const { centres } = useStore();
  const openCentre = centres.find((c) => c.id === openCentreId) ?? null;

  return (
    <aside className="w-56 shrink-0 border-r border-border bg-bg-elev p-4 flex flex-col">
      <div className="mb-6 px-2">
        <NavLink to="/" className="block">
          <div className="text-lg font-bold text-olive tracking-tight">
            Shichida India
          </div>
          <div className="text-xs text-text-muted">Admin portal</div>
        </NavLink>
      </div>
      <nav className="flex-1 space-y-1">
        <NavLink
          to="/admin/centres"
          end={!openCentre}
          className={({ isActive }) =>
            [
              'flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium',
              isActive || openCentre
                ? 'bg-olive/10 text-olive'
                : 'text-text-muted hover:bg-beige hover:text-text',
            ].join(' ')
          }
        >
          <CentresIcon className="shrink-0" />
          <span>Centres</span>
        </NavLink>

        {openCentre && (
          <div
            className="ml-3 pl-3 border-l border-olive/30 space-y-1"
            aria-label={`${openCentre.name} sections`}
          >
            <div
              className="px-3 pt-1 pb-0.5 text-[10px] uppercase tracking-wide text-text-dim truncate"
              title={openCentre.name}
            >
              {openCentre.name}
            </div>
            {CENTRE_SUBNAV.map(({ label, to, Icon }) => (
              <NavLink
                key={label}
                to={to(openCentre.id)}
                className={({ isActive }) =>
                  [
                    'flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm',
                    isActive
                      ? 'bg-olive/15 text-olive font-medium'
                      : 'text-text-muted hover:bg-beige hover:text-text',
                  ].join(' ')
                }
              >
                <Icon className="shrink-0" width={16} height={16} />
                <span>{label}</span>
              </NavLink>
            ))}
          </div>
        )}

        <NavLink
          to="/admin/invoices"
          className={({ isActive }) =>
            [
              'flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium',
              isActive
                ? 'bg-olive/10 text-olive'
                : 'text-text-muted hover:bg-beige hover:text-text',
            ].join(' ')
          }
        >
          <ReceiptIcon className="shrink-0" />
          <span>Invoices</span>
        </NavLink>

        <NavLink
          to="/admin/info"
          className={({ isActive }) =>
            [
              'flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium',
              isActive
                ? 'bg-olive/10 text-olive'
                : 'text-text-muted hover:bg-beige hover:text-text',
            ].join(' ')
          }
        >
          <InfoIcon className="shrink-0" />
          <span>Info</span>
        </NavLink>
      </nav>
      <div className="text-xs text-text-dim px-2 pt-3 border-t border-border">
        Phase 1 · v0.1
      </div>
    </aside>
  );
}

function AdminLayout() {
  return (
    <div className="flex h-full">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-6">
        <Routes>
          <Route index element={<Navigate to="/admin/centres" replace />} />
          <Route path="centres" element={<CentresPage />} />
          <Route path="centres/:centreId" element={<CentreLayout />}>
            <Route index element={<CentreOverview />} />
            <Route path="sessions" element={<CentreSessionsRoute />} />
            <Route path="timetable" element={<CentreTimetableRoute />} />
            <Route path="children" element={<CentreChildrenRoute />} />
            <Route path="roles" element={<CentreRolesRoute />} />
          </Route>
          <Route path="invoices" element={<InvoiceGeneratorPage />} />
          <Route path="info" element={<InfoPage />} />
          <Route path="*" element={<Navigate to="/admin/centres" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <StoreProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/admin/*" element={<AdminLayout />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </StoreProvider>
  );
}
