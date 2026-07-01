import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { TrashIcon } from '@/components/ui/icons';
import { Modal } from '@/components/ui/Modal';
import { InvoicePreview } from './InvoicePreview';
import { loadInvoiceHistory, deleteInvoiceFromHistory, type StoredInvoice } from './invoiceLocalStorage';
import { isApiConfigured, listInvoices, getInvoice } from '@/lib/invoiceApi';
import type { InvoiceFormData } from './invoiceGeneratorTypes';

function fmtDate(iso: string): string {
  if (!iso) return '—';
  const [y, m, d] = iso.split('-').map(Number);
  return `${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}/${y}`;
}

function formatINR(n: number): string {
  return `₹ ${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

export function InvoiceHistoryPage() {
  const navigate = useNavigate();
  const [invoices, setInvoices] = useState<StoredInvoice[]>(loadInvoiceHistory);
  const [viewing, setViewing] = useState<InvoiceFormData | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  // On mount, if API is configured, merge API invoices with local ones
  useEffect(() => {
    if (!isApiConfigured()) return;
    setLoading(true);
    listInvoices()
      .then((res) => {
        const local = loadInvoiceHistory();
        const localNumbers = new Set(local.map((l) => l.invoiceNumber));
        // Add API invoices that aren't already in local storage
        const apiOnly: StoredInvoice[] = res.invoices
          .filter((inv) => !localNumbers.has(inv.invoiceNumber))
          .map((inv) => ({
            invoiceNumber: inv.invoiceNumber,
            studentName: inv.studentName,
            parentName: inv.parentName,
            centerCode: inv.centerCode,
            centerLocation: '',
            invoiceDate: inv.invoiceDate,
            totalAmount: inv.totalAmount,
            createdAt: inv.createdAt,
            data: null as unknown as InvoiceFormData, // Will fetch on View
          }));
        setInvoices([...local, ...apiOnly]);
      })
      .catch((e) => console.error('Failed to fetch API invoices:', e))
      .finally(() => setLoading(false));
  }, []);

  function handleDelete(invoiceNumber: string) {
    deleteInvoiceFromHistory(invoiceNumber);
    setInvoices((prev) => prev.filter((i) => i.invoiceNumber !== invoiceNumber));
    setConfirmDelete(null);
  }

  async function handleView(inv: StoredInvoice) {
    if (inv.data) {
      setViewing(inv.data);
      return;
    }
    // Fetch full data from API
    if (isApiConfigured()) {
      setLoadingDetail(inv.invoiceNumber);
      try {
        const data = await getInvoice(inv.invoiceNumber);
        setViewing(data);
      } catch (e) {
        console.error('Failed to load invoice:', e);
      } finally {
        setLoadingDetail(null);
      }
    }
  }

  if (viewing) {
    return (
      <InvoicePreview
        data={viewing}
        sent={false}
        onBack={() => setViewing(null)}
        onCreateNew={() => navigate('/admin/invoices/generate')}
        onViewHistory={() => setViewing(null)}
      />
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">Invoice History</h1>
          <p className="text-sm text-text-muted mt-1">All generated invoices are stored here</p>
        </div>
        <Button variant="primary" onClick={() => navigate('/admin/invoices/generate')}>
          + New Invoice
        </Button>
      </div>

      {invoices.length === 0 && !loading ? (
        <div className="rounded-xl border border-border bg-cream/40 p-10 text-center text-text-muted text-sm">
          No invoices generated yet. Create your first one.
        </div>
      ) : loading ? (
        <div className="text-center py-16 text-text-muted text-sm animate-pulse">
          Loading invoices…
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-text-muted">
            {invoices.length} invoice{invoices.length !== 1 ? 's' : ''}
          </p>
          <div className="rounded-xl border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-border">
                  <th className="px-4 py-3 text-left font-semibold text-text-muted">Invoice #</th>
                  <th className="px-4 py-3 text-left font-semibold text-text-muted">Student</th>
                  <th className="px-4 py-3 text-left font-semibold text-text-muted">Parent</th>
                  <th className="px-4 py-3 text-left font-semibold text-text-muted">Center</th>
                  <th className="px-4 py-3 text-left font-semibold text-text-muted">Date</th>
                  <th className="px-4 py-3 text-right font-semibold text-text-muted">Total</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv, i) => (
                  <tr
                    key={inv.invoiceNumber}
                    className={`border-b border-border last:border-0 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}`}
                  >
                    <td className="px-4 py-3 font-mono font-semibold text-[#1a5fa8]">
                      {inv.invoiceNumber}
                    </td>
                    <td className="px-4 py-3">{inv.studentName || '—'}</td>
                    <td className="px-4 py-3 text-text-muted">{inv.parentName || '—'}</td>
                    <td className="px-4 py-3 text-text-muted">
                      {inv.centerCode || '—'}
                      {inv.centerLocation ? ` — ${inv.centerLocation}` : ''}
                    </td>
                    <td className="px-4 py-3 text-text-muted">{fmtDate(inv.invoiceDate)}</td>
                    <td className="px-4 py-3 text-right font-medium">
                      {formatINR(inv.totalAmount)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          className="text-xs font-medium text-[#1a5fa8] hover:underline disabled:opacity-50"
                          disabled={loadingDetail === inv.invoiceNumber}
                          onClick={() => handleView(inv)}
                        >
                          {loadingDetail === inv.invoiceNumber ? 'Loading…' : 'View'}
                        </button>
                        <button
                          className="h-7 w-7 inline-flex items-center justify-center rounded-md text-text-muted hover:text-danger hover:bg-danger/10"
                          title="Delete invoice"
                          onClick={() => setConfirmDelete(inv.invoiceNumber)}
                        >
                          <TrashIcon width={14} height={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        title="Delete Invoice"
        size="sm"
        footer={
          <>
            <Button variant="danger" onClick={() => { if (confirmDelete) handleDelete(confirmDelete); }}>
              Yes, Delete
            </Button>
            <Button onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
          </>
        }
      >
        <p className="text-sm text-text-muted">
          Are you sure you want to delete invoice <strong>{confirmDelete}</strong>? This action cannot be undone.
        </p>
      </Modal>
    </div>
  );
}
