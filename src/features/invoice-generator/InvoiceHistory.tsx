import { useEffect, useState } from 'react';
import { listInvoices, getInvoice, isApiConfigured, type InvoiceSummary } from '@/lib/invoiceApi';
import type { InvoiceFormData } from './invoiceGeneratorTypes';
import { InvoicePreview } from './InvoicePreview';

function fmtDate(iso: string): string {
  if (!iso) return '—';
  const [y, m, d] = iso.split('-').map(Number);
  return `${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}/${y}`;
}

function formatINR(n: number): string {
  return `₹ ${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

export function InvoiceHistory() {
  const [invoices, setInvoices] = useState<InvoiceSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewing, setViewing] = useState<InvoiceFormData | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<string | null>(null);

  useEffect(() => {
    if (!isApiConfigured()) {
      setLoading(false);
      return;
    }
    listInvoices()
      .then((r) => setInvoices(r.invoices))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function openInvoice(invoiceNumber: string) {
    setLoadingDetail(invoiceNumber);
    try {
      const data = await getInvoice(invoiceNumber);
      setViewing(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingDetail(null);
    }
  }

  if (viewing) {
    return (
      <InvoicePreview
        data={viewing}
        sent={false}
        onBack={() => setViewing(null)}
        onSend={() => {}}
        onCreateNew={() => setViewing(null)}
      />
    );
  }

  if (!isApiConfigured()) {
    return (
      <div className="rounded-xl border border-border bg-cream/40 p-10 text-center space-y-2">
        <p className="font-medium text-charcoal">Invoice history not connected</p>
        <p className="text-sm text-text-muted">
          Set <code className="bg-beige px-1 rounded">VITE_INVOICES_API_URL</code> to your API Gateway URL to enable history.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="text-center py-16 text-text-muted text-sm animate-pulse">
        Loading invoices…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-danger/10 border border-danger/20 text-danger text-sm px-4 py-3">
        Failed to load invoices: {error}
      </div>
    );
  }

  if (invoices.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-cream/40 p-10 text-center text-text-muted text-sm">
        No invoices yet. Create your first one.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-text-muted">{invoices.length} invoice{invoices.length !== 1 ? 's' : ''}</p>
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
                <td className="px-4 py-3 text-text-muted">{inv.centerCode || '—'}</td>
                <td className="px-4 py-3 text-text-muted">{fmtDate(inv.invoiceDate)}</td>
                <td className="px-4 py-3 text-right font-medium">
                  {inv.totalAmount != null ? formatINR(inv.totalAmount) : '—'}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    className="text-xs font-medium text-[#1a5fa8] hover:underline disabled:opacity-50"
                    disabled={loadingDetail === inv.invoiceNumber}
                    onClick={() => openInvoice(inv.invoiceNumber)}
                  >
                    {loadingDetail === inv.invoiceNumber ? 'Loading…' : 'View'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
