import {
  NavLink,
  Navigate,
  Route,
  Routes,
  useMatch,
} from 'react-router-dom';
import { StoreProvider, useStore } from '@/store/store';
import { AuthProvider, useAuth } from '@/features/auth/AuthContext';
import { LoginPage } from '@/features/auth/LoginPage';
import { SignupPage } from '@/features/auth/SignupPage';
import { ProtectedRoute } from '@/features/auth/ProtectedRoute';
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
import { InvoiceHistoryPage } from '@/features/invoice-generator/InvoiceHistoryPage';
import { PaymentsPage } from '@/features/invoice-generator/PaymentsPage';
import {
  ChildrenIcon,
  LogoutIcon,
  RolesIcon,
  SessionsIcon,
  TimetableIcon,
  ReceiptIcon,
} from '@/components/ui/icons';
import type { ComponentType, SVGProps } from 'react';

type IconType = ComponentType<SVGProps<SVGSVGElement>>;

const _CENTRE_SUBNAV: { to: (id: string) => string; label: string; Icon: IconType }[] = [
  { to: (id) => `/admin/centres/${id}/sessions`, label: 'Sessions', Icon: SessionsIcon },
  { to: (id) => `/admin/centres/${id}/timetable`, label: 'Timetable', Icon: TimetableIcon },
  { to: (id) => `/admin/centres/${id}/children`, label: 'Children', Icon: ChildrenIcon },
  { to: (id) => `/admin/centres/${id}/roles`, label: 'Roles', Icon: RolesIcon },
];
void _CENTRE_SUBNAV;

function Sidebar() {
  const centreMatch = useMatch('/admin/centres/:centreId/*');
  const openCentreId = centreMatch?.params.centreId ?? null;
  const { centres } = useStore();
  const { isRoot, user, logout } = useAuth();
  const _openCentre = centres.find((c) => c.id === openCentreId) ?? null;
  void _openCentre;

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
        <div className="px-3 py-2 text-xs uppercase tracking-wide text-text-muted font-semibold">
          Invoices
        </div>
        <NavLink
          to="/admin/invoices/generate"
          className={({ isActive }) =>
            [
              'flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium ml-2',
              isActive
                ? 'bg-olive/10 text-olive'
                : 'text-text-muted hover:bg-beige hover:text-text',
            ].join(' ')
          }
        >
          <ReceiptIcon className="shrink-0" />
          <span>Generate Invoice</span>
        </NavLink>
        <NavLink
          to="/admin/invoices/history"
          className={({ isActive }) =>
            [
              'flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium ml-2',
              isActive
                ? 'bg-olive/10 text-olive'
                : 'text-text-muted hover:bg-beige hover:text-text',
            ].join(' ')
          }
        >
          <ReceiptIcon className="shrink-0" />
          <span>Invoice History</span>
        </NavLink>
        <NavLink
          to="/admin/payments"
          className={({ isActive }) =>
            [
              'flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium ml-2',
              isActive
                ? 'bg-olive/10 text-olive'
                : 'text-text-muted hover:bg-beige hover:text-text',
            ].join(' ')
          }
        >
          <ReceiptIcon className="shrink-0" />
          <span>Payments</span>
        </NavLink>

      </nav>

      {/* User info & logout */}
      <div className="border-t border-border pt-3 mt-2">
        <div className="flex items-center gap-2 px-2 mb-2">
          <div className="w-7 h-7 rounded-full bg-olive/10 flex items-center justify-center text-xs font-semibold text-olive shrink-0">
            {user?.name?.charAt(0).toUpperCase() ?? 'U'}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium text-charcoal truncate">{user?.name}</p>
            <p className="text-[10px] text-text-dim truncate">
              {isRoot ? 'Root Admin' : 'Admin'}
            </p>
          </div>
        </div>
        <button
          onClick={() => logout()}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm text-text-muted hover:bg-beige hover:text-text w-full transition-colors"
        >
          <LogoutIcon className="shrink-0" width={16} height={16} />
          <span>Logout</span>
        </button>
      </div>
      <div className="text-xs text-text-dim px-2 pt-3 border-t border-border mt-2">
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
          <Route index element={<Navigate to="/admin/invoices/generate" replace />} />
          <Route path="centres" element={<CentresPage />} />
          <Route path="centres/:centreId" element={<CentreLayout />}>
            <Route index element={<CentreOverview />} />
            <Route path="sessions" element={<CentreSessionsRoute />} />
            <Route path="timetable" element={<CentreTimetableRoute />} />
            <Route path="children" element={<CentreChildrenRoute />} />
            <Route path="roles" element={<CentreRolesRoute />} />
          </Route>
          <Route path="invoices/generate" element={<InvoiceGeneratorPage />} />
          <Route path="invoices/history" element={<InvoiceHistoryPage />} />
          <Route path="invoices" element={<Navigate to="/admin/invoices/generate" replace />} />
          <Route path="payments" element={<PaymentsPage />} />
          <Route path="info" element={<InfoPage />} />
          <Route path="*" element={<Navigate to="/admin/centres" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <StoreProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/request-access" element={<SignupPage />} />
          <Route path="/signup" element={<Navigate to="/request-access" replace />} />
          <Route path="/admin/*" element={
            <ProtectedRoute>
              <AdminLayout />
            </ProtectedRoute>
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </StoreProvider>
    </AuthProvider>
  );
}
