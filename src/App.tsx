import {
  NavLink,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom';
import { StoreProvider } from '@/store/store';
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
import { ReceiptIcon } from '@/components/ui/icons';

function Sidebar() {
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
          <Route path="*" element={<Navigate to="/admin/invoices/generate" replace />} />
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
