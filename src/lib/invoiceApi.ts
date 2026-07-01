import type { InvoiceFormData, SavedCenter } from '@/features/invoice-generator/invoiceGeneratorTypes';

const BASE_URL = import.meta.env.VITE_INVOICES_API_URL as string | undefined;

export interface InvoiceSummary {
  invoiceNumber: string;
  studentName: string;
  parentName: string;
  centerCode: string;
  invoiceDate: string;
  totalAmount: number;
  status: string;
  createdAt: string;
}

export interface InvoiceListResponse {
  invoices: InvoiceSummary[];
  count: number;
}

function apiUrl(path: string): string {
  return `${BASE_URL}${path}`;
}

export function isApiConfigured(): boolean {
  return !!BASE_URL;
}

export async function saveInvoice(data: InvoiceFormData): Promise<void> {
  if (!BASE_URL) return;
  const res = await fetch(apiUrl('/invoices'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Save failed: ${res.status}`);
  }
}

export async function listInvoices(): Promise<InvoiceListResponse> {
  if (!BASE_URL) return { invoices: [], count: 0 };
  const res = await fetch(apiUrl('/invoices'));
  if (!res.ok) throw new Error(`List failed: ${res.status}`);
  return res.json();
}

export async function getInvoice(invoiceNumber: string): Promise<InvoiceFormData> {
  if (!BASE_URL) throw new Error('API not configured');
  const res = await fetch(apiUrl(`/invoices/${invoiceNumber}`));
  if (!res.ok) throw new Error(`Not found: ${res.status}`);
  return res.json();
}

// ── Centers ────────────────────────────────────────────────────────────

export async function saveCenterToCloud(center: SavedCenter): Promise<void> {
  if (!BASE_URL) return;
  const res = await fetch(apiUrl('/centers'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(center),
  });
  if (!res.ok) throw new Error(`Center save failed: ${res.status}`);
}

export async function listCentersFromCloud(): Promise<SavedCenter[]> {
  if (!BASE_URL) return [];
  const res = await fetch(apiUrl('/centers'));
  if (!res.ok) throw new Error(`Center list failed: ${res.status}`);
  const data = await res.json();
  return data.centers ?? [];
}

export async function deleteCenterFromCloud(centerCode: string): Promise<void> {
  if (!BASE_URL) return;
  const res = await fetch(apiUrl(`/centers/${encodeURIComponent(centerCode)}`), { method: 'DELETE' });
  if (!res.ok) throw new Error(`Center delete failed: ${res.status}`);
}
