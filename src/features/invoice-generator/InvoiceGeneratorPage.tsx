import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { InvoiceForm, nextInvoiceNum } from './InvoiceForm';
import { InvoicePreview } from './InvoicePreview';
import type { InvoiceFormData } from './invoiceGeneratorTypes';
import { saveInvoiceLocally } from './invoiceLocalStorage';
import { saveInvoice, isApiConfigured } from '@/lib/invoiceApi';

type Step = 'form' | 'preview';

const COMPANY_GST = '06AAKCB5662Q1Z0';

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export function defaultFormData(): InvoiceFormData {
  return {
    centerCode: '',
    centerLocation: '',
    fullAddress: '',
    centerEmail: '',
    centerPhone: '',
    gstNumber: COMPANY_GST,
    website: '',
    bankName: '',
    accountNumber: '',
    ifscCode: '',
    upiId: '',
    studentName: '',
    parentName: '',
    city: '',
    contact: '',
    email: '',
    invoiceNumber: nextInvoiceNum(),
    invoiceDate: todayISO(),
    dueDate: '',
    gstPercent: 0,
    debitBroughtForward: 0,
    registrationFee: 0,
    sessionFeeStart: '',
    sessionFeeEnd: '',
    sessionFeeAmount: 0,
    extraItems: [],
    deductions: [],
  };
}

export function InvoiceGeneratorPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('form');
  const [formData, setFormData] = useState<InvoiceFormData>(defaultFormData);

  function handleGenerate() {
    // Save invoice to local history
    saveInvoiceLocally(formData);
    // Also save to AWS if configured
    if (isApiConfigured()) {
      saveInvoice(formData).catch((e) => console.error('API save failed:', e));
    }
    setStep('preview');
  }

  if (step === 'form') {
    return (
      <InvoiceForm
        data={formData}
        onChange={setFormData}
        onGenerate={handleGenerate}
      />
    );
  }

  return (
    <InvoicePreview
      data={formData}
      sent={false}
      onBack={() => setStep('form')}
      onCreateNew={() => {
        setFormData(defaultFormData());
        setStep('form');
      }}
      onViewHistory={() => navigate('/admin/invoices/history')}
    />
  );
}
