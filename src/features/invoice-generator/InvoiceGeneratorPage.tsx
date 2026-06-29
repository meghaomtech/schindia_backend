import { useState } from 'react';
import { InvoiceForm, nextInvoiceNum } from './InvoiceForm';
import { InvoicePreview } from './InvoicePreview';
import { InvoiceHistory } from './InvoiceHistory';
import type { InvoiceFormData } from './invoiceGeneratorTypes';
import { saveInvoice, isApiConfigured } from '@/lib/invoiceApi';

type Step = 'form' | 'preview' | 'sent';
type Tab = 'new' | 'history';

const COMPANY_GST = '06AAKCB5662Q1Z0';

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function tomorrowISO(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}

function defaultFormData(): InvoiceFormData {
  return {
    centerCode: '',
    bankName: '',
    accountNumber: '',
    ifscCode: '',
    gstNumber: COMPANY_GST,
    studentName: '',
    parentName: '',
    city: '',
    contact: '',
    email: '',
    invoiceNumber: nextInvoiceNum(),
    invoiceDate: todayISO(),
    dueDate: tomorrowISO(),
    registrationFee: 0,
    sessionFeeStart: '',
    sessionFeeEnd: '',
    sessionFeeAmount: 0,
    extraItems: [],
  };
}

export function InvoiceGeneratorPage() {
  const [tab, setTab] = useState<Tab>('new');
  const [step, setStep] = useState<Step>('form');
  const [formData, setFormData] = useState<InvoiceFormData>(defaultFormData);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  async function handleSend() {
    setSending(true);
    setSendError(null);
    try {
      await saveInvoice(formData);
    } catch (e) {
      setSendError((e as Error).message);
      setSending(false);
      return;
    }
    setSending(false);
    setStep('sent');
  }

  const isNew = tab === 'new';
  const isHistory = tab === 'history';

  const tabBar = (
    <div className="flex items-center gap-3 border-b border-border pb-4">
      <button
        className={`text-sm font-medium px-3 py-1.5 rounded-md transition-colors ${isNew ? 'bg-charcoal text-white' : 'text-text-muted hover:text-charcoal'}`}
        onClick={() => { setTab('new'); setStep('form'); }}
      >
        + New Invoice
      </button>
      {isApiConfigured() && (
        <button
          className={`text-sm font-medium px-3 py-1.5 rounded-md transition-colors ${isHistory ? 'bg-charcoal text-white' : 'text-text-muted hover:text-charcoal'}`}
          onClick={() => setTab('history')}
        >
          Invoice History
        </button>
      )}
    </div>
  );

  if (isHistory) {
    return (
      <div className="max-w-4xl mx-auto p-6 space-y-5">
        {tabBar}
        <InvoiceHistory />
      </div>
    );
  }

  if (step === 'form') {
    return (
      <div className="space-y-0">
        <div className="pt-6">{tabBar}</div>
        <InvoiceForm
          data={formData}
          onChange={setFormData}
          onGenerate={() => setStep('preview')}
        />
      </div>
    );
  }

  return (
    <div className="space-y-0">
      <div className="pt-6">{tabBar}</div>
      {sendError && (
        <div className="max-w-2xl mx-auto px-6">
          <div className="rounded-md bg-danger/10 border border-danger/20 text-danger text-sm px-4 py-2">
            Failed to save invoice: {sendError}
          </div>
        </div>
      )}
      <InvoicePreview
        data={formData}
        sent={step === 'sent'}
        sending={sending}
        onBack={() => { setStep('form'); setSendError(null); }}
        onSend={handleSend}
        onCreateNew={() => {
          setFormData(defaultFormData());
          setStep('form');
          setSendError(null);
          setTab('new');
        }}
        onViewHistory={() => setTab('history')}
      />
    </div>
  );
}
