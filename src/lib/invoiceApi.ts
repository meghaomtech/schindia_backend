import type { InvoiceFormData } from '@/features/invoice-generator/invoiceGeneratorTypes';

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
